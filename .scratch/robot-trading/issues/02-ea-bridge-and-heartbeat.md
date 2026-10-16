# 02: EA Bridge & Local Ping-Pong Communication

**What to build:** An EA (Expert Advisor) compiled in MT5 that connects to a local FastAPI backend service. The EA periodically streams account state (balance, equity, margin, free margin) and connectivity status, while the backend responds with health acknowledgments, proving two-way communication between the web backend and the MT5 trading terminal.

**Blocked by:** 01 (MT5 Docker Sandbox & Headless Web-GUI)

**Status:** ready-for-agent

- [ ] Lightweight MQL5 Bridge EA compiled and loaded on an active MT5 chart
- [ ] Backend endpoint `/api/v1/bridge/heartbeat` successfully receives periodic payloads from the EA
- [ ] Backend stores latest connection timestamp and metrics in memory/cache
- [ ] Terminal logs confirm zero network errors and successful WebRequest responses from the backend
