# 08: Telegram Alerts & Cloudflare Tunnel Remote Access

**What to build:** Real-time push notifications sent to the user's Telegram chat for all system events (signals detected, orders filled, SL/TP hits, Kill Switch activations) and secure remote access to the web dashboard from mobile devices outside the local network via Cloudflare Tunnel.

**Blocked by:** 07 (Autonomous Auto-Pilot Mode with Daily Drawdown Guard)

**Status:** ready-for-agent

- [ ] Telegram bot sends formatted trade alert messages with pair, lot, PnL, and action taken
- [ ] Ansible automation registers the web dashboard service with the homeserver's Cloudflare Tunnel / Nginx stack
- [ ] Web dashboard is accessible via a custom domain over HTTPS without opening inbound router ports
- [ ] Mobile responsive layout verified on smartphone viewport
