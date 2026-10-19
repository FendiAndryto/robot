from fastapi import APIRouter, Depends, status
from app.models.risk import (
    LotCalculationRequest,
    LotCalculationResponse,
    KillSwitchTriggerRequest,
    KillSwitchStatusResponse,
)
from app.services.risk_service import risk_service
from app.services.bridge_service import bridge_service
from app.core.deps import get_current_user

router = APIRouter(prefix="/risk", tags=["Risk Management & Safety"])


@router.post(
    "/calculate-lot",
    response_model=LotCalculationResponse,
    status_code=status.HTTP_200_OK,
    summary="Calculate dynamic position size based on risk percentage and stop loss pips"
)
async def calculate_lot_size(
    req: LotCalculationRequest
):
    live_equity = bridge_service.get_equity()
    return risk_service.calculate_lot(req, live_equity=live_equity)


@router.post(
    "/kill-switch",
    status_code=status.HTTP_200_OK,
    summary="Trigger emergency Kill Switch to close all open trades and disarm trading"
)
async def trigger_kill_switch(
    payload: KillSwitchTriggerRequest,
    current_user: str = Depends(get_current_user)
):
    reason = payload.reason or "Manual emergency kill switch triggered"
    return bridge_service.trigger_kill_switch(reason=reason, username=current_user)


@router.post(
    "/unlock",
    status_code=status.HTTP_200_OK,
    summary="Disarm emergency Kill Switch and restore normal trading operations"
)
async def disarm_kill_switch(
    current_user: str = Depends(get_current_user)
):
    return bridge_service.disarm_kill_switch(username=current_user)


@router.get(
    "/status",
    response_model=KillSwitchStatusResponse,
    status_code=status.HTTP_200_OK,
    summary="Retrieve current emergency Kill Switch state and risk parameters"
)
async def get_risk_status():
    return bridge_service.get_kill_switch_status()
