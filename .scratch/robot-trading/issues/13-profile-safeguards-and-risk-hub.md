# 13: Profile, Safeguards & Risk Management Hub

**What to build:** Consolidate account settings, engine safeguards, and connection diagnostics within the Profile tab. Displays connected MT5 broker accounts, Daily Drawdown Guard progress, baseline reset action, Master Kill Switch trigger/unlock modal, MT5 Web-GUI viewer modal trigger, and Telegram notification test button. Includes persistent global emergency alert banners that lock to the top of all pages when a safety lockout is engaged.

**Blocked by:** 09 (TradeGear Design Tokens, App Shell & Responsive Navigation)

**Status:** done

- [x] Profile tab renders user profile card, connected accounts section, and system settings
- [x] Daily Drawdown Guard shows daily loss limit progress bar, starting baseline equity, and reset control
- [x] Master Kill Switch trigger button and unlock flow protect against uncontrolled market volatility
- [x] MT5 Web-GUI modal button opens live NoVNC terminal screen
- [x] Telegram alert test button sends verification message to configured Telegram bot
- [x] Global emergency warning banner appears on all tabs whenever Kill Switch or Drawdown Lockout is active
