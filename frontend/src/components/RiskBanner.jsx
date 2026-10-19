import React, { useState } from 'react';
import { AlertOctagon, Unlock, Loader2 } from 'lucide-react';

export default function RiskBanner({
  reason,
  triggeredAt,
  onUnlock,
  isUnlocking = false
}) {
  const [showConfirm, setShowConfirm] = useState(false);

  const formattedTime = triggeredAt
    ? new Date(triggeredAt * 1000).toLocaleTimeString()
    : 'Recently';

  return (
    <div className="risk-emergency-banner animate-fade-in" id="risk-emergency-banner">
      <div className="risk-banner-content">
        <div className="risk-banner-icon-pulse">
          <AlertOctagon size={24} />
        </div>
        <div>
          <div className="risk-banner-title">
            EMERGENCY KILL SWITCH ENGAGED — TRADING OPERATIONS LOCKED
          </div>
          <div className="risk-banner-subtitle">
            Reason: <span style={{ color: '#fff', fontWeight: 600 }}>{reason || 'Emergency shutdown triggered'}</span> • Triggered at: {formattedTime}
          </div>
        </div>
      </div>

      <div className="risk-banner-actions">
        {!showConfirm ? (
          <button
            type="button"
            className="btn-unlock-engine"
            onClick={() => setShowConfirm(true)}
            id="unlock-engine-init-btn"
          >
            <Unlock size={16} />
            <span>Disarm & Unlock Engine</span>
          </button>
        ) : (
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <button
              type="button"
              className="btn-cancel mini"
              onClick={() => setShowConfirm(false)}
              disabled={isUnlocking}
            >
              Cancel
            </button>
            <button
              type="button"
              className="btn-confirm-unlock"
              onClick={() => {
                setShowConfirm(false);
                onUnlock();
              }}
              disabled={isUnlocking}
              id="confirm-unlock-engine-btn"
            >
              {isUnlocking ? (
                <>
                  <Loader2 size={14} className="animate-spin" />
                  <span>Unlocking...</span>
                </>
              ) : (
                <>
                  <Unlock size={14} />
                  <span>Confirm Unlock</span>
                </>
              )}
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
