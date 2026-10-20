import time
import uuid
import threading
from datetime import datetime, timezone
from typing import List, Dict, Optional
from fastapi import HTTPException, status
from app.core.config import settings
from app.models.strategy import (
    CandleData,
    IndicatorValues,
    SignalItem,
    StrategyConfigResponse,
    TestSignalRequest,
)
from app.models.bridge import OrderRequest
from app.models.risk import LotCalculationRequest
from app.services.risk_service import risk_service
from app.services.bridge_service import bridge_service


class StrategyEngine:
    def __init__(self):
        self._lock = threading.Lock()
        # In-memory store for active & past signals: signal_id -> SignalItem
        self._signals: Dict[str, SignalItem] = {}
        # Cooldown tracker to prevent duplicate signal flood: symbol -> last_signal_time
        self._last_signal_time: Dict[str, float] = {}

    def reset_state(self):
        """Reset internal signal state (for tests)."""
        with self._lock:
            self._signals.clear()
            self._last_signal_time.clear()

    @staticmethod
    def calculate_ema(prices: List[float], period: int) -> List[float]:
        if len(prices) < period:
            return []
        ema = []
        multiplier = 2.0 / (period + 1)
        # Seed with Simple Moving Average of first 'period' elements
        sma = sum(prices[:period]) / period
        ema.append(sma)
        for price in prices[period:]:
            ema.append(price * multiplier + ema[-1] * (1.0 - multiplier))
        return ema

    @staticmethod
    def calculate_rsi(prices: List[float], period: int = 14) -> List[float]:
        if len(prices) <= period:
            return []

        deltas = [prices[i] - prices[i - 1] for i in range(1, len(prices))]
        gains = [max(d, 0.0) for d in deltas]
        losses = [max(-d, 0.0) for d in deltas]

        # Initial average gain & loss
        avg_gain = sum(gains[:period]) / period
        avg_loss = sum(losses[:period]) / period

        rsi_list = []
        if avg_loss == 0.0:
            rsi_list.append(100.0)
        else:
            rs = avg_gain / avg_loss
            rsi_list.append(100.0 - (100.0 / (1.0 + rs)))

        for i in range(period, len(deltas)):
            avg_gain = (avg_gain * (period - 1) + gains[i]) / period
            avg_loss = (avg_loss * (period - 1) + losses[i]) / period

            if avg_loss == 0.0:
                rsi_list.append(100.0)
            else:
                rs = avg_gain / avg_loss
                rsi_list.append(round(100.0 - (100.0 / (1.0 + rs)), 2))

        return rsi_list

    def evaluate_candles(
        self,
        symbol: str,
        candles: List[CandleData],
        candles_m5: Optional[List[CandleData]] = None,
        live_equity: Optional[float] = None,
        current_spread: Optional[int] = None,
        ignore_session_filter: bool = False
    ) -> Optional[SignalItem]:
        if not settings.STRATEGY_ENABLED:
            return None

        # 1. Spread Guard: protect scalper against excessive spread or news spikes
        if current_spread is not None and current_spread > settings.MAX_SPREAD_POINTS:
            return None

        # 2. Session Filter: prioritize high-liquidity London/NY overlap, skip rollover gap
        if not ignore_session_filter and settings.STRATEGY_ENABLE_SESSION_FILTER:
            current_hour_utc = datetime.now(timezone.utc).hour
            start_h = settings.STRATEGY_SESSION_START_HOUR_UTC
            end_h = settings.STRATEGY_SESSION_END_HOUR_UTC
            if start_h <= end_h:
                in_session = start_h <= current_hour_utc < end_h
            else:
                in_session = current_hour_utc >= start_h or current_hour_utc < end_h
            if not in_session:
                return None

        sym = symbol.strip()
        min_bars = max(settings.STRATEGY_EMA_SLOW, settings.STRATEGY_RSI_PERIOD) + 5

        # Multi-timeframe Scalping: M15 Trend Bias + M5 Entry Trigger
        use_m5 = candles_m5 is not None and len(candles_m5) >= min_bars
        target_candles = candles_m5 if use_m5 else candles
        if len(target_candles) < min_bars:
            return None

        closes = [c.close if hasattr(c, "close") else c["close"] for c in target_candles]
        ema_fast = self.calculate_ema(closes, settings.STRATEGY_EMA_FAST)
        ema_slow = self.calculate_ema(closes, settings.STRATEGY_EMA_SLOW)
        rsi = self.calculate_rsi(closes, settings.STRATEGY_RSI_PERIOD)

        if not ema_fast or not ema_slow or not rsi:
            return None

        fast_now = ema_fast[-1]
        slow_now = ema_slow[-1]
        rsi_now = rsi[-1]
        price_now = closes[-1]

        # Check Higher Timeframe (M15) Trend Bias if candles provided
        m15_bullish = True
        m15_bearish = True
        if use_m5 and len(candles) >= min_bars:
            m15_closes = [c.close if hasattr(c, "close") else c["close"] for c in candles]
            m15_fast = self.calculate_ema(m15_closes, settings.STRATEGY_EMA_FAST)
            m15_slow = self.calculate_ema(m15_closes, settings.STRATEGY_EMA_SLOW)
            if m15_fast and m15_slow:
                m15_bullish = m15_fast[-1] > m15_slow[-1]
                m15_bearish = m15_fast[-1] < m15_slow[-1]

        action = None
        reason = ""
        trend = "NEUTRAL"

        is_bullish_trigger = fast_now > slow_now and m15_bullish
        is_bearish_trigger = fast_now < slow_now and m15_bearish

        if is_bullish_trigger:
            trend = "BULLISH"
            if settings.STRATEGY_RSI_OVERSOLD <= rsi_now <= settings.STRATEGY_RSI_OVERBOUGHT:
                action = "BUY"
                reason = (
                    f"Scalp Confluence: M15 Bullish Bias + M5 EMA({settings.STRATEGY_EMA_FAST}) > "
                    f"EMA({settings.STRATEGY_EMA_SLOW}) with RSI @ {rsi_now:.1f}"
                    if use_m5 else
                    f"Trend Confluence: EMA({settings.STRATEGY_EMA_FAST}) {fast_now:.5f} > "
                    f"EMA({settings.STRATEGY_EMA_SLOW}) {slow_now:.5f} with RSI @ {rsi_now:.1f}"
                )
        elif is_bearish_trigger:
            trend = "BEARISH"
            if settings.STRATEGY_RSI_OVERSOLD <= rsi_now <= settings.STRATEGY_RSI_OVERBOUGHT:
                action = "SELL"
                reason = (
                    f"Scalp Confluence: M15 Bearish Bias + M5 EMA({settings.STRATEGY_EMA_FAST}) < "
                    f"EMA({settings.STRATEGY_EMA_SLOW}) with RSI @ {rsi_now:.1f}"
                    if use_m5 else
                    f"Trend Confluence: EMA({settings.STRATEGY_EMA_FAST}) {fast_now:.5f} < "
                    f"EMA({settings.STRATEGY_EMA_SLOW}) {slow_now:.5f} with RSI @ {rsi_now:.1f}"
                )

        if not action:
            return None

        # Check signal cooldown (prevent flood on same symbol within 60s)
        current_time = int(time.time())
        with self._lock:
            last_time = self._last_signal_time.get(sym, 0)
            if current_time - last_time < 60:
                return None
            self._last_signal_time[sym] = current_time

        # Calculate SL / TP and position size
        pip_size = risk_service.get_pip_size(sym)
        sl_pips = settings.STRATEGY_DEFAULT_SL_PIPS
        tp_pips = sl_pips * settings.STRATEGY_DEFAULT_RR_RATIO

        if action == "BUY":
            sl_price = round(price_now - (sl_pips * pip_size), 5)
            tp_price = round(price_now + (tp_pips * pip_size), 5)
        else:
            sl_price = round(price_now + (sl_pips * pip_size), 5)
            tp_price = round(price_now - (tp_pips * pip_size), 5)

        lot_calc = risk_service.calculate_lot(
            LotCalculationRequest(
                symbol=sym,
                stop_loss_pips=sl_pips,
                risk_percent=settings.DEFAULT_RISK_PER_TRADE_PERCENT,
                equity=live_equity,
                market_price=price_now
            ),
            live_equity=live_equity
        )

        signal_id = f"sig_{current_time}_{sym.lower()}_{action.lower()}_{uuid.uuid4().hex[:4]}"
        signal = SignalItem(
            signal_id=signal_id,
            id=signal_id,
            symbol=sym,
            action=action,
            entry_price=round(price_now, 5),
            sl=sl_price,
            tp=tp_price,
            sl_pips=sl_pips,
            tp_pips=tp_pips,
            risk_reward=f"1:{settings.STRATEGY_DEFAULT_RR_RATIO:.1f}",
            recommended_lot=lot_calc.calculated_lot,
            risk_amount=lot_calc.risk_amount,
            reason=reason,
            indicators=IndicatorValues(
                ema_fast=round(fast_now, 5),
                ema_slow=round(slow_now, 5),
                rsi=round(rsi_now, 2),
                trend=trend
            ),
            status="PENDING",
            created_at=current_time,
            expires_at=current_time + settings.STRATEGY_SIGNAL_TTL_SECONDS
        )

        with self._lock:
            self._signals[signal_id] = signal

        # Autonomous Auto-Pilot Execution Hook
        from app.services.autopilot_service import autopilot_service
        is_auto_active = autopilot_service.is_autopilot_active() and not autopilot_service.is_drawdown_locked()
        if is_auto_active:
            try:
                self.approve_signal(signal_id)
                autopilot_service.increment_auto_executed_count()
                signal.reason += " [AUTOPILOT AUTO-EXECUTED]"
            except Exception:
                pass

        # Dispatch Telegram signal alert
        try:
            from app.services.telegram_service import telegram_service
            telegram_service.send_signal_alert_background({
                "action": signal.action,
                "symbol": signal.symbol,
                "confidence": 0.88,
                "current_price": signal.entry_price,
                "suggested_sl": signal.sl,
                "suggested_tp": signal.tp,
                "status": "APPROVED" if is_auto_active else "PENDING",
                "is_autopilot": is_auto_active
            })
        except Exception:
            pass

        return signal

    def create_custom_signal(
        self,
        req: TestSignalRequest,
        live_equity: Optional[float] = None
    ) -> SignalItem:
        current_time = int(time.time())
        sym = req.symbol.upper().strip()
        action = req.action.upper().strip()
        if action not in ("BUY", "SELL"):
            action = "BUY"

        # Determine price default if not provided
        pip_size = risk_service.get_pip_size(sym)
        if req.price and req.price > 0:
            entry_price = req.price
        else:
            if "JPY" in sym:
                entry_price = 152.450
            elif "XAU" in sym or "GOLD" in sym:
                entry_price = 2735.50
            elif "BTC" in sym:
                entry_price = 68450.0
            else:
                entry_price = 1.08650

        sl_pips = req.sl_pips if (req.sl_pips and req.sl_pips > 0) else settings.STRATEGY_DEFAULT_SL_PIPS
        rr_ratio = req.rr_ratio if (req.rr_ratio and req.rr_ratio > 0) else settings.STRATEGY_DEFAULT_RR_RATIO
        tp_pips = sl_pips * rr_ratio

        if action == "BUY":
            sl_price = round(entry_price - (sl_pips * pip_size), 5)
            tp_price = round(entry_price + (tp_pips * pip_size), 5)
            fast_ema = entry_price * 1.0008
            slow_ema = entry_price * 0.9995
            rsi_val = 54.2
            trend = "BULLISH"
            reason = f"Confluence detected: EMA({settings.STRATEGY_EMA_FAST}) Golden Cross over EMA({settings.STRATEGY_EMA_SLOW}) with RSI({settings.STRATEGY_RSI_PERIOD}) @ {rsi_val} Bullish Momentum."
        else:
            sl_price = round(entry_price + (sl_pips * pip_size), 5)
            tp_price = round(entry_price - (tp_pips * pip_size), 5)
            fast_ema = entry_price * 0.9992
            slow_ema = entry_price * 1.0005
            rsi_val = 46.8
            trend = "BEARISH"
            reason = f"Confluence detected: EMA({settings.STRATEGY_EMA_FAST}) Death Cross below EMA({settings.STRATEGY_EMA_SLOW}) with RSI({settings.STRATEGY_RSI_PERIOD}) @ {rsi_val} Bearish Momentum."

        lot_calc = risk_service.calculate_lot(
            LotCalculationRequest(
                symbol=sym,
                stop_loss_pips=sl_pips,
                risk_percent=settings.DEFAULT_RISK_PER_TRADE_PERCENT,
                equity=live_equity,
                market_price=entry_price
            ),
            live_equity=live_equity
        )

        signal_id = f"sig_{current_time}_{sym.lower()}_{action.lower()}_{uuid.uuid4().hex[:4]}"
        signal = SignalItem(
            signal_id=signal_id,
            id=signal_id,
            symbol=sym,
            action=action,
            entry_price=round(entry_price, 5),
            sl=sl_price,
            tp=tp_price,
            sl_pips=round(sl_pips, 1),
            tp_pips=round(tp_pips, 1),
            risk_reward=f"1:{rr_ratio:.1f}",
            recommended_lot=lot_calc.calculated_lot,
            risk_amount=lot_calc.risk_amount,
            reason=reason,
            indicators=IndicatorValues(
                ema_fast=round(fast_ema, 5),
                ema_slow=round(slow_ema, 5),
                rsi=rsi_val,
                trend=trend
            ),
            status="PENDING",
            created_at=current_time,
            expires_at=current_time + settings.STRATEGY_SIGNAL_TTL_SECONDS
        )

        with self._lock:
            self._signals[signal_id] = signal

        # Autonomous Auto-Pilot Execution Hook
        from app.services.autopilot_service import autopilot_service
        is_auto_active = autopilot_service.is_autopilot_active() and not autopilot_service.is_drawdown_locked()
        if is_auto_active:
            try:
                self.approve_signal(signal_id)
                autopilot_service.increment_auto_executed_count()
                signal.reason += " [AUTOPILOT AUTO-EXECUTED]"
            except Exception:
                pass

        # Dispatch Telegram signal alert
        try:
            from app.services.telegram_service import telegram_service
            telegram_service.send_signal_alert_background({
                "action": signal.action,
                "symbol": signal.symbol,
                "confidence": 0.85,
                "current_price": signal.entry_price,
                "suggested_sl": signal.sl,
                "suggested_tp": signal.tp,
                "status": "APPROVED" if is_auto_active else "PENDING",
                "is_autopilot": is_auto_active
            })
        except Exception:
            pass

        return signal

    def get_signals(self, include_all: bool = False) -> List[SignalItem]:
        current_time = int(time.time())
        with self._lock:
            # Auto-expire pending signals whose TTL has passed
            for sig in self._signals.values():
                if sig.status == "PENDING" and current_time > sig.expires_at:
                    sig.status = "EXPIRED"

            if include_all:
                return sorted(self._signals.values(), key=lambda s: s.created_at, reverse=True)

            # Return only PENDING non-expired signals
            pending = [s for s in self._signals.values() if s.status == "PENDING"]
            return sorted(pending, key=lambda s: s.created_at, reverse=True)

    def approve_signal(self, signal_id: str, custom_lot: Optional[float] = None) -> dict:
        with self._lock:
            signal = self._signals.get(signal_id)
            if not signal:
                for s in self._signals.values():
                    if getattr(s, "id", None) == signal_id or s.signal_id == signal_id:
                        signal = s
                        break
            if not signal:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Signal with ID '{signal_id}' not found."
                )

            if signal.status != "PENDING":
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Cannot approve signal. Current status is '{signal.status}'."
                )

            current_time = int(time.time())
            if current_time > signal.expires_at:
                signal.status = "EXPIRED"
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Cannot approve signal. Signal has expired."
                )

            lot_to_execute = custom_lot if (custom_lot and custom_lot > 0) else signal.recommended_lot

        # Submit order through bridge pipeline
        order_req = OrderRequest(
            action=signal.action,
            symbol=signal.symbol,
            volume=lot_to_execute,
            sl=signal.sl,
            tp=signal.tp
        )
        order_res = bridge_service.submit_order(order_req)

        with self._lock:
            signal.status = "APPROVED"

        return {
            "status": "approved",
            "signal": signal,
            "order": order_res,
            "message": f"Signal {signal.signal_id} approved. Executed {signal.action} {lot_to_execute} lots of {signal.symbol} to MT5."
        }

    def dismiss_signal(self, signal_id: str, reason: str = "Manual dismissal") -> dict:
        with self._lock:
            signal = self._signals.get(signal_id)
            if not signal:
                for s in self._signals.values():
                    if getattr(s, "id", None) == signal_id or s.signal_id == signal_id:
                        signal = s
                        break
            if not signal:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Signal with ID '{signal_id}' not found."
                )

            if signal.status != "PENDING":
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Cannot dismiss signal. Current status is '{signal.status}'."
                )

            signal.status = "DISMISSED"

        return {
            "status": "dismissed",
            "signal_id": signal_id,
            "reason": reason,
            "message": f"Signal {signal_id} dismissed."
        }

    def get_config(self) -> StrategyConfigResponse:
        monitored = [s.strip().upper() for s in settings.STRATEGY_MONITORED_SYMBOLS.split(",") if s.strip()]
        return StrategyConfigResponse(
            enabled=settings.STRATEGY_ENABLED,
            ema_fast=settings.STRATEGY_EMA_FAST,
            ema_slow=settings.STRATEGY_EMA_SLOW,
            rsi_period=settings.STRATEGY_RSI_PERIOD,
            rsi_oversold=settings.STRATEGY_RSI_OVERSOLD,
            rsi_overbought=settings.STRATEGY_RSI_OVERBOUGHT,
            default_sl_pips=settings.STRATEGY_DEFAULT_SL_PIPS,
            default_rr_ratio=settings.STRATEGY_DEFAULT_RR_RATIO,
            signal_ttl_seconds=settings.STRATEGY_SIGNAL_TTL_SECONDS,
            monitored_symbols=monitored
        )


strategy_engine = StrategyEngine()
