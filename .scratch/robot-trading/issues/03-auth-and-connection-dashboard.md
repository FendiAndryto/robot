# 03: Authentication & Connection Dashboard Slice

**What to build:** A secure web dashboard where the user logs in with credentials and views real-time MT5 account metrics (Balance, Equity, Margin, Free Margin, Floating Profit/Loss) alongside a live connection indicator showing whether the broker connection is currently healthy.

**Blocked by:** 02 (EA Bridge & Local Ping-Pong Communication)

**Status:** done

- [x] User can log in with username/password and receive an authenticated session (JWT)
- [x] Protected dashboard route displays live connection status badge (Connected / Disconnected)
- [x] Metric cards show real-time Balance, Equity, Margin Level (%), and Floating PnL
- [x] Disconnecting MT5 updates the status indicator to "Disconnected" within seconds

