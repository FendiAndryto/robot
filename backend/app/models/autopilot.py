from typing import Optional
from pydantic import BaseModel, Field


class AutoPilotStatusResponse(BaseModel):
    is_autopilot_active: bool
    is_drawdown_lockout_active: bool
    drawdown_lockout_reason: Optional[str] = None
    lockout_time: Optional[int] = None
    starting_equity: float
    current_equity: float
    closed_daily_pnl: float
    floating_pnl: float
    total_daily_pnl: float
    daily_drawdown_amount: float
    daily_drawdown_percent: float
    max_daily_drawdown_percent: float
    auto_executed_signals_count: int


class AutoPilotToggleRequest(BaseModel):
    enabled: bool = Field(..., description="Enable or disable autonomous Auto-Pilot mode")
    reason: Optional[str] = Field("Manual toggle by trader", description="Reason for state change")


class DrawdownResetRequest(BaseModel):
    starting_equity: Optional[float] = Field(None, gt=0, description="Optional new baseline starting equity")
    reason: Optional[str] = Field("Manual drawdown lockout override by trader", description="Reason for reset")
