import React from 'react';
import { ShieldAlert, ShieldCheck, Zap, AlertTriangle } from 'lucide-react';

const formatCurrency = (val, currency = 'USD') => {
  if (val === null || val === undefined) return '$0.00';
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: currency || 'USD',
    minimumFractionDigits: 2,
    maximumFractionDigits: 2
  }).format(val);
};

export default function DrawdownGuardCard({
  autopilotStatus,
  currency = 'USD'
}) {
  if (!autopilotStatus) return null;

  const {
    is_autopilot_active = false,
    is_drawdown_lockout_active = false,
    starting_equity = 0,
    closed_daily_pnl = 0,
    floating_pnl = 0,
    daily_drawdown_amount = 0,
    daily_drawdown_percent = 0,
    max_daily_drawdown_percent = 3.0,
    auto_executed_signals_count = 0
  } = autopilotStatus;

  // Calculate percentage of drawdown limit used (0% to 100+%)
  const limitUsedPercent = max_daily_drawdown_percent > 0
    ? Math.min(100, (daily_drawdown_percent / max_daily_drawdown_percent) * 100)
    : 0;

  // Remaining safety buffer
  const remainingBufferPercent = Math.max(0, max_daily_drawdown_percent - daily_drawdown_percent);

  // Dynamic status color
  let barColor = 'var(--accent-emerald)';
  let cardVariant = 'normal';
  if (is_drawdown_lockout_active) {
    barColor = 'var(--accent-rose)';
    cardVariant = 'lockout';
  } else if (limitUsedPercent > 75) {
    barColor = 'var(--accent-rose)';
    cardVariant = 'danger';
  } else if (limitUsedPercent > 40) {
    barColor = 'var(--accent-amber)';
    cardVariant = 'warning';
  }

  return (
    <div
      className={`drawdown-guard-card glass-panel ${cardVariant}`}
      id="drawdown-guard-card"
    >
      <div className="drawdown-card-header">
        <div className="drawdown-card-title-group">
          <div className="drawdown-icon-box">
            {is_drawdown_lockout_active ? (
              <ShieldAlert size={20} className="text-rose animate-pulse" />
            ) : (
              <ShieldCheck size={20} className="text-emerald" />
            )}
          </div>
          <div>
            <h4 className="drawdown-title">Daily Drawdown Guard</h4>
            <span className="drawdown-subtitle">
              Max Risk Ceiling: {max_daily_drawdown_percent.toFixed(2)}% of Baseline Equity
            </span>
          </div>
        </div>

        <div className="drawdown-status-badges">
          {is_drawdown_lockout_active ? (
            <span className="badge-drawdown-locked" id="badge-drawdown-locked">
              <AlertTriangle size={13} />
              LOCKOUT ACTIVE
            </span>
          ) : (
            <span className="badge-drawdown-armed" id="badge-drawdown-armed">
              <span className="drawdown-pulse-dot" />
              GUARD ARMED
            </span>
          )}
          {is_autopilot_active && (
            <span className="badge-autopilot-active" id="badge-autopilot-active">
              <Zap size={13} />
              AUTOPILOT ON ({auto_executed_signals_count})
            </span>
          )}
        </div>
      </div>

      {/* Drawdown Progress Meter */}
      <div className="drawdown-meter-container">
        <div className="drawdown-meter-labels">
          <span className="meter-label-left">
            Current Drawdown: <strong>{daily_drawdown_percent.toFixed(2)}%</strong>
            {daily_drawdown_amount > 0 && (
              <span className="meter-sub-amt"> ({formatCurrency(daily_drawdown_amount, currency)})</span>
            )}
          </span>
          <span className="meter-label-right">
            Remaining Buffer: <strong style={{ color: remainingBufferPercent <= 0.5 ? 'var(--accent-rose)' : 'var(--text-primary)' }}>{remainingBufferPercent.toFixed(2)}%</strong> / {max_daily_drawdown_percent.toFixed(2)}% Max
          </span>
        </div>

        <div className="drawdown-progress-track">
          <div
            className="drawdown-progress-fill"
            style={{
              width: `${Math.max(2, limitUsedPercent)}%`,
              backgroundColor: barColor
            }}
          />
        </div>
      </div>

      {/* Grid of Key Telemetry Sub-Metrics */}
      <div className="drawdown-metrics-subgrid">
        <div className="drawdown-submetric">
          <div className="submetric-label">Baseline Day Equity</div>
          <div className="submetric-val" id="drawdown-baseline-equity">
            {formatCurrency(starting_equity, currency)}
          </div>
        </div>

        <div className="drawdown-submetric">
          <div className="submetric-label">Today's Closed PnL</div>
          <div
            className={`submetric-val ${closed_daily_pnl >= 0 ? 'text-emerald' : 'text-rose'}`}
            id="drawdown-closed-pnl"
          >
            {closed_daily_pnl >= 0 ? '+' : ''}{formatCurrency(closed_daily_pnl, currency)}
          </div>
        </div>

        <div className="drawdown-submetric">
          <div className="submetric-label">Today's Floating PnL</div>
          <div
            className={`submetric-val ${floating_pnl >= 0 ? 'text-emerald' : 'text-rose'}`}
            id="drawdown-floating-pnl"
          >
            {floating_pnl >= 0 ? '+' : ''}{formatCurrency(floating_pnl, currency)}
          </div>
        </div>

        <div className="drawdown-submetric">
          <div className="submetric-label">Auto-Routed Orders</div>
          <div className="submetric-val text-cyan" id="drawdown-auto-executed-count">
            {auto_executed_signals_count} Executed
          </div>
        </div>
      </div>
    </div>
  );
}
