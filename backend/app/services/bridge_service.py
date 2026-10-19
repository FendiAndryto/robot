import time
import threading
from typing import Optional, List
from app.models.bridge import HeartbeatPayload, HeartbeatResponse, BridgeStatusResponse, CommandItem
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

    def queue_command(self, command: CommandItem) -> None:
        with self._lock:
            self._pending_commands.append(command)

    def get_status(self) -> BridgeStatusResponse:
        current_time = time.time()
        with self._lock:
            if self._last_received_time is None or self._latest_payload is None:
                return BridgeStatusResponse(
                    is_connected=False,
                    terminal_connected=False,
                    last_heartbeat_at=None,
                    seconds_since_last_heartbeat=None,
                    metrics=None
                )
            
            diff = current_time - self._last_received_time
            is_active = (diff <= settings.HEARTBEAT_TIMEOUT_SECONDS)
            
            return BridgeStatusResponse(
                is_connected=is_active,
                terminal_connected=self._latest_payload.terminal_connected if is_active else False,
                last_heartbeat_at=int(self._last_received_time),
                seconds_since_last_heartbeat=round(diff, 2),
                metrics=self._latest_payload
            )


bridge_service = BridgeService()
