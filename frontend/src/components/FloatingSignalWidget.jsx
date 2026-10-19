import React, { useState } from 'react';
import {
  Zap,
  ChevronDown,
  ChevronUp,
  CheckCircle2,
  XCircle,
  Sparkles
} from 'lucide-react';
import { api } from '../services/api';

export default function FloatingSignalWidget({
  signals = [],
  onRefreshSignals,
  isKillSwitchActive = false,
  isAutoPilotActive = false,
  onToggleAutoPilot,
  onOrderExecuted
}) {
  const [isOpen, setIsOpen] = useState(false);
  const [approvingId, setApprovingId] = useState(null);
  const [isSimulating, setIsSimulating] = useState(false);
  const [feedback, setFeedback] = useState(null);

  const signalCount = signals.length;

  const handleApprove = async (signalId) => {
    setApprovingId(signalId);
    setFeedback(null);
    try {
      const res = await api.approveSignal(signalId);
      setFeedback({ type: 'success', text: res.message || 'Signal approved & executed to MT5!' });
      if (onOrderExecuted) onOrderExecuted();
      if (onRefreshSignals) onRefreshSignals();
    } catch (err) {
      setFeedback({ type: 'error', text: err.message || 'Failed to approve signal' });
    } finally {
      setApprovingId(null);
    }
  };

  const handleDismiss = async (signalId) => {
    try {
      await api.dismissSignal(signalId);
      if (onRefreshSignals) onRefreshSignals();
    } catch (err) {
      console.error('Failed to dismiss signal:', err);
    }
  };

  const handleSimulate = async () => {
    setIsSimulating(true);
    setFeedback(null);
    try {
      await api.generateTestSignal({ symbol: 'XAUUSD', action: 'BUY' });
      if (onRefreshSignals) onRefreshSignals();
      setIsOpen(true);
      setFeedback({ type: 'success', text: 'Simulated BUY signal for XAUUSD generated!' });
    } catch (err) {
      setFeedback({ type: 'error', text: err.message || 'Failed to generate test signal' });
    } finally {
      setIsSimulating(false);
    }
  };

  return (
    <div
      className="floating-signals-container"
      id="floating-strategy-signals"
      style={{
        position: 'fixed',
        right: '16px',
        bottom: '82px', // Positioned safely above the mobile bottom navigation bar
        zIndex: 45,
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'flex-end',
        gap: '8px'
      }}
    >
      {/* Expanded Floating Signal Card */}
      {isOpen && (
        <div
          className="card"
          style={{
            width: '320px',
            maxWidth: 'calc(100vw - 32px)',
            maxHeight: '440px',
            overflowY: 'auto',
            background: 'rgba(17, 30, 38, 0.96)',
            backdropFilter: 'blur(20px)',
            WebkitBackdropFilter: 'blur(20px)',
            borderColor: 'rgba(69, 224, 173, 0.4)',
            boxShadow: '0 16px 40px rgba(0, 0, 0, 0.6), 0 0 20px rgba(69, 224, 173, 0.15)',
            borderRadius: '16px',
            padding: '14px',
            animation: 'pageIn 0.2s ease-out'
          }}
        >
          {/* Card Header */}
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '10px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
              <Zap size={15} style={{ color: 'var(--g)' }} />
              <h3 style={{ fontSize: '13px', margin: 0 }}>Strategy Signals</h3>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
              {onToggleAutoPilot ? (
                <button
                  type="button"
                  onClick={() => onToggleAutoPilot(!isAutoPilotActive)}
                  className={`tag ${isAutoPilotActive ? '' : 'blue'}`}
                  style={{
                    cursor: 'pointer',
                    border: 0,
                    fontSize: '9px',
                    padding: '3px 8px'
                  }}
                  title="Click to toggle AutoPilot / Semi-Auto mode"
                >
                  {isAutoPilotActive ? '⚡ AUTOPILOT' : 'SEMI-AUTO'}
                </button>
              ) : (
                <span className={`tag ${isAutoPilotActive ? '' : 'blue'}`} style={{ fontSize: '9px' }}>
                  {isAutoPilotActive ? 'AUTOPILOT' : 'SEMI-AUTO'}
                </span>
              )}
              <button
                type="button"
                onClick={() => setIsOpen(false)}
                style={{ background: 'transparent', border: 0, color: 'var(--muted)', cursor: 'pointer', padding: '2px' }}
                title="Minimize signals"
              >
                <ChevronDown size={16} />
              </button>
            </div>
          </div>

          {feedback && (
            <div
              style={{
                padding: '6px 10px',
                borderRadius: '8px',
                fontSize: '10.5px',
                marginBottom: '10px',
                background: feedback.type === 'success' ? '#14382c' : '#451f25',
                color: feedback.type === 'success' ? '#7ce8be' : '#ff9da7',
                border: `1px solid ${feedback.type === 'success' ? '#29785e' : '#732c38'}`
              }}
            >
              {feedback.text}
            </div>
          )}

          {/* Signal List */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
            {signals.length > 0 ? (
              signals.map((sig, idx) => {
                const isBuy = sig.action === 'BUY';
                return (
                  <div
                    key={sig.id || `signal-${idx}`}
                    style={{
                      background: '#0e181f',
                      border: '1px solid var(--line)',
                      borderRadius: '12px',
                      padding: '10px'
                    }}
                  >
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '6px' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                        <span style={{ fontWeight: 800, fontSize: '13px' }}>{sig.symbol}</span>
                        <span className={`tag ${isBuy ? '' : 'red'}`} style={{ fontSize: '9px' }}>
                          {sig.action} {sig.volume || '0.01'} lot
                        </span>
                      </div>
                      <span className="tiny" style={{ color: 'var(--muted)' }}>
                        {sig.timeframe || 'M15'}
                      </span>
                    </div>

                    <div style={{ fontSize: '10.5px', color: 'var(--muted)', marginBottom: '8px' }}>
                      {sig.reason || 'EMA 20/50 Cross + RSI Confluence'}
                    </div>

                    <div style={{ display: 'flex', gap: '6px' }}>
                      <button
                        type="button"
                        className="btn"
                        style={{ flex: 1, padding: '6px 8px', fontSize: '10.5px' }}
                        onClick={() => handleApprove(sig.id)}
                        disabled={approvingId === sig.id || isKillSwitchActive}
                      >
                        <CheckCircle2 size={12} />
                        <span>{approvingId === sig.id ? 'Executing...' : 'Approve'}</span>
                      </button>
                      <button
                        type="button"
                        className="btn alt"
                        style={{ padding: '6px 8px', fontSize: '10.5px' }}
                        onClick={() => handleDismiss(sig.id)}
                      >
                        <XCircle size={12} />
                        <span>Dismiss</span>
                      </button>
                    </div>
                  </div>
                );
              })
            ) : (
              <div style={{ padding: '16px 8px', textAlign: 'center', color: 'var(--muted)', fontSize: '11px' }}>
                <div>Tidak ada sinyal konfluensi baru saat ini.</div>
                <button
                  type="button"
                  className="btn alt"
                  style={{ marginTop: '8px', fontSize: '10px', padding: '5px 10px' }}
                  onClick={handleSimulate}
                  disabled={isSimulating}
                >
                  <Sparkles size={11} />
                  <span>{isSimulating ? 'Simulating...' : 'Simulate Confluence Signal'}</span>
                </button>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Floating Pill Trigger */}
      <button
        type="button"
        onClick={() => setIsOpen(!isOpen)}
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: '8px',
          padding: '8px 14px',
          borderRadius: '99px',
          background: signalCount > 0 ? '#143a2e' : '#14252e',
          color: signalCount > 0 ? 'var(--g)' : 'var(--text)',
          border: `1px solid ${signalCount > 0 ? 'rgba(69, 224, 173, 0.6)' : 'var(--line)'}`,
          boxShadow: '0 8px 24px rgba(0, 0, 0, 0.45)',
          cursor: 'pointer',
          fontWeight: 800,
          fontSize: '11.5px',
          transition: 'all 0.2s ease'
        }}
        id="floating-signals-trigger-btn"
        title="Strategy Recommendations & Semi-Auto Signals"
      >
        <span
          className={`pulse-dot ${signalCount > 0 ? 'online' : ''}`}
          style={{
            background: signalCount > 0 ? 'var(--g)' : 'var(--muted)',
            boxShadow: signalCount > 0 ? '0 0 10px var(--g)' : 'none'
          }}
        />
        <Zap size={14} />
        <span>Signals ({signalCount})</span>
        {isOpen ? <ChevronDown size={14} /> : <ChevronUp size={14} />}
      </button>
    </div>
  );
}
