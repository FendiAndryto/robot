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

    def process_heartbeat(self, payload: HeartbeatPayload) -> HeartbeatResponse:
        current_time = time.time()
        with self._lock:
            self._latest_payload = payload
            self._last_received_time = current_time
            
            # Pop pending commands to return to EA
            commands_to_send = list(self._pending_commands)
            self._pending_commands.clear()

        return HeartbeatResponse(
            status="ok",
            server_time=int(current_time),
            commands=commands_to_send
        )

    def submit_order(self, order_req: OrderRequest) -> OrderResponse:
        action = order_req.action.upper().strip()
        current_time = int(time.time())

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
                    pending_commands_count=pending_count
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
                pending_commands_count=pending_count
            )


bridge_service = BridgeService()
