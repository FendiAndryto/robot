import time
from fastapi import APIRouter, status
from app.models.bridge import HeartbeatPayload, HeartbeatResponse, BridgeStatusResponse
from app.services.bridge_service import bridge_service

router = APIRouter(prefix="/bridge", tags=["Bridge"])


@router.post(
    "/heartbeat",
    response_model=HeartbeatResponse,
    status_code=status.HTTP_200_OK,
    summary="Receive periodic heartbeat telemetry from MT5 Bridge EA"
)
async def receive_heartbeat(payload: HeartbeatPayload):
    return bridge_service.process_heartbeat(payload)


@router.get(
    "/status",
    response_model=BridgeStatusResponse,
    status_code=status.HTTP_200_OK,
    summary="Retrieve current MT5 bridge connectivity status and latest metrics"
)
async def get_bridge_status():
    return bridge_service.get_status()


@router.get(
    "/ping",
    summary="Simple ping-pong health check"
)
async def ping():
    return {
        "status": "pong",
        "timestamp": int(time.time())
    }
