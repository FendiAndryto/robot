import React, { useState } from 'react';
import {
  ArrowUpRight,
  ArrowDownRight,
  Check,
  X,
  TrendingUp,
  TrendingDown,
  ShieldAlert,
  Target,
  Zap,
  Loader2,
  Clock,
  Layers,
  Lock
} from 'lucide-react';

export default function SignalCard({
  signal,
  onApprove,
  onDismiss,
  isKillSwitchActive = false
}) {
  const [loadingAction, setLoadingAction] = useState(null); // 'APPROVE' | 'DISMISS' | null

  const isBuy = signal.action === 'BUY';

  const handleApprove = async () => {
    if (isKillSwitchActive) return;
    setLoadingAction('APPROVE');
    try {
      await onApprove(signal.signal_id);
    } finally {
      setLoadingAction(null);
    }
  };

  const handleDismiss = async () => {
    setLoadingAction('DISMISS');
    try {
      await onDismiss(signal.signal_id);
    } finally {
      setLoadingAction(null);
    }
  };

  const formattedTime = signal.created_at
    ? new Date(signal.created_at * 1000).toLocaleTimeString()
    : 'Just now';

  return (
    <div
      className={`signal-card glass-panel ${isBuy ? 'buy-signal' : 'sell-signal'} animate-fade-in`}
      id={`signal-card-${signal.signal_id}`}
    >
      {/* Top Header */}
      <div className="signal-card-header">
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <span className="signal-symbol-badge">{signal.symbol}</span>
          <span className={`signal-action-badge ${isBuy ? 'buy' : 'sell'}`}>
            {isBuy ? <ArrowUpRight size={14} /> : <ArrowDownRight size={14} />}
            <span>{signal.action}</span>
          </span>
          <span className="signal-rr-badge">{signal.risk_reward} RR</span>
        </div>

        <div className="signal-time-badge">
          <Clock size={12} />
          <span>{formattedTime}</span>
        </div>
      </div>

      {/* Main Signal Metrics Grid */}
      <div className="signal-metrics-grid">
        <div className="signal-metric-item">
          <span className="signal-metric-label">Entry Price</span>
          <span className="signal-metric-value font-mono">
            {signal.entry_price.toFixed(signal.symbol.includes('JPY') ? 3 : 5)}
          </span>
        </div>

        <div className="signal-metric-item">
          <span className="signal-metric-label">Recommended Lot</span>
          <span className="signal-metric-value font-mono" style={{ color: 'var(--accent-cyan)' }}>
            {signal.recommended_lot.toFixed(2)} Lots
          </span>
          <span style={{ fontSize: '0.68rem', color: 'var(--text-muted)' }}>
            ~${signal.risk_amount.toFixed(2)} risk
          </span>
        </div>

        <div className="signal-metric-item">
          <span className="signal-metric-label" style={{ display: 'flex', alignItems: 'center', gap: '3px' }}>
            <ShieldAlert size={11} style={{ color: 'var(--accent-rose)' }} /> Stop Loss
          </span>
          <span className="signal-metric-value font-mono" style={{ color: 'var(--accent-rose)' }}>
            {signal.sl.toFixed(signal.symbol.includes('JPY') ? 3 : 5)}
          </span>
          <span style={{ fontSize: '0.68rem', color: 'var(--text-muted)' }}>
            -{signal.sl_pips} pips
          </span>
        </div>

        <div className="signal-metric-item">
          <span className="signal-metric-label" style={{ display: 'flex', alignItems: 'center', gap: '3px' }}>
            <Target size={11} style={{ color: 'var(--accent-emerald)' }} /> Take Profit
          </span>
          <span className="signal-metric-value font-mono" style={{ color: 'var(--accent-emerald)' }}>
            {signal.tp.toFixed(signal.symbol.includes('JPY') ? 3 : 5)}
          </span>
          <span style={{ fontSize: '0.68rem', color: 'var(--text-muted)' }}>
            +{signal.tp_pips} pips
          </span>
        </div>
      </div>

      {/* Indicator Reason Box */}
      <div className="signal-reason-box">
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px', marginBottom: '4px' }}>
          <span className="signal-indicator-pill">
            {isBuy ? <TrendingUp size={12} /> : <TrendingDown size={12} />}
            EMA 9/21 {signal.indicators?.trend || 'TREND'}
          </span>
          <span className="signal-indicator-pill">
            RSI {signal.indicators?.rsi || '50'}
          </span>
        </div>
        <div className="signal-reason-text">{signal.reason}</div>
      </div>

      {/* Action Buttons */}
      <div className="signal-actions">
        <button
          type="button"
          className="btn-signal-dismiss"
          onClick={handleDismiss}
          disabled={loadingAction !== null}
          id={`dismiss-signal-${signal.signal_id}`}
          title="Ignore / Dismiss this setup"
        >
          {loadingAction === 'DISMISS' ? (
            <Loader2 size={14} className="animate-spin" />
          ) : (
            <X size={14} />
          )}
          <span>Dismiss</span>
        </button>

        <button
          type="button"
          className={`btn-signal-approve ${isKillSwitchActive ? 'disabled' : ''}`}
          onClick={handleApprove}
          disabled={isKillSwitchActive || loadingAction !== null}
          id={`approve-signal-${signal.signal_id}`}
          title={isKillSwitchActive ? 'Trading locked by Kill Switch' : 'Approve and dispatch order to MT5'}
        >
          {loadingAction === 'APPROVE' ? (
            <>
              <Loader2 size={15} className="animate-spin" />
              <span>Executing Order...</span>
            </>
          ) : isKillSwitchActive ? (
            <>
              <Lock size={15} />
              <span>Trading Locked</span>
            </>
          ) : (
            <>
              <Check size={16} />
              <span>Approve & Execute</span>
            </>
          )}
        </button>
      </div>
    </div>
  );
}
