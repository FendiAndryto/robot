# 02: EA Bridge & Local Ping-Pong Communication

**What to build:** An EA (Expert Advisor) compiled in MT5 that connects to a local FastAPI backend service. The EA periodically streams account state (balance, equity, margin, free margin) and connectivity status, while the backend responds with health acknowledgments, proving two-way communication between the web backend and the MT5 trading terminal.

**Blocked by:** 01 (MT5 Docker Sandbox & Headless Web-GUI)

**Status:** done

- [x] Lightweight MQL5 Bridge EA compiled and loaded on an active MT5 chart
- [x] Backend endpoint `/api/v1/bridge/heartbeat` successfully receives periodic payloads from the EA
- [x] Backend stores latest connection timestamp and metrics in memory/cache
- [x] Terminal logs confirm zero network errors and successful WebRequest responses from the backend
