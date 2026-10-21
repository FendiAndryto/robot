# 0002. Initial Deposit Baseline and Account Performance Curve Reconstruction

## Context
Traders need to clearly evaluate their true net profitability (All-Time P/L and ROI %) from the moment capital was funded, compared to their current live balance and equity. Additionally, the existing performance chart only held transient in-memory polling snapshots that were lost upon server restart and could not display historical trades executed prior to bridge connection.

## Decision
1. **Initial Deposit Tracking**: Adopt a hybrid source of truth:
   - MT5 telemetry automatically extracts the earliest funding balance deal (`DEAL_TYPE_BALANCE` where profit > 0).
   - If historical broker deals are unavailable or truncated, traders can set or override their `Initial Deposit` via an inline quick-edit modal on the Total Balance card or Profile tab, persisted in `backend/app/data/account_settings.json`.
2. **Account Performance Curve Reconstruction**:
   - Instead of volatile time-series polling snapshots, the equity/balance curve is deterministically reconstructed starting from `Initial Deposit` (or balance at period start) and incremented/decremented chronologically by each recorded closed trade (`closed_trades`).
   - The final curve point is always tied to real-time `Account Equity`.
   - Time filters are standardized to `Day`, `Week`, and `Month`.
3. **Dashboard Layout Ergonomics**:
   - Swap `Live Market Feed` with `Active Trades` in the top 2-column grid.
   - Account Performance (growth chart) and Active Trades (open positions with instant close controls) now sit side-by-side above the fold, ensuring immediate execution oversight without scrolling.
   - Live Market Feed moves below the grid as a clean horizontal ticker/summary.
