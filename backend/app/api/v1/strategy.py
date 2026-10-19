from typing import List, Optional
from fastapi import APIRouter, Depends, Query, status
from app.models.strategy import (
    SignalItem,
    ApproveSignalRequest,
    DismissSignalRequest,
    StrategyConfigResponse,
    TestSignalRequest,
    CandleData
)
from app.services.strategy_engine import strategy_engine
from app.services.bridge_service import bridge_service
from app.core.deps import get_current_user

router = APIRouter(prefix="/strategy", tags=["Strategy & Signals"])


@router.get(
    "/signals",
    response_model=List[SignalItem],
    status_code=status.HTTP_200_OK,
    summary="List active or historic trading signals detected by the strategy engine"
)
async def get_signals(
    include_all: bool = Query(False, alias="all", description="Include non-pending signals (approved, dismissed, expired)")
):
    return strategy_engine.get_signals(include_all=include_all)


@router.post(
    "/signals/{signal_id}/approve",
    status_code=status.HTTP_200_OK,
    summary="Semi-Auto: Approve recommended signal and execute order to MT5"
)
async def approve_signal(
    signal_id: str,
    req: ApproveSignalRequest = ApproveSignalRequest(),
    current_user: str = Depends(get_current_user)
):
    return strategy_engine.approve_signal(signal_id=signal_id, custom_lot=req.custom_lot)


@router.post(
    "/signals/{signal_id}/dismiss",
    status_code=status.HTTP_200_OK,
    summary="Semi-Auto: Dismiss recommended signal without executing"
)
async def dismiss_signal(
    signal_id: str,
    req: DismissSignalRequest = DismissSignalRequest(),
    current_user: str = Depends(get_current_user)
):
    return strategy_engine.dismiss_signal(signal_id=signal_id, reason=req.reason)


@router.post(
    "/generate-test-signal",
    response_model=SignalItem,
    status_code=status.HTTP_200_OK,
    summary="Generate a synthetic strategy confluence signal for UI demonstration or testing"
)
async def generate_test_signal(
    req: TestSignalRequest = TestSignalRequest(),
    current_user: str = Depends(get_current_user)
):
    live_equity = bridge_service.get_equity()
    return strategy_engine.create_custom_signal(req=req, live_equity=live_equity)


@router.post(
    "/evaluate-candles",
    response_model=Optional[SignalItem],
    status_code=status.HTTP_200_OK,
    summary="Evaluate a series of OHLC candle bars against EMA Trend and RSI Momentum strategy"
)
async def evaluate_candles(
    symbol: str,
    candles: List[CandleData]
):
    live_equity = bridge_service.get_equity()
    return strategy_engine.evaluate_candles(symbol=symbol, candles=candles, live_equity=live_equity)


@router.get(
    "/config",
    response_model=StrategyConfigResponse,
    status_code=status.HTTP_200_OK,
    summary="Get current technical strategy parameters and monitored symbol settings"
)
async def get_strategy_config():
    return strategy_engine.get_config()
