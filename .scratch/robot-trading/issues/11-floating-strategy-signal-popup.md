# 11: Floating Strategy Signal Recommendation Popup

**What to build:** Move strategy signal recommendations from the main page body into a floating bottom-right widget. Displays a pulsating trigger pill showing the count of available signals. Clicking or new signal arrivals expand a semi-transparent floating card allowing traders to review technical confluence (EMA/RSI), execute 1-click semi-auto approval to MT5, dismiss signals, simulate test signals, and view AutoPilot status.

**Blocked by:** 09 (TradeGear Design Tokens, App Shell & Responsive Navigation)

**Status:** done

- [x] Floating trigger pill appears at bottom-right (positioned safely above bottom nav on mobile viewports)
- [x] Pulse animation alerts the trader when active strategy signals are waiting for review
- [x] Expanded floating popup displays confluence indicators, lot size, direction, and TP/SL levels
- [x] One-click approve button executes market order via MT5 bridge API and updates telemetry
- [x] Dismiss button discards signal; simulate button generates test confluence signal
- [x] AutoPilot mode toggle is visible with indicator badge
