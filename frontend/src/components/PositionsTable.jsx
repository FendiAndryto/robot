import React, { useState } from 'react';
import { Layers, XCircle, AlertOctagon, CheckCircle2, AlertCircle } from 'lucide-react';
import { api } from '../services/api';

const formatCurrency = (val, currency = 'USD') => {
  if (val === null || val === undefined) return '$0.00';
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: currency || 'USD',
    minimumFractionDigits: 2,
    maximumFractionDigits: 2
  }).format(val);
};

export default function PositionsTable({ positions = [], currency = 'USD', onActionCompleted }) {
  const [closingTicket, setClosingTicket] = useState(null);
  const [closingAll, setClosingAll] = useState(false);
  const [actionFeedback, setActionFeedback] = useState(null);

  const handleClosePosition = async (ticket) => {
    setClosingTicket(ticket);
    setActionFeedback(null);
    try {
      const res = await api.closePosition(ticket);
      setActionFeedback({
        type: 'success',
        message: `Close order queued for Ticket #${ticket} (${res.command_id}).`
      });
      if (onActionCompleted) onActionCompleted();
    } catch (err) {
      setActionFeedback({
        type: 'error',
        message: err.message || `Failed to close position #${ticket}.`
      });
    } finally {
      setClosingTicket(null);
    }
  };

  const handleCloseAll = async () => {
    if (!window.confirm('Are you sure you want to close ALL active trading positions immediately?')) {
      return;
    }
    setClosingAll(true);
    setActionFeedback(null);
    try {
      const res = await api.closeAllPositions();
      setActionFeedback({
        type: 'success',
        message: `Close all positions queued (${res.command_id}). Dispatching to MT5.`
      });
      if (onActionCompleted) onActionCompleted();
    } catch (err) {
      setActionFeedback({
        type: 'error',
        message: err.message || 'Failed to close all positions.'
      });
    } finally {
      setClosingAll(false);
    }
  };

  const totalPnL = positions.reduce((acc, p) => acc + (p.pnl || 0), 0);

  return (
    <div className="positions-panel glass-panel" id="positions-table-panel">
      <div className="positions-header">
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <div className="metric-icon-box" style={{ color: 'var(--accent-cyan)' }}>
            <Layers size={18} />
          </div>
          <div>
            <h3 style={{ fontSize: '1.05rem', fontWeight: 700 }}>Active Open Positions</h3>
            <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
              {positions.length} active trade{positions.length === 1 ? '' : 's'} on MT5
            </span>
          </div>
        </div>

        {positions.length > 0 && (
          <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
            <div style={{ textAlign: 'right' }}>
              <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)', textTransform: 'uppercase' }}>Total Floating</span>
              <div
                className="font-mono"
                style={{
                  fontWeight: 700,
                  fontSize: '0.95rem',
                  color: totalPnL >= 0 ? 'var(--accent-emerald)' : 'var(--accent-rose)'
                }}
              >
                {totalPnL >= 0 ? '+' : ''}{formatCurrency(totalPnL, currency)}
              </div>
            </div>

            <button
              onClick={handleCloseAll}
              disabled={closingAll}
              className="btn-close-all"
              id="close-all-positions-btn"
              title="Close all positions immediately"
            >
              <AlertOctagon size={15} />
              <span>{closingAll ? 'Closing All...' : 'Close All'}</span>
            </button>
          </div>
        )}
      </div>

      {actionFeedback && (
        <div
          className={`order-feedback-banner ${actionFeedback.type === 'success' ? 'success' : 'error'}`}
          style={{ margin: '1rem 0' }}
        >
          {actionFeedback.type === 'success' ? (
            <CheckCircle2 size={16} style={{ flexShrink: 0 }} />
          ) : (
            <AlertCircle size={16} style={{ flexShrink: 0 }} />
          )}
          <span>{actionFeedback.message}</span>
        </div>
      )}

      {positions.length === 0 ? (
        <div className="empty-positions-state" id="empty-positions-placeholder">
          <Layers size={36} style={{ opacity: 0.25, marginBottom: '0.5rem' }} />
          <p style={{ fontWeight: 600, color: 'var(--text-secondary)' }}>No Active Open Positions</p>
          <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
            Use the manual execution panel on the left to open a new trade on MT5.
          </span>
        </div>
      ) : (
        <div className="table-responsive">
          <table className="positions-table" id="positions-data-table">
            <thead>
              <tr>
                <th>Ticket</th>
                <th>Symbol</th>
                <th>Type</th>
                <th>Lots</th>
                <th>Open Price</th>
                <th>Current</th>
                <th>SL / TP</th>
                <th>Profit / Loss</th>
                <th style={{ textAlign: 'right' }}>Action</th>
              </tr>
            </thead>
            <tbody>
              {positions.map((pos) => {
                const isProfit = (pos.pnl || 0) >= 0;
                return (
                  <tr key={pos.ticket} id={`position-row-${pos.ticket}`}>
                    <td className="font-mono" style={{ color: 'var(--text-muted)', fontSize: '0.8rem' }}>
                      #{pos.ticket}
                    </td>
                    <td style={{ fontWeight: 700, color: '#ffffff' }}>
                      {pos.symbol}
                    </td>
                    <td>
                      <span className={`trade-badge ${pos.type === 'BUY' ? 'buy' : 'sell'}`}>
                        {pos.type}
                      </span>
                    </td>
                    <td className="font-mono">{pos.volume?.toFixed(2)}</td>
                    <td className="font-mono">{pos.open_price?.toFixed(5)}</td>
                    <td className="font-mono">{pos.current_price ? pos.current_price.toFixed(5) : '-'}</td>
                    <td className="font-mono" style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                      {pos.sl ? pos.sl.toFixed(5) : '-'} / {pos.tp ? pos.tp.toFixed(5) : '-'}
                    </td>
                    <td
                      className="font-mono"
                      style={{
                        fontWeight: 700,
                        color: isProfit ? 'var(--accent-emerald)' : 'var(--accent-rose)'
                      }}
                    >
                      {isProfit ? '+' : ''}{formatCurrency(pos.pnl, currency)}
                    </td>
                    <td style={{ textAlign: 'right' }}>
                      <button
                        onClick={() => handleClosePosition(pos.ticket)}
                        disabled={closingTicket === pos.ticket}
                        className="btn-close-pos"
                        id={`close-btn-${pos.ticket}`}
                        title={`Close Position #${pos.ticket}`}
                      >
                        <XCircle size={14} />
                        <span>{closingTicket === pos.ticket ? 'Closing...' : 'Close'}</span>
                      </button>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
