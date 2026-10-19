import React, { useState } from 'react';
import { AlertOctagon, X, ShieldAlert, AlertTriangle, Loader2 } from 'lucide-react';

export default function KillSwitchModal({
  isOpen,
  onClose,
  onConfirm,
  openPositionsCount = 0,
  floatingPnl = 0,
  currency = 'USD'
}) {
  const [reason, setReason] = useState('Manual emergency kill switch triggered');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState(null);

  if (!isOpen) return null;

  const handleConfirm = async () => {
    setIsSubmitting(true);
    setError(null);
    try {
      await onConfirm(reason);
      onClose();
    } catch (err) {
      setError(err.message || 'Failed to trigger Kill Switch');
    } finally {
      setIsSubmitting(false);
    }
  };

  const formattedPnl = `${floatingPnl >= 0 ? '+' : ''}${new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: currency || 'USD'
  }).format(floatingPnl)}`;

  return (
    <div className="modal-backdrop animate-fade-in" id="kill-switch-modal-backdrop">
      <div className="kill-switch-modal glass-panel" id="kill-switch-modal">
        {/* Modal Header */}
        <div className="kill-switch-modal-header">
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <div className="kill-switch-icon-box">
              <AlertOctagon size={24} />
            </div>
            <div>
              <h3 className="kill-switch-title">EMERGENCY KILL SWITCH</h3>
              <span className="kill-switch-subtitle">BLANKET SHUTDOWN PROTOCOL</span>
            </div>
          </div>
          <button
            onClick={onClose}
            className="btn-modal-close"
            id="close-kill-switch-modal-btn"
            disabled={isSubmitting}
          >
            <X size={18} />
          </button>
        </div>

        {/* Modal Body */}
        <div className="kill-switch-modal-body">
          {error && (
            <div className="order-feedback-banner error" style={{ marginBottom: '1rem' }}>
              <AlertTriangle size={16} style={{ flexShrink: 0 }} />
              <span>{error}</span>
            </div>
          )}

          <div className="kill-switch-warning-box">
            <ShieldAlert size={22} style={{ flexShrink: 0, color: 'var(--accent-rose)' }} />
            <div style={{ fontSize: '0.85rem', lineHeight: 1.45 }}>
              <strong>CRITICAL WARNING:</strong> Triggering the Emergency Kill Switch will immediately transmit a
              blanket <span className="font-mono" style={{ color: 'var(--accent-rose)', fontWeight: 700 }}>CLOSE_ALL</span> command to MT5,
              liquidating all open positions, and lock the execution engine against any new incoming trades.
            </div>
          </div>

          {/* Quick Metrics at Risk */}
          <div className="kill-switch-metrics-grid">
            <div className="kill-switch-metric-card">
              <div className="metric-label">Positions to Liquidate</div>
              <div className="metric-val" style={{ color: openPositionsCount > 0 ? 'var(--accent-rose)' : 'var(--text-primary)' }}>
                {openPositionsCount} Trade{openPositionsCount === 1 ? '' : 's'}
              </div>
            </div>
            <div className="kill-switch-metric-card">
              <div className="metric-label">Current Floating PnL</div>
              <div className="metric-val" style={{ color: floatingPnl >= 0 ? 'var(--accent-emerald)' : 'var(--accent-rose)' }}>
                {formattedPnl}
              </div>
            </div>
          </div>

          {/* Reason Input */}
          <div className="form-group" style={{ marginTop: '1rem' }}>
            <label htmlFor="kill-switch-reason-input" style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
              Emergency Incident Reason
            </label>
            <input
              id="kill-switch-reason-input"
              type="text"
              className="form-input"
              value={reason}
              onChange={(e) => setReason(e.target.value)}
              placeholder="e.g. Extreme news spike, broker slippage, manual intervention"
              disabled={isSubmitting}
            />
          </div>
        </div>

        {/* Modal Footer */}
        <div className="kill-switch-modal-footer">
          <button
            type="button"
            className="btn-cancel"
            onClick={onClose}
            disabled={isSubmitting}
            id="cancel-kill-switch-btn"
          >
            Cancel
          </button>
          <button
            type="button"
            className="btn-confirm-kill-switch"
            onClick={handleConfirm}
            disabled={isSubmitting}
            id="confirm-kill-switch-btn"
          >
            {isSubmitting ? (
              <>
                <Loader2 size={16} className="animate-spin" />
                <span>ENGAGING SHUTDOWN...</span>
              </>
            ) : (
              <>
                <AlertOctagon size={18} />
                <span>CONFIRM EMERGENCY SHUTDOWN</span>
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  );
}
