import os
import json
import time
import uuid
import threading
from datetime import datetime, timezone
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
    InitialDepositRequest,
    InitialDepositResponse,
)
from app.core.config import settings
from app.services.user_service import user_service


class UserBridgeSession:
    def __init__(self, username: str):
        self.username = username
        self.latest_payload: Optional[HeartbeatPayload] = None
        self.last_received_time: Optional[float] = None
        self.pending_commands: List[CommandItem] = []
        self.is_kill_switch_active: bool = False
        self.kill_switch_reason: Optional[str] = None
        self.kill_switch_time: Optional[int] = None
        self.kill_switch_user: Optional[str] = None
        self.previous_positions_map: dict = {}
        self.previous_balance: Optional[float] = None
        self.market_quotes: Dict[str, MarketQuoteItem] = {}
        self.closed_trades_map: Dict[int, ClosedTradeItem] = {}
        self.equity_snapshots: List[dict] = []
        self.chart_symbol: Optional[str] = None
        self.mt5_initial_deposit: Optional[float] = None
        self.custom_initial_deposit: Optional[float] = user_service.get_custom_initial_deposit(username)

    def get_effective_initial_deposit(self) -> Optional[float]:
        if self.custom_initial_deposit is not None and self.custom_initial_deposit > 0:
            return self.custom_initial_deposit
        if self.mt5_initial_deposit is not None and self.mt5_initial_deposit > 0:
            return self.mt5_initial_deposit
        if self.latest_payload and self.latest_payload.balance > 0:
            return self.latest_payload.balance
        return None


