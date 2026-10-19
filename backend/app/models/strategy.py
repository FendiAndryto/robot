from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class CandleData(BaseModel):
    time: int = Field(..., description="Bar open unix timestamp")
    open: float = Field(..., description="Bar Open price")
    high: float = Field(..., description="Bar High price")
    low: float = Field(..., description="Bar Low price")
    close: float = Field(..., description="Bar Close price")
    volume: Optional[float] = Field(0.0, description="Tick or real volume")


class IndicatorValues(BaseModel):
    ema_fast: float
    ema_slow: float
    rsi: float
    trend: str = "NEUTRAL"  # "BULLISH", "BEARISH", "NEUTRAL"


class SignalItem(BaseModel):
    signal_id: str
    symbol: str
    action: str  # "BUY" or "SELL"
    entry_price: float
    sl: float
    tp: float
    sl_pips: float
    tp_pips: float
    risk_reward: str = "1:2.0"
    recommended_lot: float
    risk_amount: float
    reason: str
    indicators: IndicatorValues
    status: str = "PENDING"  # "PENDING", "APPROVED", "DISMISSED", "EXPIRED"
    created_at: int
    expires_at: int


class ApproveSignalRequest(BaseModel):
    custom_lot: Optional[float] = Field(None, gt=0, description="Optional override for lot size")


class DismissSignalRequest(BaseModel):
    reason: Optional[str] = Field("Manual dismissal by trader", description="Reason for dismissing signal")


class StrategyConfigResponse(BaseModel):
    enabled: bool
    ema_fast: int
    ema_slow: int
    rsi_period: int
    rsi_oversold: float
    rsi_overbought: float
    default_sl_pips: float
    default_rr_ratio: float
    signal_ttl_seconds: int
    monitored_symbols: List[str]


class TestSignalRequest(BaseModel):
    symbol: str = "EURUSD"
    action: str = "BUY"
    price: Optional[float] = None
    sl_pips: Optional[float] = None
    rr_ratio: Optional[float] = None
