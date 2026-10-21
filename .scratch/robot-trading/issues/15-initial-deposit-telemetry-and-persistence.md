# 15: Initial Deposit Telemetry Extraction & Hybrid Persistence

**What to build:** Extract the initial funding balance deposit deal (`DEAL_TYPE_BALANCE`, `profit > 0`) automatically in MT5 EA and transmit it through bridge telemetry. In FastAPI backend, parse and expose `initial_deposit`, `all_time_pnl`, and `all_time_pnl_percent` on bridge status and telemetry, and provide `POST /api/v1/bridge/initial-deposit` endpoint for persistent manual override stored in `backend/app/data/account_settings.json`.

**Blocked by:** None (can start immediately)

**Status:** done

- [x] MT5 EA scans deal history for the first balance deposit deal and transmits `initial_deposit` in heartbeat payload
- [x] Backend bridge schema (`HeartbeatPayload`, `BridgeStatusResponse`) updated with `initial_deposit`, `all_time_pnl`, and `all_time_pnl_percent`
- [x] Backend persists manual initial deposit override in `account_settings.json` with reset support
- [x] Automated tests verify telemetry extraction, override persistence, and all-time P/L calculation

