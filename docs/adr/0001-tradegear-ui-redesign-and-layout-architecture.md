# 0001. TradeGear UI Redesign and Layout Architecture

## Context
The initial dashboard had all functional widgets (telemetry, connection alerts, drawdown guards, metric cards, order form, signals panel, and positions table) vertically stacked on a single scrollable page. This caused visual clutter ("terlalu rame") and poor mobile ergonomics. The user requested adopting a clean, dark-emerald aesthetic inspired by the provided prototype, renaming the application to **TradeGear**, using the tab window favicon logo, setting AI Assistant and Replay to "Coming Soon", and converting strategy signals into a floating popup widget.

## Decision
We adopt a tabbed progressive-disclosure architecture matching the prototype design system:
1. **Navigation Structure**: 6 primary tabs (`Home`, `Journal`, `Market`, `AI Assistant [Coming Soon]`, `Replay [Coming Soon]`, `Profile`), with top navigation on desktop and a fixed bottom navigation bar on mobile.
2. **Branding**: Renamed to **TradeGear** with the SVG logo from `/favicon.svg` and dark-teal/emerald palette (`#080f14`, `#45e0ad`, `#29404a`).
3. **Floating Strategy Signal Widget**: Decouple `SignalsPanel` from page flow into a floating toast/popup widget positioned at the bottom-right (above the mobile bottom nav), allowing traders to approve or dismiss signals from any screen without visual clutter.
4. **Execution & Risk Placement**:
   - Order execution (`OrderForm` with Risk Calculator) is accessible via a high-visibility quick-action "New Trade" button on `Home` that opens a slide-over drawer / modal.
   - Risk management telemetry (`DrawdownGuardCard`, Kill Switch, latency, broker diagnostics) is consolidated into the `Profile` tab and critical top banners when safety thresholds are breached.
