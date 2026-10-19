import React, { useState } from 'react';
import { Cpu, Zap, Radio, RefreshCw, AlertCircle, Sparkles } from 'lucide-react';
import SignalCard from './SignalCard';
import { api } from '../services/api';

export default function SignalsPanel({
  signals = [],
  onRefreshSignals,
  isKillSwitchActive = false,
  isAutoPilotActive = false,
  onOrderExecuted
}) {
  const [feedback, setFeedback] = useState(null);
  const [isSimulating, setIsSimulating] = useState(false);

  const handleApprove = async (signalId) => {
    setFeedback(null);
    try {
      const res = await api.approveSignal(signalId);
      setFeedback({
        type: 'success',
        message: res.message || 'Signal approved and executed to MT5!'
      });
      if (onOrderExecuted) onOrderExecuted();
      if (onRefreshSignals) onRefreshSignals();
    } catch (err) {
      setFeedback({
        type: 'error',
        message: err.message || 'Failed to approve signal'
      });
    }
  };

  const handleDismiss = async (signalId) => {
    setFeedback(null);
    try {
      await api.dismissSignal(signalId);
      if (onRefreshSignals) onRefreshSignals();
    } catch (err) {
      setFeedback({
        type: 'error',
        message: err.message || 'Failed to dismiss signal'
      });
    }
  };

  const handleSimulateSignal = async (symbol = 'EURUSD', action = 'BUY') => {
    setIsSimulating(true);
    setFeedback(null);
    try {
      const sig = await api.generateTestSignal({ symbol, action });
      setFeedback({
        type: 'success',
        message: `Simulated ${sig.action} confluence signal on ${sig.symbol} successfully!`
      });
      if (onRefreshSignals) onRefreshSignals();
    } catch (err) {
      setFeedback({
        type: 'error',
        message: err.message || 'Failed to generate simulated signal'
      });
    } finally {
      setIsSimulating(false);
    }
  };

  return (
    <section className="signals-panel glass-panel" id="strategy-signals-section">
      {/* Header */}
      <div className="signals-panel-header">
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <div className="metric-icon-box" style={{ color: 'var(--accent-purple)' }}>
            <Cpu size={18} />
          </div>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <h3 style={{ fontSize: '1.05rem', fontWeight: 700 }}>Strategy Recommendations</h3>
              {isAutoPilotActive ? (
                <span className="live-pill autopilot" id="signals-mode-pill" style={{ background: 'rgba(16, 185, 129, 0.15)', borderColor: 'rgba(16, 185, 129, 0.4)', color: '#34d399' }}>
                  <Zap size={11} style={{ display: 'inline', marginRight: '3px', verticalAlign: '-1px' }} />
                  AUTOPILOT ON
                </span>
              ) : (
                <span className="live-pill" id="signals-mode-pill">
                  <span className="pulse-dot online" style={{ width: '6px', height: '6px' }} />
                  SEMI-AUTO
                </span>
              )}
            </div>
            <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
              {isAutoPilotActive
                ? 'Confluence signals are automatically executed to MT5 terminal'
                : 'EMA Trend & RSI Momentum Confluence Monitor'}
            </span>
          </div>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <button
            type="button"
            className="btn-simulate-signal"
            onClick={() => handleSimulateSignal(signals.length % 2 === 0 ? 'EURUSD' : 'GBPUSD', signals.length % 2 === 0 ? 'BUY' : 'SELL')}
            disabled={isSimulating}
            id="simulate-signal-btn"
            title="Generate a simulated confluence signal to test semi-auto workflow"
          >
            <Sparkles size={13} />
            <span>Simulate Confluence</span>
          </button>

          <button
            type="button"
            className="btn-refresh-icon"
            onClick={onRefreshSignals}
            id="refresh-signals-btn"
            title="Refresh signal list"
          >
            <RefreshCw size={14} />
          </button>
        </div>
      </div>

      {feedback && (
        <div
          className={`order-feedback-banner ${feedback.type === 'success' ? 'success' : 'error'}`}
          style={{ marginBottom: '1rem' }}
        >
          <AlertCircle size={16} style={{ flexShrink: 0 }} />
          <span>{feedback.message}</span>
        </div>
      )}

      {/* Signals Content */}
      <div className="signals-content-area">
        {signals && signals.length > 0 ? (
          <div className="signals-grid" id="active-signals-grid">
            {signals.map((sig) => (
              <SignalCard
                key={sig.signal_id}
                signal={sig}
                onApprove={handleApprove}
                onDismiss={handleDismiss}
                isKillSwitchActive={isKillSwitchActive}
              />
            ))}
          </div>
        ) : (
          <div className="signals-empty-state" id="signals-empty-state">
            <div className="empty-state-icon-box">
              <Radio size={24} style={{ color: 'var(--accent-purple)' }} />
            </div>
            <div className="empty-state-title">No Active Confluence Signals</div>
            <div className="empty-state-subtitle">
              The technical strategy engine is continuously scanning live quotes for EMA(9/21) trend and RSI momentum alignment.
              When a high-probability confluence is identified, approval cards will appear here.
            </div>
          </div>
        )}
      </div>
    </section>
  );
}
