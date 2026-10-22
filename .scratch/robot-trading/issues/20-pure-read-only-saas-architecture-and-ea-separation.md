# 20: Pure Read-Only SaaS Telemetry Architecture and EA Separation

**What to build:** Refactor TradeGear into a 100% pure read-only SaaS monitoring, journal, and risk watchdog platform by completely separating the MT5 bridge from trading execution. Convert the MT5 connection client into an ultra-lightweight `TradeGearMonitor.mq5` telemetry-only EA with zero order placement, order modification, or kill switch capabilities, while decoupling robot trading strategies into standalone EAs ready for independent user execution and future marketplace distribution.

**Blocked by:** 19 (User-Isolated MT5 Bridge Architecture and Authentication Security Hardening)

**Status:** done

## Problem Statement

TradeGear currently couples real-time account telemetry reporting with trading execution capabilities (autonomous order placement, SL/TP enforcement, breakeven, trailing stops, and emergency kill-switch position liquidation) inside a single monolithic MT5 bridge client (`BridgeEA.mq5`) and backend command dispatch queue. In a commercial Software-as-a-Service (SaaS) model, maintaining order execution and liquidation capabilities introduces severe legal, regulatory, and financial liability: if broker slippage occurs, internet latency delays execution, or market volatility causes liquidation during normal retracements, the SaaS platform operator is exposed to user disputes and blame for trading losses. 

Furthermore, professional traders and Prop Firm account managers (managing $50k-$200k accounts on FTMO, FundedNext, etc.) are deeply hesitant to attach third-party software that possesses live trade execution or position modification permissions to their accounts. Traders already have their own preferred Expert Advisors (or trade manually) and desire an independent, beautiful, mobile-friendly analytics dashboard, automated trading journal, and passive risk watchdog without having third-party software interfere with or alter their active trades.

## Solution

Transform TradeGear into a 100% Pure Read-Only SaaS Monitoring, Analytics, and Journal Platform. The bridge between MT5 and TradeGear becomes strictly unidirectional for telemetry and passive observation:

1. **Lightweight Pure Read-Only MT5 Monitor (`TradeGearMonitor.mq5`)**: The client-side EA is stripped of all trade execution logic (`CTrade`, order opening, order closing, SL/TP modification, breakeven protection, and trailing stops). It acts solely as an unobtrusive telemetry sensor that transmits account balances, equity, margin levels, active positions, deal history, and live quotes to TradeGear via standard HTTP WebRequest. It requires zero live trading permissions on the user's terminal.
2. **De-coupled Trading Robot EAs**: Proprietary trading strategies are packaged as separate, standalone EA files. Traders run their own EAs (or TradeGear Marketplace EAs) on designated charts, while `TradeGearMonitor` runs quietly on any single chart to observe and analyze the overall account in real time.
3. **Passive Risk Watchdog & Smart Alerts (Zero-Execution Risk Management)**: The Drawdown Guard and Risk Hub pivot from active order cancellation/kill-switch liquidation to proactive alerting (instant Telegram alerts and dashboard push warnings when drawdown or margin thresholds are breached), leaving all execution decisions safely in the trader's hands.
4. **Clean API & Backend Removal of Command Queues**: Backend endpoints and services permanently retire order queueing, manual order submission, and kill-switch execution routes, ensuring zero risk of accidental trade liquidation.

## User Stories

1. As a TradeGear SaaS subscriber, I want the MT5 bridge EA to be 100% read-only, so that I can be completely confident that the software will never open, modify, or close trades on my broker account.
2. As a TradeGear SaaS subscriber, I want to use my own custom EA or manual trading strategy on MT5, so that I am not forced to use TradeGear's built-in trading algorithms.
3. As a Prop Firm trader, I want to attach `TradeGearMonitor` to my funded evaluation account without granting live trading permissions, so that I comply with strict prop firm compliance rules.
4. As a TradeGear SaaS subscriber, I want to see real-time balance, equity, and floating P/L on my web dashboard, so that I can monitor my account health from my mobile phone or laptop.
5. As a TradeGear SaaS subscriber, I want all active positions from all my other EAs to be tracked in TradeGear's live positions table, so that I have a unified overview of all my open exposure.
6. As a TradeGear SaaS subscriber, I want my historical closed trades to be automatically synchronized and journaled, so that I can analyze win rate, profit factor, and trade performance metrics.
7. As a TradeGear SaaS subscriber, I want an automated Telegram alert when my daily floating loss reaches a predefined drawdown threshold, so that I can manually intervene before hitting broker limits without the platform closing my trades.
8. As a TradeGear SaaS subscriber, I want margin level warning alerts when my free margin drops below safe levels, so that I can protect my account from margin calls.
9. As a TradeGear SaaS subscriber, I want the MT5 monitor EA to consume virtually zero CPU and RAM on my VPS or laptop, so that my other trading robots execute with maximum performance and minimal latency.
10. As a TradeGear SaaS subscriber, I want to attach `TradeGearMonitor` to just a single chart, so that I do not need to configure bridge settings on every chart I trade.
11. As a TradeGear SaaS subscriber, I want clear visual confirmation on the MT5 chart HUD that the monitor is operating in "Read-Only Telemetry Mode", so that I have peace of mind regarding safety.
12. As a TradeGear SaaS operator, I want the system to have zero trade execution capability, so that my business is completely protected against financial and legal liability from user trading losses or broker execution slippage.
13. As a TradeGear SaaS operator, I want the backend API to reject any trade submission or order modification requests, so that unauthorized external actors cannot manipulate user trading terminals.
14. As a TradeGear SaaS operator, I want a clean separation between the monitoring bridge and trading robots, so that I can offer standalone robot EAs as separate add-on products in the future marketplace.
15. As a TradeGear SaaS subscriber, I want to browse and download optional TradeGear robot EAs in the future, so that I can deploy automated strategies alongside the monitor if I choose to.
16. As a TradeGear SaaS subscriber, I want my initial balance benchmark to calculate all-time return trajectories, so that I can evaluate account growth irrespective of how many different EAs contributed to the profits.
17. As a TradeGear SaaS subscriber, I want daily and weekly performance curves to reflect my total portfolio equity trajectory, so that I can evaluate day-to-day risk consistency.
18. As a TradeGear SaaS subscriber, I want to be able to pause or disconnect telemetry at any time by simply removing `TradeGearMonitor` from MT5, so that I retain full sovereign control over my terminal data.

