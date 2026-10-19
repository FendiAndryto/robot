# 05: Risk Calculator & Emergency Kill Switch

**What to build:** Automated position sizing based on risk percentage and an emergency "Kill Switch" button. Entering a risk percentage (e.g. 1%) and Stop Loss pip distance auto-calculates the exact lot size before ordering. Pressing the "Kill Switch" immediately transmits a blanket command to close all open trades on MT5 and disarms trading operations.

**Blocked by:** 04 (Web-Triggered Manual Trade Execution)

**Status:** done

- [x] UI calculator updates lot size dynamically based on account equity, currency pair, and SL distance
- [x] Prominent, protected "Kill Switch" button on the UI (with quick confirmation modal)
- [x] Triggering Kill Switch sends emergency signal that closes all open market positions in MT5
- [x] System status locks into a paused state preventing any new trades until explicitly unlocked
