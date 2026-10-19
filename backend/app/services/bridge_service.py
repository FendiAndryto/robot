import time
import uuid
import threading
from typing import Optional, List
from fastapi import HTTPException, status
from app.models.bridge import (
    HeartbeatPayload,
    HeartbeatResponse,
    BridgeStatusResponse,
    CommandItem,
    OrderRequest,
    OrderResponse,
    PositionItem,
)
from app.core.config import settings


class BridgeService:
    def __init__(self):
        self._lock = threading.Lock()
        self._latest_payload: Optional[HeartbeatPayload] = None
        self._last_received_time: Optional[float] = None
        self._pending_commands: List[CommandItem] = []
        self._is_kill_switch_active: bool = False
        self._kill_switch_reason: Optional[str] = None
        self._kill_switch_time: Optional[int] = None
        self._is_kill_switch_user: Optional[str] = None
        self._previous_positions_map: dict = {}
        self._previous_balance: Optional[float] = None

    def reset_state(self):
        """Reset internal state (primarily used for test isolation)."""
        with self._lock:
            self._latest_payload = None
            self._last_received_time = None
            self._pending_commands.clear()
            self._is_kill_switch_active = False
            self._kill_switch_reason = None
            self._kill_switch_time = None
            self._kill_switch_user = None
            self._previous_positions_map.clear()
            self._previous_balance = None

    def get_equity(self) -> Optional[float]:
        with self._lock:
            if self._latest_payload and self._latest_payload.equity > 0:
                return self._latest_payload.equity
            return None

    def trigger_kill_switch(self, reason: str = "Manual Emergency Kill Switch Triggered", username: str = "admin") -> dict:
        current_time = int(time.time())
        cmd_id = f"cmd_{current_time}_kill_{uuid.uuid4().hex[:6]}"
        kill_cmd = CommandItem(
            command_id=cmd_id,
            action="CLOSE_ALL",
            created_at=current_time
        )
        with self._lock:
            self._is_kill_switch_active = True
            self._kill_switch_reason = reason
            self._kill_switch_time = current_time
            self._kill_switch_user = username
            # Put CLOSE_ALL at the head of commands so MT5 executes it immediately on next poll
            self._pending_commands.insert(0, kill_cmd)
            closed_count = len(self._latest_payload.positions) if self._latest_payload else 0

        # Dispatch structured Telegram emergency alert
        try:
            from app.services.telegram_service import telegram_service
            telegram_service.send_kill_switch_alert_background(
                reason=reason,
                triggered_by=username,
                closed_count=closed_count
            )
        except Exception:
            pass

        return {
            "status": "engaged",
            "is_kill_switch_active": True,
            "reason": reason,
            "triggered_at": current_time,
            "triggered_by": username,
            "command_id": cmd_id,
            "message": "Emergency Kill Switch engaged. Blanket CLOSE_ALL command dispatched to MT5. Trading engine locked."
        }

    def disarm_kill_switch(self, username: str = "admin") -> dict:
        with self._lock:
            self._is_kill_switch_active = False
            prev_reason = self._kill_switch_reason
            self._kill_switch_reason = None
            self._kill_switch_time = None
            self._kill_switch_user = None

        return {
            "status": "disarmed",
            "is_kill_switch_active": False,
            "message": "Trading engine disarmed and unlocked. Normal trading operations restored.",
            "unlocked_by": username
        }

    def get_kill_switch_status(self) -> dict:
        with self._lock:
            return {
                "is_kill_switch_active": self._is_kill_switch_active,
                "kill_switch_reason": self._kill_switch_reason,
                "kill_switch_time": self._kill_switch_time,
                "kill_switch_user": self._kill_switch_user,
                "default_risk_percent": settings.DEFAULT_RISK_PER_TRADE_PERCENT,
                "max_risk_percent": settings.MAX_RISK_PER_TRADE_PERCENT,
                "max_daily_drawdown_percent": settings.MAX_DAILY_DRAWDOWN_PERCENT,
                "min_lot": settings.MIN_LOT_SIZE,
                "max_lot": settings.MAX_LOT_SIZE
            }

    def process_heartbeat(self, payload: HeartbeatPayload) -> HeartbeatResponse:
        current_time = time.time()
        closed_positions = []
        balance_delta = 0.0

        with self._lock:
            # Detect closed positions by comparing with previous positions
            current_tickets = {pos.ticket for pos in payload.positions}
            if self._previous_positions_map:
                for old_ticket, old_pos in self._previous_positions_map.items():
                    if old_ticket not in current_tickets:
                        closed_positions.append(old_pos)

            if self._previous_balance is not None:
                balance_delta = round(payload.balance - self._previous_balance, 2)

            self._previous_positions_map = {pos.ticket: pos for pos in payload.positions}
            self._previous_balance = payload.balance

            self._latest_payload = payload
            self._last_received_time = current_time
            
            # Pop pending commands to return to EA
            commands_to_send = list(self._pending_commands)
            self._pending_commands.clear()

        # Record closed trades into Daily Drawdown Tracker and dispatch Telegram alerts
        if closed_positions:
            try:
                from app.services.autopilot_service import autopilot_service
                from app.services.telegram_service import telegram_service

                for pos in closed_positions:
                    pnl = balance_delta if (len(closed_positions) == 1 and balance_delta != 0.0) else pos.pnl
                    autopilot_service.record_closed_trade(pnl)
                    telegram_service.send_trade_closed_alert_background(
                        ticket=pos.ticket,
                        symbol=pos.symbol,
                        pnl=pnl,
                        reason="TP / SL / Manual Close"
                    )
            except Exception:
                pass

        return HeartbeatResponse(
            status="ok",
            server_time=int(current_time),
            commands=commands_to_send
        )

    def submit_order(self, order_req: OrderRequest) -> OrderResponse:
        action = order_req.action.upper().strip()
        current_time = int(time.time())

        # Safety Check: Block new trade entries if Kill Switch is active
        with self._lock:
            if self._is_kill_switch_active and action in ("BUY", "SELL"):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Trading engine is locked by emergency Kill Switch ({self._kill_switch_reason or 'Emergency lockdown'}). Disarm Kill Switch before submitting new orders."
                )

        # Safety Check: Block new trade entries if Daily Drawdown Guard is locked
        from app.services.autopilot_service import autopilot_service
        if autopilot_service.is_drawdown_locked() and action in ("BUY", "SELL"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Trading engine is locked by Daily Drawdown Guard: Maximum allowable daily loss threshold exceeded."
            )

        if action in ("BUY", "SELL"):
            if not order_req.symbol or not order_req.symbol.strip():
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Symbol is required for BUY/SELL orders."
                )
            if not order_req.volume or order_req.volume <= 0:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Volume must be greater than 0.0."
                )
        elif action == "CLOSE":
            if not order_req.ticket or order_req.ticket <= 0:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Position ticket ID is required for CLOSE action."
                )
        elif action == "CLOSE_ALL":
            pass
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported action: '{action}'. Allowed: BUY, SELL, CLOSE, CLOSE_ALL."
            )

        cmd_id = f"cmd_{current_time}_{uuid.uuid4().hex[:8]}"
        command = CommandItem(
            command_id=cmd_id,
            action=action,
            symbol=order_req.symbol.strip().upper() if order_req.symbol else None,
            volume=round(order_req.volume, 2) if order_req.volume else None,
            sl=order_req.sl,
            tp=order_req.tp,
            ticket=order_req.ticket,
            created_at=current_time
        )

        with self._lock:
            self._pending_commands.append(command)

        msg = f"Order {action}"
        if command.symbol:
            msg += f" {command.volume} lots of {command.symbol}"
        if command.ticket:
            msg += f" (Ticket #{command.ticket})"
        msg += " queued for MT5 execution."

        # Dispatch Telegram trade alert
        try:
            from app.services.telegram_service import telegram_service
            telegram_service.send_order_alert_background({
                "action": action,
                "symbol": command.symbol or "",
                "volume": command.volume or 0.0,
                "ticket": command.ticket or "",
                "sl": command.sl or 0.0,
                "tp": command.tp or 0.0
            })
        except Exception:
            pass

        return OrderResponse(
            status="queued",
            command_id=cmd_id,
            message=msg,
            command=command
        )

    def get_positions(self) -> List[PositionItem]:
        current_time = time.time()
        with self._lock:
            if self._last_received_time is None or self._latest_payload is None:
                return []
            
            diff = current_time - self._last_received_time
            if diff > settings.HEARTBEAT_TIMEOUT_SECONDS:
                return []
            
            return list(self._latest_payload.positions)

    def get_status(self) -> BridgeStatusResponse:
        current_time = time.time()
        with self._lock:
            pending_count = len(self._pending_commands)
            
            if self._last_received_time is None or self._latest_payload is None:
                return BridgeStatusResponse(
                    is_connected=False,
                    terminal_connected=False,
                    last_heartbeat_at=None,
                    seconds_since_last_heartbeat=None,
                    metrics=None,
                    positions=[],
                    pending_commands_count=pending_count,
                    is_kill_switch_active=self._is_kill_switch_active,
                    kill_switch_reason=self._kill_switch_reason,
                    kill_switch_time=self._kill_switch_time
                )
            
            diff = current_time - self._last_received_time
            is_active = (diff <= settings.HEARTBEAT_TIMEOUT_SECONDS)
            positions = list(self._latest_payload.positions) if is_active else []
            
            return BridgeStatusResponse(
                is_connected=is_active,
                terminal_connected=self._latest_payload.terminal_connected if is_active else False,
                last_heartbeat_at=int(self._last_received_time),
                seconds_since_last_heartbeat=round(diff, 2),
                metrics=self._latest_payload,
                positions=positions,
                pending_commands_count=pending_count,
                is_kill_switch_active=self._is_kill_switch_active,
                kill_switch_reason=self._kill_switch_reason,
                kill_switch_time=self._kill_switch_time
            )


bridge_service = BridgeService()
