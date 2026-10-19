from typing import Optional, List, Any
from pydantic import BaseModel, Field


class PositionItem(BaseModel):
    ticket: int = Field(..., description="MT5 Position Ticket ID")
    symbol: str = Field(..., description="Trading Instrument Symbol (e.g. EURUSD)")
    type: str = Field(..., description="Position Type: BUY or SELL")
    volume: float = Field(..., description="Position Lot Size")
    open_price: float = Field(..., description="Order Open Price")
    current_price: float = Field(0.0, description="Current Market Price")
    sl: float = Field(0.0, description="Stop Loss Price")
    tp: float = Field(0.0, description="Take Profit Price")
    pnl: float = Field(0.0, description="Floating Profit and Loss")
    open_time: int = Field(0, description="Unix timestamp when order was opened")
    magic: int = Field(0, description="Expert Advisor Magic Number")


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
    positions: List[PositionItem] = Field(default_factory=list, description="Active open positions list")
    timestamp: int = Field(..., description="Unix timestamp sent from terminal")


class CommandItem(BaseModel):
    command_id: str
    action: str  # "BUY", "SELL", "CLOSE", "CLOSE_ALL"
    symbol: Optional[str] = None
    volume: Optional[float] = None
    sl: Optional[float] = None
    tp: Optional[float] = None
    ticket: Optional[int] = None
    created_at: int


class OrderRequest(BaseModel):
    action: str = Field(..., description="Action: BUY, SELL, CLOSE, or CLOSE_ALL")
    symbol: Optional[str] = Field(None, description="Trading instrument symbol (e.g. EURUSD, XAUUSD)")
    volume: Optional[float] = Field(0.01, description="Lot size", ge=0.01)
    sl: Optional[float] = Field(None, description="Stop loss price")
    tp: Optional[float] = Field(None, description="Take profit price")
    ticket: Optional[int] = Field(None, description="Target position ticket to close")


class OrderResponse(BaseModel):
    status: str = "queued"
    command_id: str
    message: str
    command: CommandItem


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
    positions: List[PositionItem] = []
    pending_commands_count: int = 0
    is_kill_switch_active: bool = False
    kill_switch_reason: Optional[str] = None
    kill_switch_time: Optional[int] = None
