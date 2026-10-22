import time
import threading
from datetime import datetime, timezone
from typing import Optional, Dict
from fastapi import HTTPException, status
from app.core.config import settings
from app.models.autopilot import AutoPilotStatusResponse


class UserAutoPilotState:
    def __init__(self, username: str):
        self.username = username
        self.is_autopilot_active: bool = settings.AUTOPILOT_DEFAULT_ENABLED
        self.is_drawdown_lockout_active: bool = False
        self.drawdown_lockout_reason: Optional[str] = None
        self.drawdown_lockout_time: Optional[int] = None
        self.starting_equity: Optional[float] = None
        self.closed_daily_pnl: float = 0.0
        self.last_reset_date: str = ""
        self.auto_executed_count: int = 0


class AutoPilotService:
    def __init__(self):
        self._lock = threading.Lock()
        self._states: Dict[str, UserAutoPilotState] = {}

    def _get_state(self, username: Optional[str]) -> UserAutoPilotState:
        key = (username or settings.ADMIN_USERNAME).strip().lower()
        if key not in self._states:
            self._states[key] = UserAutoPilotState(username=key)
        return self._states[key]

    def reset_state(self):
        """Reset internal state for unit test isolation."""
        with self._lock:
            self._states.clear()

    def _check_day_rollover(self, state: UserAutoPilotState, current_equity: float):
        """Reset daily tracking at 00:00 UTC."""
        today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        if not state.last_reset_date:
            state.last_reset_date = today_str
            if state.starting_equity is None and current_equity > 0:
                state.starting_equity = current_equity
            return

        if state.last_reset_date != today_str:
            state.last_reset_date = today_str
            state.closed_daily_pnl = 0.0
            # Auto-reset drawdown lockout on new trading day
            state.is_drawdown_lockout_active = False
            state.drawdown_lockout_reason = None
            state.drawdown_lockout_time = None
            if current_equity > 0:
                state.starting_equity = current_equity

    def record_closed_trade(self, pnl: float, username: Optional[str] = None):
        with self._lock:
            st = self._get_state(username)
            st.closed_daily_pnl += pnl

    def set_starting_equity_baseline(self, equity: float, username: Optional[str] = None):
        today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        with self._lock:
            st = self._get_state(username)
            if equity > 0:
                st.starting_equity = equity
                st.last_reset_date = today_str

    def ensure_active_on_connect(self, username: Optional[str] = None):
        """Automatically engage AutoPilot whenever MT5 terminal connects, provided Drawdown Guard is not locked."""
        from app.services.bridge_service import bridge_service
        user_key = (username or settings.ADMIN_USERNAME).strip().lower()
        bridge_status = bridge_service.get_status(username=user_key)
        with self._lock:
            st = self._get_state(user_key)
            if not st.is_drawdown_lockout_active and not bridge_status.is_kill_switch_active:
                st.is_autopilot_active = True

    def is_autopilot_active(self, username: Optional[str] = None) -> bool:
        from app.services.bridge_service import bridge_service
        user_key = (username or settings.ADMIN_USERNAME).strip().lower()
        bridge_status = bridge_service.get_status(username=user_key)
        with self._lock:
            st = self._get_state(user_key)
            if bridge_status.is_connected and not st.is_drawdown_lockout_active and not bridge_status.is_kill_switch_active:
                st.is_autopilot_active = True
            return st.is_autopilot_active and not st.is_drawdown_lockout_active

    def is_drawdown_locked(self, username: Optional[str] = None) -> bool:
        with self._lock:
            return self._get_state(username).is_drawdown_lockout_active

    def increment_auto_executed_count(self, username: Optional[str] = None):
        with self._lock:
            self._get_state(username).auto_executed_count += 1

    def toggle_autopilot(self, enabled: bool, username: str = "admin") -> dict:
        from app.services.bridge_service import bridge_service
        user_key = (username or settings.ADMIN_USERNAME).strip().lower()
        bridge_status = bridge_service.get_status(username=user_key)

        with self._lock:
            st = self._get_state(user_key)
            if enabled:
                if st.is_drawdown_lockout_active:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail=f"Cannot engage Auto-Pilot: System is locked by Daily Drawdown Guard ({st.drawdown_lockout_reason})."
                    )
                if bridge_status.is_kill_switch_active:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="Cannot engage Auto-Pilot: Emergency Kill Switch is currently active."
                    )
                st.is_autopilot_active = True
                msg = "Autonomous Auto-Pilot mode ENGAGED. Strategy confluence signals will execute automatically."
            else:
                st.is_autopilot_active = False
                msg = "Autonomous Auto-Pilot mode DISENGAGED. Robot switched to standby / observing mode."

        return {
            "status": "success",
            "is_autopilot_active": st.is_autopilot_active,
            "message": msg,
            "toggled_by": username
        }

    def reset_drawdown_lockout(self, new_baseline: Optional[float] = None, username: str = "admin") -> dict:
        with self._lock:
            st = self._get_state(username)
            st.is_drawdown_lockout_active = False
            st.drawdown_lockout_reason = None
            st.drawdown_lockout_time = None
            if new_baseline and new_baseline > 0:
                st.starting_equity = new_baseline

        return {
            "status": "reset",
            "is_drawdown_lockout_active": False,
            "message": "Daily Drawdown Guard disarmed. Normal operations restored.",
            "unlocked_by": username
        }

    def get_status(self, username: Optional[str] = None) -> AutoPilotStatusResponse:
        from app.services.bridge_service import bridge_service
        user_key = (username or settings.ADMIN_USERNAME).strip().lower()
        bridge_status = bridge_service.get_status(username=user_key)
        metrics = bridge_status.metrics

        live_equity = metrics.equity if (metrics and metrics.equity > 0) else 10000.0
        floating_pnl = metrics.floating_pnl if metrics else 0.0

        current_time = int(time.time())

        with self._lock:
            st = self._get_state(user_key)
            if bridge_status.is_connected and not st.is_drawdown_lockout_active and not bridge_status.is_kill_switch_active:
                st.is_autopilot_active = True

            self._check_day_rollover(st, live_equity)

            baseline = st.starting_equity or live_equity
            daily_loss_amount = baseline - live_equity
            daily_dd_pct = round((daily_loss_amount / baseline) * 100.0, 2) if baseline > 0 else 0.0
            daily_dd_pct = max(0.0, daily_dd_pct)

            max_allowed = settings.MAX_DAILY_DRAWDOWN_PERCENT
            closed_pnl = round(st.closed_daily_pnl, 2)
            flt_pnl = round(floating_pnl, 2)
            tot_pnl = round(closed_pnl + flt_pnl, 2)
            daily_dd_amt = round(max(0.0, daily_loss_amount), 2)

            return AutoPilotStatusResponse(
                is_autopilot_active=st.is_autopilot_active and not st.is_drawdown_lockout_active,
                is_drawdown_lockout_active=st.is_drawdown_lockout_active,
                drawdown_lockout_reason=st.drawdown_lockout_reason,
                lockout_time=st.drawdown_lockout_time,
                starting_equity=round(baseline, 2),
                current_equity=round(live_equity, 2),
                closed_daily_pnl=closed_pnl,
                floating_pnl=flt_pnl,
                total_daily_pnl=tot_pnl,
                daily_drawdown_amount=daily_dd_amt,
                daily_drawdown_percent=daily_dd_pct,
                max_daily_drawdown_percent=max_allowed,
                auto_executed_signals_count=st.auto_executed_count
            )

    def check_drawdown(self, current_equity: float, floating_pnl: float = 0.0, username: Optional[str] = None) -> bool:
        """Evaluate daily drawdown against threshold and lock out trading if breached."""
        user_key = (username or settings.ADMIN_USERNAME).strip().lower()
        with self._lock:
            st = self._get_state(user_key)
            self._check_day_rollover(st, current_equity)

            if st.starting_equity is None or st.starting_equity <= 0:
                st.starting_equity = current_equity
                return False

            baseline = st.starting_equity
            daily_loss = baseline - current_equity
            daily_dd_pct = (daily_loss / baseline) * 100.0 if baseline > 0 else 0.0

            if daily_dd_pct >= settings.MAX_DAILY_DRAWDOWN_PERCENT:
                if not st.is_drawdown_lockout_active:
                    st.is_drawdown_lockout_active = True
                    st.is_autopilot_active = False
                    st.drawdown_lockout_time = int(time.time())
                    st.drawdown_lockout_reason = (
                        f"Daily Drawdown Guard breached: {daily_dd_pct:.2f}% loss exceeds "
                        f"max allowable limit of {settings.MAX_DAILY_DRAWDOWN_PERCENT:.1f}%. "
                        f"Starting baseline: ${baseline:.2f}, Current equity: ${current_equity:.2f}."
                    )
                    return True
            return False


autopilot_service = AutoPilotService()
