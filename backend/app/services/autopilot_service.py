import time
import threading
from datetime import datetime, timezone
from typing import Optional
from fastapi import HTTPException, status
from app.core.config import settings
from app.models.autopilot import AutoPilotStatusResponse
from app.services.bridge_service import bridge_service


class AutoPilotService:
    def __init__(self):
        self._lock = threading.Lock()
        self._is_autopilot_active: bool = settings.AUTOPILOT_DEFAULT_ENABLED
        self._is_drawdown_lockout_active: bool = False
        self._drawdown_lockout_reason: Optional[str] = None
        self._drawdown_lockout_time: Optional[int] = None
        self._starting_equity: Optional[float] = None
        self._closed_daily_pnl: float = 0.0
        self._last_reset_date: str = ""
        self._auto_executed_count: int = 0

    def reset_state(self):
        """Reset internal state for unit test isolation."""
        with self._lock:
            self._is_autopilot_active = settings.AUTOPILOT_DEFAULT_ENABLED
            self._is_drawdown_lockout_active = False
            self._drawdown_lockout_reason = None
            self._drawdown_lockout_time = None
            self._starting_equity = None
            self._closed_daily_pnl = 0.0
            self._last_reset_date = ""
            self._auto_executed_count = 0

    def _check_day_rollover(self, current_equity: float):
        """Reset daily tracking at 00:00 UTC."""
        today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        if not self._last_reset_date:
            self._last_reset_date = today_str
            if self._starting_equity is None and current_equity > 0:
                self._starting_equity = current_equity
            return

        if self._last_reset_date != today_str:
            self._last_reset_date = today_str
            self._closed_daily_pnl = 0.0
            # Auto-reset drawdown lockout on new trading day
            self._is_drawdown_lockout_active = False
            self._drawdown_lockout_reason = None
            self._drawdown_lockout_time = None
            if current_equity > 0:
                self._starting_equity = current_equity

    def record_closed_trade(self, pnl: float):
        with self._lock:
            self._closed_daily_pnl += pnl

    def set_starting_equity_baseline(self, equity: float):
        today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        with self._lock:
            if equity > 0:
                self._starting_equity = equity
                self._last_reset_date = today_str

    def is_autopilot_active(self) -> bool:
        with self._lock:
            return self._is_autopilot_active and not self._is_drawdown_lockout_active

    def is_drawdown_locked(self) -> bool:
        with self._lock:
            return self._is_drawdown_lockout_active

    def increment_auto_executed_count(self):
        with self._lock:
            self._auto_executed_count += 1

    def toggle_autopilot(self, enabled: bool, username: str = "admin") -> dict:
        bridge_status = bridge_service.get_status()

        with self._lock:
            if enabled:
                if self._is_drawdown_lockout_active:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail=f"Cannot engage Auto-Pilot: System is locked by Daily Drawdown Guard ({self._drawdown_lockout_reason})."
                    )
                if bridge_status.is_kill_switch_active:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="Cannot engage Auto-Pilot: Emergency Kill Switch is currently active."
                    )
                self._is_autopilot_active = True
                msg = "Autonomous Auto-Pilot mode ENGAGED. Strategy confluence signals will execute automatically."
            else:
                self._is_autopilot_active = False
                msg = "Autonomous Auto-Pilot mode DISENGAGED. Switched to manual / semi-auto approval mode."

        return {
            "status": "success",
            "is_autopilot_active": self._is_autopilot_active,
            "message": msg,
            "toggled_by": username
        }

    def reset_drawdown_lockout(self, new_baseline: Optional[float] = None, username: str = "admin") -> dict:
        with self._lock:
            self._is_drawdown_lockout_active = False
            self._drawdown_lockout_reason = None
            self._drawdown_lockout_time = None
            if new_baseline and new_baseline > 0:
                self._starting_equity = new_baseline

        return {
            "status": "reset",
            "is_drawdown_lockout_active": False,
            "message": "Daily Drawdown Guard disarmed. Normal operations restored.",
            "unlocked_by": username
        }

    def get_status(self) -> AutoPilotStatusResponse:
        bridge_status = bridge_service.get_status()
        metrics = bridge_status.metrics

        live_equity = metrics.equity if (metrics and metrics.equity > 0) else 10000.0
        floating_pnl = metrics.floating_pnl if metrics else 0.0

        current_time = int(time.time())

        with self._lock:
            self._check_day_rollover(live_equity)

            if self._starting_equity is None or self._starting_equity <= 0:
                self._starting_equity = live_equity

            baseline = self._starting_equity
            closed_pnl = self._closed_daily_pnl
            total_pnl = round(closed_pnl + floating_pnl, 2)

            # Drawdown relative to starting baseline
            if live_equity < baseline:
                dd_amount = round(baseline - live_equity, 2)
                dd_percent = round((dd_amount / baseline) * 100.0, 2)
            else:
                dd_amount = 0.0
                dd_percent = 0.0

            # Guard Breach Evaluation: Trigger lockout if drawdown exceeds maximum allowable limit
            if dd_percent >= settings.MAX_DAILY_DRAWDOWN_PERCENT and not self._is_drawdown_lockout_active:
                self._is_drawdown_lockout_active = True
                self._is_autopilot_active = False  # Auto shut-off autopilot
                self._drawdown_lockout_time = current_time
                self._drawdown_lockout_reason = (
                    f"Daily Drawdown Breach: -{dd_percent:.2f}% equity loss exceeds maximum allowed safety threshold of {settings.MAX_DAILY_DRAWDOWN_PERCENT:.1f}%."
                )

            return AutoPilotStatusResponse(
                is_autopilot_active=self._is_autopilot_active and not self._is_drawdown_lockout_active,
                is_drawdown_lockout_active=self._is_drawdown_lockout_active,
                drawdown_lockout_reason=self._drawdown_lockout_reason,
                lockout_time=self._drawdown_lockout_time,
                starting_equity=round(baseline, 2),
                current_equity=round(live_equity, 2),
                closed_daily_pnl=round(closed_pnl, 2),
                floating_pnl=round(floating_pnl, 2),
                total_daily_pnl=total_pnl,
                daily_drawdown_amount=dd_amount,
                daily_drawdown_percent=dd_percent,
                max_daily_drawdown_percent=settings.MAX_DAILY_DRAWDOWN_PERCENT,
                auto_executed_signals_count=self._auto_executed_count
            )


autopilot_service = AutoPilotService()
