# 01: MT5 Docker Sandbox & Headless Web-GUI

**What to build:** A running MetaTrader 5 instance deployed in a Docker container on the Ubuntu server, packaged with Wine and a web-accessible noVNC interface. From a web browser, the user can open the visual MT5 terminal interface, complete broker login with a demo/live account, and confirm market quotes are streaming.

**Blocked by:** None (can start immediately)

**Status:** done

- [x] Docker Compose service definition running Wine + MT5 + Xvfb + noVNC
- [x] Web browser can navigate to the noVNC port and display the MT5 GUI without crashes
- [x] User can authenticate into a broker trading account and observe live market ticks on charts
- [x] Container includes volume mounts for terminal data, configurations, and MQL5 Experts
