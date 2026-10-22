from fastapi import APIRouter, Depends, status
from app.models.autopilot import (
    AutoPilotStatusResponse,
    AutoPilotToggleRequest,
    DrawdownResetRequest
)
from app.services.autopilot_service import autopilot_service
from app.core.deps import get_current_user

router = APIRouter(prefix="/autopilot", tags=["Autonomous Auto-Pilot & Drawdown Guard"])


@router.get(
    "/status",
    response_model=AutoPilotStatusResponse,
    status_code=status.HTTP_200_OK,
    summary="Get current Auto-Pilot operational status and daily drawdown guard metrics for current user"
)
async def get_autopilot_status(current_user: str = Depends(get_current_user)):
    return autopilot_service.get_status(username=current_user)


@router.post(
    "/toggle",
    status_code=status.HTTP_200_OK,
    summary="Toggle autonomous Auto-Pilot trading mode on or off"
)
async def toggle_autopilot(
    payload: AutoPilotToggleRequest,
    current_user: str = Depends(get_current_user)
):
    return autopilot_service.toggle_autopilot(enabled=payload.enabled, username=current_user)


@router.post(
    "/reset-drawdown",
    status_code=status.HTTP_200_OK,
    summary="Disarm daily drawdown lockout and optionally calibrate starting baseline equity"
)
async def reset_drawdown_guard(
    payload: DrawdownResetRequest = DrawdownResetRequest(),
    current_user: str = Depends(get_current_user)
):
    return autopilot_service.reset_drawdown_lockout(new_baseline=payload.starting_equity, username=current_user)