## Implementation Decisions

- **Single Seam Principle**: All client-server interactions remain strictly defined at the top-level HTTP REST boundary. The backend operates as an authenticated telemetry receiver and analytics engine.
- **Client EA Refactoring (`TradeGearMonitor.mq5`)**:
  - Deprecate monolithic execution logic in favor of a dedicated `TradeGearMonitor.mq5`.
  - Remove `#include <Trade\Trade.mqh>`, `CTrade g_trade`, SL/TP calculation routines, breakeven triggers, trailing stop adjustments, and order execution loops.
  - Retain WinINet HTTP WebRequest telemetry dispatching: account balance, equity, margin, free margin, margin level, floating P/L, active positions, deal history, quotes, and chart symbol.
  - The MT5 chart HUD explicitly displays `[TradeGear Monitor] Status: Active (Read-Only Telemetry)`.
- **Standalone Strategy Robot Packaging**:
  - Move the built-in trend confluence strategy (EMA + RSI) into a standalone expert advisor template (`TradeGearConfluenceRobot.mq5`).
  - This robot EA focuses purely on market execution with its own Magic Number, SL/TP parameters, and lot management, completely independent of the web monitor.
- **Backend API & Service Decoupling**:
  - Permanently remove or disarm `/api/v1/bridge/order`, `/api/v1/risk/kill-switch`, and `/api/v1/risk/unlock` execution endpoints.
  - In `bridge_service`, remove `pending_commands` dispatching from heartbeat processing; heartbeat responses return pure telemetry acknowledgments (`status: "ok"`).
  - Transform AutoPilot and Drawdown Guard into passive observation and alerting services:
    - Instead of locking order execution or closing positions, Drawdown Guard status flags an account state as `DRAWDOWN_WARNING` or `DRAWDOWN_BREACHED`.
    - Telegram Service dispatches high-priority alert notifications to the user without attempting to alter trades.
- **Frontend Dashboard Alignment**:
  - Remove all remaining execution elements (Kill Switch buttons, order submission modal triggers, close-all actions).
  - Update Drawdown Guard cards and Home command center to present passive risk telemetry ("Risk Watchdog / Alert Threshold") rather than an active order-blocking lockout.
  - Update MT5 Connection Modal to guide users on installing `TradeGearMonitor.mq5` with emphasis on its 100% Read-Only, zero-risk architecture.

## Testing Decisions

- **What makes a good test**: Tests must verify observable system behavior from external seams (HTTP API requests and responses) without relying on internal private attributes.
- **Testing Scenarios**:
  - Verify heartbeat processing accepts and persists telemetry without returning any execution commands in the response.
  - Verify that attempting to invoke order placement or kill-switch execution endpoints returns HTTP 404 (Not Found) or HTTP 403 (Forbidden - Pure Read-Only System).
  - Verify Drawdown Guard detects drawdown breach and triggers alert status and notification events without attempting order liquidation.
  - Verify multi-tenant telemetry isolation remains intact across distinct user accounts and tokens.
  - Verify frontend production build succeeds with all execution triggers safely removed.
- **Prior Art**: Builds on the existing test suite in `backend/tests/test_bridge.py`, `backend/tests/test_risk.py`, and `backend/tests/test_auth.py`.

## Out of Scope

- Marketplace payment processing and digital rights management (DRM) for selling third-party EAs (deferred to future marketplace issue).
- Copy-trading or multi-account trade mirror networks between different MT5 terminals.
- Web-based broker deposits, withdrawals, or password changes.

## Further Notes

- By adopting a 100% read-only architecture, TradeGear positions itself alongside premier institutional analytics tools like TradeZella and Myfxbook, making it vastly more attractive and safe for prop firm and retail traders alike.
