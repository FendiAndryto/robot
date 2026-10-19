# 07: Autonomous Auto-Pilot Mode with Daily Drawdown Guard

**What to build:** A toggleable "Auto-Pilot" mode that executes valid strategy signals automatically without human confirmation, protected by a strict daily drawdown guard. If cumulative closed and floating daily losses reach a set safety threshold (e.g. 3%), the bot shuts off and rejects all subsequent trade signals for the remainder of the day.

**Blocked by:** 06 (Strategy Engine & Semi-Auto Signal Approval)

**Status:** done

- [x] Master "Auto-Pilot" switch on the dashboard header with clear visual state indicators
- [x] In Auto-Pilot mode, high-confidence strategy signals immediately route to MT5 execution
- [x] Drawdown tracker aggregates daily closed PnL and floating PnL against starting day equity
- [x] If drawdown breaches the maximum daily risk threshold, system locks out and notifies user
