import time
import uuid
import threading
from typing import Optional, List, Dict
from fastapi import HTTPException, status
from app.models.bridge import (
    HeartbeatPayload,
    HeartbeatResponse,
    BridgeStatusResponse,
    CommandItem,
    OrderRequest,
    OrderResponse,
    PositionItem,
    MarketQuoteItem,
    ClosedTradeItem,
    TradeHistoryResponse,
    EquityPointItem,
    EquityCurveResponse,
)
from app.core.config import settings


class BridgeService:
    def __init__(self):
        self._lock = threading.Lock()
        self._latest_payload: Optional[HeartbeatPayload] = None
        self._last_received_time: Optional[float] = None
        self._pending_commands: List[CommandItem] = []
        self._is_kill_switch_active: bool = False
        self._kill_switch_reason: Optional[str] = None
        self._kill_switch_time: Optional[int] = None
        self._is_kill_switch_user: Optional[str] = None
        self._previous_positions_map: dict = {}
        self._previous_balance: Optional[float] = None
        self._market_quotes: Dict[str, MarketQuoteItem] = {}
        self._closed_trades_map: Dict[int, ClosedTradeItem] = {}
        self._equity_snapshots: List[dict] = []
        self._chart_symbol: Optional[str] = None

    def reset_state(self):
        """Reset internal state (primarily used for test isolation)."""
        with self._lock:
            self._latest_payload = None
            self._last_received_time = None
            self._pending_commands.clear()
            self._is_kill_switch_active = False
            self._kill_switch_reason = None
            self._kill_switch_time = None
            self._kill_switch_user = None
            self._previous_positions_map.clear()
            self._previous_balance = None
            self._market_quotes.clear()
            self._closed_trades_map.clear()
            self._equity_snapshots.clear()
            self._chart_symbol = None

    def get_equity(self) -> Optional[float]:
        with self._lock:
            if self._latest_payload and self._latest_payload.equity > 0:
                return self._latest_payload.equity
            return None

    def trigger_kill_switch(self, reason: str = "Manual Emergency Kill Switch Triggered", username: str = "admin") -> dict:
        current_time = int(time.time())
        cmd_id = f"cmd_{current_time}_kill_{uuid.uuid4().hex[:6]}"
        kill_cmd = CommandItem(
            command_id=cmd_id,
            action="CLOSE_ALL",
            created_at=current_time
        )
        with self._lock:
            self._is_kill_switch_active = True
            self._kill_switch_reason = reason
            self._kill_switch_time = current_time
            self._kill_switch_user = username
            # Put CLOSE_ALL at the head of commands so MT5 executes it immediately on next poll
            self._pending_commands.insert(0, kill_cmd)
            closed_count = len(self._latest_payload.positions) if self._latest_payload else 0

        # Dispatch structured Telegram emergency alert
        try:
            from app.services.telegram_service import telegram_service
            telegram_service.send_kill_switch_alert_background(
                reason=reason,
                triggered_by=username,
                closed_count=closed_count
            )
        except Exception:
            pass

        return {
            "status": "engaged",
            "is_kill_switch_active": True,
            "reason": reason,
            "triggered_at": current_time,
            "triggered_by": username,
            "command_id": cmd_id,
            "message": "Emergency Kill Switch engaged. Blanket CLOSE_ALL command dispatched to MT5. Trading engine locked."
        }

    def disarm_kill_switch(self, username: str = "admin") -> dict:
        with self._lock:
            self._is_kill_switch_active = False
            prev_reason = self._kill_switch_reason
            self._kill_switch_reason = None
            self._kill_switch_time = None
            self._kill_switch_user = None

        return {
            "status": "disarmed",
            "is_kill_switch_active": False,
            "message": "Trading engine disarmed and unlocked. Normal trading operations restored.",
            "unlocked_by": username
        }

    def get_kill_switch_status(self) -> dict:
        with self._lock:
            return {
                "is_kill_switch_active": self._is_kill_switch_active,
                "kill_switch_reason": self._kill_switch_reason,
                "kill_switch_time": self._kill_switch_time,
                "kill_switch_user": self._kill_switch_user,
                "default_risk_percent": settings.DEFAULT_RISK_PER_TRADE_PERCENT,
                "max_risk_percent": settings.MAX_RISK_PER_TRADE_PERCENT,
                "max_daily_drawdown_percent": settings.MAX_DAILY_DRAWDOWN_PERCENT,
                "min_lot": settings.MIN_LOT_SIZE,
                "max_lot": settings.MAX_LOT_SIZE
            }

    def process_heartbeat(self, payload: HeartbeatPayload) -> HeartbeatResponse:
        current_time = time.time()
        closed_positions = []
        balance_delta = 0.0

        with self._lock:
            # Update market quotes
            if payload.market_quotes:
                for q in payload.market_quotes:
                    self._market_quotes[q.symbol.upper()] = q

            # Update closed trades from MT5 history
            if payload.closed_trades:
                for t in payload.closed_trades:
                    self._closed_trades_map[t.ticket] = t

            if payload.chart_symbol:
                self._chart_symbol = payload.chart_symbol.strip()

            # Record equity snapshot (capped at 500 samples)
            if payload.equity > 0:
                self._equity_snapshots.append({
                    "timestamp": int(current_time),
                    "equity": payload.equity,
                    "balance": payload.balance
                })
                if len(self._equity_snapshots) > 500:
                    self._equity_snapshots.pop(0)

            # Detect closed positions by comparing with previous positions
            current_tickets = {pos.ticket for pos in payload.positions}
            if self._previous_positions_map:
                for old_ticket, old_pos in self._previous_positions_map.items():
                    if old_ticket not in current_tickets:
                        closed_positions.append(old_pos)

            if self._previous_balance is not None:
                balance_delta = round(payload.balance - self._previous_balance, 2)

            self._previous_positions_map = {pos.ticket: pos for pos in payload.positions}
            self._previous_balance = payload.balance

            self._latest_payload = payload
            self._last_received_time = current_time
            
            # Pop pending commands to return to EA
            commands_to_send = list(self._pending_commands)
            self._pending_commands.clear()

        # Real-time strategy evaluation on real candles sent from MT5
        if (payload.candles and len(payload.candles) >= 20) or (payload.candles_m5 and len(payload.candles_m5) >= 20):
            try:
                from app.services.strategy_engine import strategy_engine
                from app.services.autopilot_service import autopilot_service
                from app.models.strategy import CandleData

                parsed_candles_m15 = []
                for c in payload.candles:
                    if isinstance(c, CandleData):
                        parsed_candles_m15.append(c)
                    elif isinstance(c, dict):
                        parsed_candles_m15.append(CandleData(**c))

                parsed_candles_m5 = []
                for c in payload.candles_m5:
                    if isinstance(c, CandleData):
                        parsed_candles_m5.append(c)
                    elif isinstance(c, dict):
                        parsed_candles_m5.append(CandleData(**c))

                sym_eval = self._chart_symbol or (payload.positions[0].symbol if payload.positions else "XAUUSD")
                cur_quote = self._market_quotes.get(sym_eval.upper())
                current_spread = cur_quote.spread if cur_quote else None

                generated_signal = strategy_engine.evaluate_candles(
                    symbol=sym_eval,
                    candles=parsed_candles_m15,
                    candles_m5=parsed_candles_m5 if parsed_candles_m5 else None,
                    live_equity=payload.equity,
                    current_spread=current_spread
                )

                if generated_signal and autopilot_service.is_autopilot_active():
                    auto_order = OrderRequest(
                        action=generated_signal.action,
                        symbol=generated_signal.symbol,
                        volume=generated_signal.recommended_lot,
                        sl=generated_signal.sl,
                        tp=generated_signal.tp
                    )
                    self.submit_order(auto_order)
                    autopilot_service.increment_auto_executed_count()
            except Exception:
                pass

        # Record closed trades into Daily Drawdown Tracker and dispatch Telegram alerts
        if closed_positions:
            try:
                from app.services.autopilot_service import autopilot_service
                from app.services.telegram_service import telegram_service

                for pos in closed_positions:
                    pnl = balance_delta if (len(closed_positions) == 1 and balance_delta != 0.0) else pos.pnl
                    autopilot_service.record_closed_trade(pnl)
                    telegram_service.send_trade_closed_alert_background(
                        ticket=pos.ticket,
                        symbol=pos.symbol,
                        pnl=pnl,
                        reason="TP / SL / Manual Close"
                    )
            except Exception:
                pass

        return HeartbeatResponse(
            status="ok",
            server_time=int(current_time),
            commands=commands_to_send
        )

    def submit_order(self, order_req: OrderRequest) -> OrderResponse:
        action = order_req.action.upper().strip()
        current_time = int(time.time())

        # Safety Check: Block new trade entries if Kill Switch is active
        with self._lock:
            if self._is_kill_switch_active and action in ("BUY", "SELL"):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Trading engine is locked by emergency Kill Switch ({self._kill_switch_reason or 'Emergency lockdown'}). Disarm Kill Switch before submitting new orders."
                )

        # Safety Check: Block new trade entries if Daily Drawdown Guard is locked
        from app.services.autopilot_service import autopilot_service
        if autopilot_service.is_drawdown_locked() and action in ("BUY", "SELL"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Trading engine is locked by Daily Drawdown Guard: Maximum allowable daily loss threshold exceeded."
            )

        if action in ("BUY", "SELL"):
            if not order_req.symbol or not order_req.symbol.strip():
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Symbol is required for BUY/SELL orders."
                )
            if not order_req.volume or order_req.volume <= 0:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Volume must be greater than 0.0."
                )
        elif action == "CLOSE":
            if not order_req.ticket or order_req.ticket <= 0:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Position ticket ID is required for CLOSE action."
                )
        elif action == "CLOSE_ALL":
            pass
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported action: '{action}'. Allowed: BUY, SELL, CLOSE, CLOSE_ALL."
            )

        cmd_id = f"cmd_{current_time}_{uuid.uuid4().hex[:8]}"
        command = CommandItem(
            command_id=cmd_id,
            action=action,
            symbol=order_req.symbol.strip().upper() if order_req.symbol else None,
            volume=round(order_req.volume, 2) if order_req.volume else None,
            sl=order_req.sl,
            tp=order_req.tp,
            ticket=order_req.ticket,
            created_at=current_time
        )

        with self._lock:
            self._pending_commands.append(command)

        msg = f"Order {action}"
        if command.symbol:
            msg += f" {command.volume} lots of {command.symbol}"
        if command.ticket:
            msg += f" (Ticket #{command.ticket})"
        msg += " queued for MT5 execution."

        # Dispatch Telegram trade alert
        try:
            from app.services.telegram_service import telegram_service
            telegram_service.send_order_alert_background({
                "action": action,
                "symbol": command.symbol or "",
                "volume": command.volume or 0.0,
                "ticket": command.ticket or "",
                "sl": command.sl or 0.0,
                "tp": command.tp or 0.0
            })
        except Exception:
            pass

        return OrderResponse(
            status="queued",
            command_id=cmd_id,
            message=msg,
            command=command
        )

    def get_positions(self) -> List[PositionItem]:
        current_time = time.time()
        with self._lock:
            if self._last_received_time is None or self._latest_payload is None:
                return []
            
            diff = current_time - self._last_received_time
            if diff > settings.HEARTBEAT_TIMEOUT_SECONDS:
                return []
            
            return list(self._latest_payload.positions)

    def get_market_quotes(self) -> List[MarketQuoteItem]:
        with self._lock:
            return sorted(list(self._market_quotes.values()), key=lambda x: x.symbol)

    def get_trade_history(self) -> TradeHistoryResponse:
        with self._lock:
            trades = sorted(list(self._closed_trades_map.values()), key=lambda x: x.close_time, reverse=True)
            total = len(trades)
            if total == 0:
                return TradeHistoryResponse(
                    trades=[],
                    net_pnl=0.0,
                    win_rate=0.0,
                    profit_factor=0.0,
                    total_trades=0,
                    winning_trades=0,
                    losing_trades=0,
                    gross_profit=0.0,
                    gross_loss=0.0
                )

            gross_profit = round(sum(t.profit for t in trades if t.profit > 0), 2)
            gross_loss = round(sum(abs(t.profit) for t in trades if t.profit < 0), 2)
            net_pnl = round(sum(t.profit for t in trades), 2)
            wins = sum(1 for t in trades if t.profit > 0)
            losses = sum(1 for t in trades if t.profit < 0)
            win_rate = round((wins / total) * 100.0, 1)
            profit_factor = round(gross_profit / gross_loss, 2) if gross_loss > 0 else (gross_profit if gross_profit > 0 else 1.0)

            return TradeHistoryResponse(
                trades=trades,
                net_pnl=net_pnl,
                win_rate=win_rate,
                profit_factor=profit_factor,
                total_trades=total,
                winning_trades=wins,
                losing_trades=losses,
                gross_profit=gross_profit,
                gross_loss=gross_loss
            )

    def get_equity_curve(self) -> EquityCurveResponse:
        with self._lock:
            points = [
                EquityPointItem(timestamp=s["timestamp"], equity=s["equity"], balance=s["balance"])
                for s in self._equity_snapshots
            ]
            current_eq = self._latest_payload.equity if self._latest_payload else 0.0
            starting_eq = points[0].equity if points else current_eq
            peak_eq = max([p.equity for p in points], default=current_eq)
            return EquityCurveResponse(
                starting_equity=starting_eq,
                current_equity=current_eq,
                peak_equity=peak_eq,
                points=points
            )

    def get_status(self) -> BridgeStatusResponse:
        current_time = time.time()
        with self._lock:
            pending_count = len(self._pending_commands)
            
            if self._last_received_time is None or self._latest_payload is None:
                return BridgeStatusResponse(
                    is_connected=False,
                    terminal_connected=False,
                    last_heartbeat_at=None,
                    seconds_since_last_heartbeat=None,
                    metrics=None,
                    positions=[],
                    market_quotes=list(self._market_quotes.values()),
                    chart_symbol=self._chart_symbol,
                    closed_trades_count=len(self._closed_trades_map),
                    pending_commands_count=pending_count,
                    is_kill_switch_active=self._is_kill_switch_active,
                    kill_switch_reason=self._kill_switch_reason,
                    kill_switch_time=self._kill_switch_time
                )
            
            diff = current_time - self._last_received_time
            is_active = (diff <= settings.HEARTBEAT_TIMEOUT_SECONDS)
            positions = list(self._latest_payload.positions) if is_active else []
            
            return BridgeStatusResponse(
                is_connected=is_active,
                terminal_connected=self._latest_payload.terminal_connected if is_active else False,
                last_heartbeat_at=int(self._last_received_time),
                seconds_since_last_heartbeat=round(diff, 2),
                metrics=self._latest_payload,
                positions=positions,
                market_quotes=list(self._market_quotes.values()),
                chart_symbol=self._chart_symbol,
                closed_trades_count=len(self._closed_trades_map),
                pending_commands_count=pending_count,
                is_kill_switch_active=self._is_kill_switch_active,
                kill_switch_reason=self._kill_switch_reason,
                kill_switch_time=self._kill_switch_time
            )


bridge_service = BridgeService()
