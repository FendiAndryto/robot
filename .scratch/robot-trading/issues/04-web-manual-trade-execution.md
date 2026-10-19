# 04: Web-Triggered Manual Trade Execution

**What to build:** An interactive trading widget on the web dashboard where the user selects a symbol (e.g., EURUSD, XAUUSD), lot size, and clicks "Buy" or "Sell". The backend queues the trade, the MT5 EA executes the order with Stop Loss and Take Profit, and the newly opened trade appears in the live position table on the web UI.

**Blocked by:** 03 (Authentication & Connection Dashboard Slice)

**Status:** done

- [x] Web UI order form with Symbol, Lot Size, Buy/Sell actions, and optional SL/TP fields
- [x] Backend dispatches execution command to MT5 EA via local bridge
- [x] EA successfully executes `OrderSend()` and returns ticket ID, open price, and timestamp
- [x] Web dashboard shows the new open trade in a live positions table with a functional "Close Position" button

