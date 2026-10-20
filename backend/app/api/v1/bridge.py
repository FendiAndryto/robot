import time
from typing import List
from fastapi import APIRouter, Depends, status
from app.models.bridge import (
    HeartbeatPayload,
    HeartbeatResponse,
    BridgeStatusResponse,
    OrderRequest,
    OrderResponse,
    PositionItem,
    MarketQuoteItem,
    TradeHistoryResponse,
    EquityCurveResponse,
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
async def get_equity_curve():
    return bridge_service.get_equity_curve()


@router.post(
    "/order",
    response_model=OrderResponse,
    status_code=status.HTTP_200_OK,
    summary="Queue a manual trading order for MT5 execution"
)
async def submit_order(
    order_req: OrderRequest,
    current_user: str = Depends(get_current_user)
):
    return bridge_service.submit_order(order_req)


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