class BridgeService:
    def __init__(self):
        self._lock = threading.Lock()
        self._sessions: Dict[str, UserBridgeSession] = {}

    def _normalize_user(self, username: Optional[str]) -> str:
        return (username or settings.ADMIN_USERNAME).strip().lower()

    def _get_or_create_session(self, username: Optional[str]) -> UserBridgeSession:
        user_key = self._normalize_user(username)
        if user_key not in self._sessions:
            self._sessions[user_key] = UserBridgeSession(username=user_key)
        return self._sessions[user_key]

    def reset_state(self):
        """Reset internal state across all sessions (for unit test isolation)."""
        with self._lock:
            self._sessions.clear()

    def get_equity(self, username: Optional[str] = None) -> Optional[float]:
        with self._lock:
            session = self._get_or_create_session(username)
            if session.latest_payload and session.latest_payload.equity > 0:
                return session.latest_payload.equity
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
            session = self._get_or_create_session(username)
            session.is_kill_switch_active = True
            session.kill_switch_reason = reason
            session.kill_switch_time = current_time
            session.kill_switch_user = username
            session.pending_commands.insert(0, kill_cmd)
            closed_count = len(session.latest_payload.positions) if session.latest_payload else 0

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
            session = self._get_or_create_session(username)
            session.is_kill_switch_active = False
            session.kill_switch_reason = None
            session.kill_switch_time = None
            session.kill_switch_user = None

        return {
            "status": "disarmed",
            "is_kill_switch_active": False,
            "message": "Trading engine disarmed and unlocked. Normal trading operations restored.",
            "unlocked_by": username
        }

    def get_kill_switch_status(self, username: Optional[str] = None) -> dict:
        with self._lock:
            session = self._get_or_create_session(username)
            return {
                "is_kill_switch_active": session.is_kill_switch_active,
                "kill_switch_reason": session.kill_switch_reason,
                "kill_switch_time": session.kill_switch_time,
                "kill_switch_user": session.kill_switch_user,
                "default_risk_percent": settings.DEFAULT_RISK_PER_TRADE_PERCENT,
                "max_risk_percent": settings.MAX_RISK_PER_TRADE_PERCENT,
                "max_daily_drawdown_percent": settings.MAX_DAILY_DRAWDOWN_PERCENT,
                "min_lot": settings.MIN_LOT_SIZE,
                "max_lot": settings.MAX_LOT_SIZE
            }

    def process_heartbeat(self, payload: HeartbeatPayload, bridge_token: Optional[str] = None) -> HeartbeatResponse:
        current_time = time.time()
        token = (bridge_token or payload.bridge_token or "").strip()

        if not token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Bridge Token required. Please provide X-Bridge-Token header or bridge_token in payload."
            )

        user = user_service.get_user_by_bridge_token(token)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid Bridge Token. Authentication failed."
            )

        username = user["username"]
        closed_positions = []

        with self._lock:
            session = self._get_or_create_session(username)

            # Update market quotes
            if payload.market_quotes:
                for q in payload.market_quotes:
                    session.market_quotes[q.symbol.upper()] = q

            # Update closed trades from MT5 history
            if payload.closed_trades:
                for t in payload.closed_trades:
                    session.closed_trades_map[t.ticket] = t

            if payload.initial_deposit and payload.initial_deposit > 0:
                session.mt5_initial_deposit = payload.initial_deposit

            if payload.chart_symbol:
                session.chart_symbol = payload.chart_symbol.strip()

            # Record equity snapshot
            if payload.equity > 0:
                session.equity_snapshots.append({
                    "timestamp": int(current_time),
                    "equity": payload.equity,
                    "balance": payload.balance
                })
                if len(session.equity_snapshots) > 500:
                    session.equity_snapshots.pop(0)

            # Detect closed positions
            current_tickets = {pos.ticket for pos in payload.positions}
            if session.previous_positions_map:
                for old_ticket, old_pos in session.previous_positions_map.items():
                    if old_ticket not in current_tickets:
                        closed_positions.append(old_pos)

            session.previous_positions_map = {pos.ticket: pos for pos in payload.positions}
            session.previous_balance = payload.balance
            session.latest_payload = payload
            session.last_received_time = current_time

        # Engage AutoPilot for this user
        try:
            from app.services.autopilot_service import autopilot_service
            autopilot_service.ensure_active_on_connect(username=username)
        except Exception:
            pass

        # Strategy evaluation for this user
        if (payload.candles and len(payload.candles) >= 20) or (payload.candles_m5 and len(payload.candles_m5) >= 20):
            try:
                from app.services.strategy_engine import strategy_engine
                from app.models.strategy import CandleData

                parsed_candles_m15 = [
                    c if isinstance(c, CandleData) else CandleData(**c) for c in payload.candles
                ]
                parsed_candles_m5 = [
                    c if isinstance(c, CandleData) else CandleData(**c) for c in payload.candles_m5
                ]

                sym_eval = session.chart_symbol or (payload.positions[0].symbol if payload.positions else "XAUUSD")
                cur_quote = session.market_quotes.get(sym_eval.upper())
                current_spread = cur_quote.spread if cur_quote else None

                strategy_engine.evaluate_market(
                    symbol=sym_eval,
                    candles=parsed_candles_m15,
                    candles_m5=parsed_candles_m5,
                    current_spread=current_spread,
                    username=username
                )
            except Exception:
                pass

        # Check Drawdown Guard limit
        try:
            from app.services.autopilot_service import autopilot_service
            is_breached = autopilot_service.check_drawdown(
                current_equity=payload.equity,
                floating_pnl=payload.floating_pnl,
                username=username
            )
            if is_breached:
                lockout_reason = (
                    f"Auto-triggered: Daily Drawdown Guard limit reached "
                    f"({settings.MAX_DAILY_DRAWDOWN_PERCENT}% limit). Trading locked."
                )
                self.trigger_kill_switch(reason=lockout_reason, username=f"system ({username})")
        except Exception:
            pass

        # Dispatch alerts for closed trades
        if closed_positions:
            try:
                from app.services.telegram_service import telegram_service
                for pos in closed_positions:
                    pnl = pos.pnl if pos.pnl != 0 else (pos.profit or 0.0)
                    telegram_service.send_trade_closed_alert_background(
                        ticket=pos.ticket,
                        symbol=pos.symbol,
                        pnl=pnl,
                        reason="TP / SL / Manual Close"
                    )
            except Exception:
                pass

        # Pop pending commands specifically for this user
        with self._lock:
            commands_to_send = list(session.pending_commands)
            session.pending_commands.clear()

        return HeartbeatResponse(
            status="ok",
            server_time=int(current_time),
            commands=commands_to_send
        )

    def submit_order(self, order_req: OrderRequest, username: Optional[str] = None) -> OrderResponse:
        action = order_req.action.upper().strip()
        current_time = int(time.time())
        user_key = self._normalize_user(username)

        with self._lock:
            session = self._get_or_create_session(user_key)
            if session.is_kill_switch_active and action in ("BUY", "SELL"):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Trading engine is locked by emergency Kill Switch ({session.kill_switch_reason or 'Emergency lockdown'}). Disarm Kill Switch before submitting new orders."
                )

        from app.services.autopilot_service import autopilot_service
        if autopilot_service.is_drawdown_locked(username=user_key) and action in ("BUY", "SELL"):
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
                detail=f"Unknown order action: {action}"
            )

        cmd_id = f"cmd_{current_time}_{uuid.uuid4().hex[:6]}"
        command = CommandItem(
            command_id=cmd_id,
            action=action,
            symbol=order_req.symbol,
            volume=order_req.volume,
            sl=order_req.sl,
            tp=order_req.tp,
            ticket=order_req.ticket,
            created_at=current_time
        )

        with self._lock:
            session.pending_commands.append(command)

        return OrderResponse(
            status="queued",
            command_id=cmd_id,
            message=f"Order {action} successfully queued for MT5 bridge execution",
            command=command
        )

    def get_positions(self, username: Optional[str] = None) -> List[PositionItem]:
        current_time = time.time()
        with self._lock:
            session = self._get_or_create_session(username)
            if session.last_received_time is None or session.latest_payload is None:
                return []
            if (current_time - session.last_received_time) > settings.HEARTBEAT_TIMEOUT_SECONDS:
                return []
            return list(session.latest_payload.positions)

    def get_market_quotes(self, username: Optional[str] = None) -> List[MarketQuoteItem]:
        with self._lock:
            session = self._get_or_create_session(username)
            return list(session.market_quotes.values())

    def get_trade_history(self, username: Optional[str] = None) -> TradeHistoryResponse:
        with self._lock:
            session = self._get_or_create_session(username)
            trades = sorted(
                list(session.closed_trades_map.values()),
                key=lambda x: x.close_time or 0,
                reverse=True
            )
            total = len(trades)
            if total == 0:
                return TradeHistoryResponse()

            profits = [t.profit for t in trades]
            net_pnl = round(sum(profits), 2)
            wins = sum(1 for p in profits if p > 0)
            losses = sum(1 for p in profits if p < 0)
            win_rate = round((wins / total) * 100.0, 1) if total > 0 else 0.0

            gross_profit = round(sum(p for p in profits if p > 0), 2)
            gross_loss = round(abs(sum(p for p in profits if p < 0)), 2)
            profit_factor = round(gross_profit / gross_loss, 2) if gross_loss > 0 else (99.99 if gross_profit > 0 else 0.0)

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

    def get_initial_deposit_info(self, username: Optional[str] = None) -> dict:
        with self._lock:
            session = self._get_or_create_session(username)
            eff_deposit = session.get_effective_initial_deposit()
            bal = session.latest_payload.balance if session.latest_payload else (eff_deposit or 0.0)
            eq = session.latest_payload.equity if session.latest_payload else (eff_deposit or 0.0)
            settled_pnl = round(bal - eff_deposit, 2) if eff_deposit else 0.0
            settled_pnl_pct = round((settled_pnl / eff_deposit) * 100.0, 2) if eff_deposit else 0.0
            all_time_pnl = round(eq - eff_deposit, 2) if eff_deposit else 0.0
            all_time_pnl_pct = round((all_time_pnl / eff_deposit) * 100.0, 2) if eff_deposit else 0.0

            source = "override" if session.custom_initial_deposit is not None else ("mt5" if session.mt5_initial_deposit else "default")
            return {
                "status": "success",
                "initial_deposit": eff_deposit,
                "is_overridden": session.custom_initial_deposit is not None,
                "source": source,
                "settled_pnl": settled_pnl,
                "settled_pnl_percent": settled_pnl_pct,
                "all_time_pnl": all_time_pnl,
                "all_time_pnl_percent": all_time_pnl_pct,
                "message": "Initial deposit retrieved successfully."
            }

    def set_initial_deposit_override(self, initial_deposit: Optional[float], username: Optional[str] = None) -> dict:
        user_key = self._normalize_user(username)
        with self._lock:
            session = self._get_or_create_session(user_key)
            if initial_deposit is not None and float(initial_deposit) > 0:
                session.custom_initial_deposit = round(float(initial_deposit), 2)
            else:
                session.custom_initial_deposit = None

        user_service.set_custom_initial_deposit(user_key, session.custom_initial_deposit)
        return self.get_initial_deposit_info(username=user_key)

    def get_equity_curve(self, time_range: str = "1M", username: Optional[str] = None) -> EquityCurveResponse:
        current_time = time.time()
        rng = (time_range or "1M").strip().upper()

        with self._lock:
            session = self._get_or_create_session(username)
            cur_bal = session.latest_payload.balance if session.latest_payload else 0.0
            cur_eq = session.latest_payload.equity if session.latest_payload else cur_bal
            eff_deposit = session.get_effective_initial_deposit() or cur_bal

            if rng in ("DAY", "1D", "D"):
                now_utc = datetime.now(timezone.utc)
                start_ts = int(datetime(now_utc.year, now_utc.month, now_utc.day, tzinfo=timezone.utc).timestamp())
            elif rng in ("WEEK", "1W", "W"):
                start_ts = int(current_time - (7 * 86400))
            elif rng in ("MONTH", "1M", "M"):
                start_ts = int(current_time - (30 * 86400))
            else:
                start_ts = 0

            trades_in_window = [
                t for t in session.closed_trades_map.values()
                if (t.close_time or 0) >= start_ts
            ]
            trades_in_window.sort(key=lambda x: x.close_time or 0)

            total_profit_in_window = sum(t.profit for t in trades_in_window)
            starting_bal_window = round(cur_bal - total_profit_in_window, 2)
            if starting_bal_window <= 0 and eff_deposit > 0:
                starting_bal_window = eff_deposit

            points: List[EquityPointItem] = []
            p0_time = start_ts if start_ts > 0 else (trades_in_window[0].close_time if trades_in_window else int(current_time))
            points.append(EquityPointItem(
                timestamp=p0_time,
                balance=starting_bal_window,
                equity=starting_bal_window
            ))

            running_bal = starting_bal_window
            for t in trades_in_window:
                running_bal = round(running_bal + t.profit, 2)
                points.append(EquityPointItem(
                    timestamp=t.close_time,
                    balance=running_bal,
                    equity=running_bal
                ))

            points.append(EquityPointItem(
                timestamp=int(current_time),
                balance=cur_bal,
                equity=cur_eq
            ))

            equities = [p.equity for p in points]
            peak_eq = max(equities) if equities else cur_eq
            starting_eq = points[0].equity if points else cur_eq

            all_time_pnl = round(cur_eq - eff_deposit, 2) if eff_deposit else 0.0
            roi_percent = round((all_time_pnl / eff_deposit) * 100.0, 2) if eff_deposit else 0.0

            return EquityCurveResponse(
                starting_equity=starting_eq,
                initial_deposit=eff_deposit,
                current_equity=cur_eq,
                peak_equity=peak_eq,
                all_time_pnl=all_time_pnl,
                roi_percent=roi_percent,
                points=points
            )

    def get_status(self, username: Optional[str] = None) -> BridgeStatusResponse:
        current_time = time.time()
        with self._lock:
            session = self._get_or_create_session(username)
            pending_count = len(session.pending_commands)
            eff_deposit = session.get_effective_initial_deposit()
            is_overridden = (session.custom_initial_deposit is not None and session.custom_initial_deposit > 0)
            
            if session.last_received_time is None or session.latest_payload is None:
                return BridgeStatusResponse(
                    is_connected=False,
                    terminal_connected=False,
                    last_heartbeat_at=None,
                    seconds_since_last_heartbeat=None,
                    metrics=None,
                    initial_deposit=eff_deposit,
                    is_deposit_overridden=is_overridden,
                    settled_pnl=0.0,
                    settled_pnl_percent=0.0,
                    all_time_pnl=0.0,
                    all_time_pnl_percent=0.0,
                    positions=[],
                    market_quotes=list(session.market_quotes.values()),
                    chart_symbol=session.chart_symbol,
                    closed_trades_count=len(session.closed_trades_map),
                    pending_commands_count=pending_count,
                    is_kill_switch_active=session.is_kill_switch_active,
                    kill_switch_reason=session.kill_switch_reason,
                    kill_switch_time=session.kill_switch_time
                )
            
            diff = current_time - session.last_received_time
            is_active = (diff <= settings.HEARTBEAT_TIMEOUT_SECONDS)
            positions = list(session.latest_payload.positions) if is_active else []
            
            bal = session.latest_payload.balance
            eq = session.latest_payload.equity
            settled_pnl = round(bal - eff_deposit, 2) if eff_deposit else 0.0
            settled_pnl_pct = round((settled_pnl / eff_deposit) * 100.0, 2) if eff_deposit else 0.0
            all_time_pnl = round(eq - eff_deposit, 2) if eff_deposit else 0.0
            all_time_pnl_pct = round((all_time_pnl / eff_deposit) * 100.0, 2) if eff_deposit else 0.0

            return BridgeStatusResponse(
                is_connected=is_active,
                terminal_connected=session.latest_payload.terminal_connected if is_active else False,
                last_heartbeat_at=int(session.last_received_time),
                seconds_since_last_heartbeat=round(diff, 2),
                metrics=session.latest_payload,
                initial_deposit=eff_deposit,
                is_deposit_overridden=is_overridden,
                settled_pnl=settled_pnl,
                settled_pnl_percent=settled_pnl_pct,
                all_time_pnl=all_time_pnl,
                all_time_pnl_percent=all_time_pnl_pct,
                positions=positions,
                market_quotes=list(session.market_quotes.values()),
                chart_symbol=session.chart_symbol,
                closed_trades_count=len(session.closed_trades_map),
                pending_commands_count=pending_count,
                is_kill_switch_active=session.is_kill_switch_active,
                kill_switch_reason=session.kill_switch_reason,
                kill_switch_time=session.kill_switch_time
            )


bridge_service = BridgeService()
