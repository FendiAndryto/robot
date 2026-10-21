# 17: Reconstructed Account Performance Curve with Day, Week & Month Filters

**What to build:** In backend and frontend, deterministically reconstruct the account growth curve from historical closed trades starting from the period's initial balance or deposit, culminating in current live equity. Provide Day (today since 00:00), Week (last 7 days), and Month (last 30 days) filter toggles on the SVG Account Performance chart with dynamic baseline summary labels.

**Blocked by:** 15 (Initial Deposit Telemetry Extraction & Hybrid Persistence)

**Status:** done

- [x] Backend generates / filters equity & balance curve points for Day, Week, and Month based on closed trades and initial deposit
- [x] Account Performance card UI provides Day, Week, and Month filter selector buttons
- [x] SVG curve renders chronological progress with dynamic green/red stroke, smooth gradient area fill, and baseline guide
- [x] Empty state gracefully handles cases with zero trades in the selected period by displaying the live baseline

