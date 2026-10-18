from typing import Optional, List, Any
from pydantic import BaseModel, Field


class HeartbeatPayload(BaseModel):
    account_number: int = Field(..., description="MT5 Account Login Number")
    server: str = Field(..., description="Broker Server Name")
    currency: str = Field("USD", description="Account Base Currency")
    balance: float = Field(..., description="Current Account Balance")
    equity: float = Field(..., description="Current Account Equity")
    margin: float = Field(0.0, description="Current Margin")
    free_margin: float = Field(0.0, description="Current Free Margin")
    margin_level: float = Field(0.0, description="Current Margin Level Percentage")
    floating_pnl: float = Field(0.0, description="Current Floating Profit and Loss")
    terminal_connected: bool = Field(True, description="Whether MT5 terminal is connected to broker")
    open_positions: int = Field(0, description="Total active open positions")
    timestamp: int = Field(..., description="Unix timestamp sent from terminal")


class CommandItem(BaseModel):
    command_id: str
    action: str  # e.g., "BUY", "SELL", "CLOSE", "CLOSE_ALL"
    symbol: Optional[str] = None
    volume: Optional[float] = None
    sl: Optional[float] = None
    tp: Optional[float] = None
    ticket: Optional[int] = None
    created_at: int


class HeartbeatResponse(BaseModel):
    status: str = "ok"
    server_time: int
    commands: List[CommandItem] = []


class BridgeStatusResponse(BaseModel):
    is_connected: bool
    terminal_connected: bool = False
    last_heartbeat_at: Optional[int] = None
    seconds_since_last_heartbeat: Optional[float] = None
    metrics: Optional[HeartbeatPayload] = None
