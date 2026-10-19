# 12: Quick-Action Slide-over Order Execution Drawer

**What to build:** An intuitive slide-over drawer (or mobile bottom-sheet) triggered by a prominent "+ New Trade" button on Home and header. Contains the complete manual order form with quick symbol picker, lot size presets, dynamic pip risk calculator linked to current equity, stop loss & take profit inputs, and one-click BUY/SELL execution directly to the MT5 terminal.

**Blocked by:** 10 (Home Command Center & Live Telemetry KPIs)

**Status:** done

- [x] "+ New Trade" button in header and Home screen smoothly opens order execution drawer
- [x] Quick symbol selector presets (EURUSD, GBPUSD, USDJPY, XAUUSD, BTCUSD) and custom input
- [x] Risk calculator computes recommended lot sizes from risk percentage and stop-loss pips based on live equity
- [x] Direct BUY and SELL execution submits orders to `/api/v1/orders/` with feedback
- [x] Drawer closes gracefully with ESC key, backdrop click, or close button
- [x] Kill Switch lockout prevents order submission if engine is locked
