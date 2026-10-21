import time
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from app.models.bridge import (
    HeartbeatPayload,
    HeartbeatResponse,
    BridgeStatusResponse,
    PositionItem,
    MarketQuoteItem,
    TradeHistoryResponse,
    EquityCurveResponse,
    InitialDepositRequest,
    InitialDepositResponse,
)
from app.services.bridge_service import bridge_service
from app.core.deps import get_current_user

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
    "/initial-deposit",
    response_model=InitialDepositResponse,
    status_code=status.HTTP_200_OK,
    summary="Get initial deposit baseline settings and all-time P/L return"
)
async def get_initial_deposit():
    return bridge_service.get_initial_deposit_info()


@router.post(
    "/initial-deposit",
    response_model=InitialDepositResponse,
    status_code=status.HTTP_200_OK,
    summary="Set or override manual initial deposit baseline (or null/0 to reset to MT5)"
)
async def set_initial_deposit(
    req: InitialDepositRequest,
    current_user: str = Depends(get_current_user)
):
    return bridge_service.set_initial_deposit_override(req.initial_deposit)


@router.get(
    "/history",
    response_model=TradeHistoryResponse,
    status_code=status.HTTP_200_OK,
    summary="Retrieve real closed deals history and calculated metrics directly from MT5"
)
async def get_trade_history():
    return bridge_service.get_trade_history()


@router.get(
    "/market",
    response_model=List[MarketQuoteItem],
    status_code=status.HTTP_200_OK,
    summary="Retrieve live quotes for monitored instruments from MT5 feed"
)
async def get_market_quotes():
    return bridge_service.get_market_quotes()


@router.get(
    "/equity-curve",
    response_model=EquityCurveResponse,
    status_code=status.HTTP_200_OK,
    summary="Retrieve equity snapshots over time for dynamic performance chart"
)
async def get_equity_curve(range: str = "1M"):
    return bridge_service.get_equity_curve(time_range=range)


@router.post(
    "/order",
    status_code=status.HTTP_403_FORBIDDEN,
    summary="Manual order execution disabled (Full-Auto trading only)"
)
async def submit_order():
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Manual order placement from web application is disabled. Trading is strictly full-auto only via autonomous AutoPilot."
    )


@router.get(
    "/positions",
    response_model=List[PositionItem],
    status_code=status.HTTP_200_OK,
    summary="Retrieve currently open trading positions from MT5"
)
async def get_positions():
    return bridge_service.get_positions()


@router.get(
    "/ping",
    summary="Simple ping-pong health check"
)
async def ping():
    return {
        "status": "pong",
        "timestamp": int(time.time())
    }
