# TradeGear

A real-time algorithmic trading web application bridging MetaTrader 5 (MT5) with FastAPI backend, telemetry monitoring, strategy signals, automated risk management, and journal analytics. The system operates strictly as a **Full-Auto Trading Robot & Telemetry Dashboard** (no manual order execution, no manual order close, no manual SL/TP modification, and no broker deposit/withdrawal transactions).

## Language

**TradeGear**:
The unified web application brand and interface for monitoring accounts, tracking robot performance, analyzing journals, and viewing MT5 bridge telemetry.
_Avoid_: Robot Trading Dashboard, MT5 Connection Dashboard, Broker Portal

**Full-Auto Robot Trading**:
The core architecture where trade entries, exits, lot sizing, Stop Loss, and Take Profit are managed exclusively by autonomous algorithmic strategies (AutoPilot) inside the robot engine. The web application functions strictly for analytics, telemetry, and monitoring without broker order-routing or manual trade buttons.
_Avoid_: Semi-Auto, Manual Trading Desk, Web Broker

**Bridge Status**:
The live telemetry health state between the FastAPI backend and the MT5 Expert Advisor bridge.
_Avoid_: Ping status, EA connection state

**Drawdown Guard**:
An automated risk control that tracks daily peak-to-trough equity loss and locks out trade execution once the predefined loss limit is hit.
_Avoid_: Loss limiter, daily cap

**AutoPilot**:
The autonomous execution mode where strategy signals are executed directly by the robot without requiring trader manual confirmation. When paused, the system remains in observing/telemetry mode.
_Avoid_: Manual execution fallback, prompt trade

**Strategy Signal Telemetry**:
Real-time indicator confluences and algorithm recommendations (e.g. EMA trend + RSI momentum) displayed as live telemetry data for monitoring.
_Avoid_: Tip, bot call, manual execution signal

**Initial Balance Benchmark (Saldo Awal Akun)**:
The baseline capital benchmark used solely for analytical evaluation of account growth, all-time P/L, and ROI trajectory. This is an analytical parameter, not a deposit transaction.
_Avoid_: Setoran dana, deposit transfer, opening cash

**All-Time P/L**:
The cumulative net profit or loss calculated as current real-time equity (or balance) relative to the initial balance benchmark.
_Avoid_: Total untung, laba keseluruhan, net gain

**Account Performance Curve**:
The chronological trajectory of account equity and balance growth reconstructed from initial balance benchmark and historical closed trades.
_Avoid_: Grafik saldo, profit line, chart trade

**TradeGear User**:
An authenticated account holder registered in the TradeGear web application with specific roles and private resources.
_Avoid_: Client, member, trader account

**MT5 Trading Account**:
The broker-hosted trading account running on a MetaTrader 5 terminal with capital, equity, and order execution capabilities.
_Avoid_: Web account, profile, login ID

**Bridge Token**:
A cryptographically secure, high-entropy API authentication token assigned to a TradeGear User to authenticate and bind incoming MT5 EA telemetry.
_Avoid_: MT5 password, broker pin, user secret

**Isolated Bridge Session**:
The strictly private runtime state (telemetry, positions, deal history, drawdown guard, and autopilot) maintained independently for each TradeGear User.
_Avoid_: Shared telemetry, global bridge, common feed

**TradeGearMonitor**:
The ultra-lightweight, 100% pure read-only MetaTrader 5 Expert Advisor that transmits real-time account telemetry (balances, equity, margin, positions, history, quotes) to TradeGear without trade execution capabilities.
_Avoid_: Bridge robot, execution EA, trader bot

**Pure Read-Only SaaS Telemetry**:
The architectural design guarantee that TradeGear operates strictly as an analytical observer and journal, possessing zero technical capability to open, modify, or liquidate trades on user accounts.
_Avoid_: Remote execution desk, web trading engine

**Risk Watchdog**:
The passive account risk monitor that evaluates equity drawdown and margin utilization against user-defined safety thresholds, dispatching high-priority alerts without touching active orders.
_Avoid_: Emergency kill switch, order liquidator, automated slasher
