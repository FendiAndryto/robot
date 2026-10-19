# 06: Strategy Engine & Semi-Auto Signal Approval

**What to build:** An automated technical analysis engine in the backend that calculates indicators (e.g., EMA Trend & RSI Momentum) on live candle streams. When a confluence signal occurs, a recommendation card appears on the web dashboard with entry, recommended lot, SL, and TP. Clicking "Approve" fires the trade to MT5, while clicking "Dismiss" ignores it.

**Blocked by:** 05 (Risk Calculator & Emergency Kill Switch)

**Status:** done

- [x] Backend worker evaluates incoming market quotes against defined strategy rules
- [x] Detected setups generate a signal event broadcasted to the web dashboard in real-time
- [x] Signal Card shows Pair, Direction, Entry Price, Reason/Indicators, SL, and TP
- [x] Clicking "Approve" triggers the full execution pipeline into MT5; clicking "Dismiss" clears the card
