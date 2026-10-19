import React, { useState } from 'react';
import { ArrowUpRight, ArrowDownRight, TrendingUp, AlertCircle, CheckCircle2, Shield, Target } from 'lucide-react';
import { api } from '../services/api';

const QUICK_SYMBOLS = ['EURUSD', 'GBPUSD', 'USDJPY', 'XAUUSD', 'BTCUSD'];
const LOT_PRESETS = [0.01, 0.05, 0.10, 0.50, 1.00];

export default function OrderForm({ onOrderSubmitted }) {
  const [symbol, setSymbol] = useState('EURUSD');
  const [volume, setVolume] = useState('0.01');
  const [sl, setSl] = useState('');
  const [tp, setTp] = useState('');
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [loadingAction, setLoadingAction] = useState(null); // 'BUY' | 'SELL' | null
  const [feedback, setFeedback] = useState(null); // { type: 'success' | 'error', message: string }

  const handleLotChange = (delta) => {
    const current = parseFloat(volume) || 0.01;
    const next = Math.max(0.01, Math.round((current + delta) * 100) / 100);
    setVolume(next.toFixed(2));
  };

  const executeOrder = async (action) => {
    if (!symbol.trim()) {
      setFeedback({ type: 'error', message: 'Please specify a trading symbol.' });
      return;
    }
    const volNum = parseFloat(volume);
    if (isNaN(volNum) || volNum <= 0) {
      setFeedback({ type: 'error', message: 'Lot volume must be greater than 0.' });
      return;
    }

    setLoadingAction(action);
    setFeedback(null);

    try {
      const orderData = {
        action,
        symbol: symbol.trim().toUpperCase(),
        volume: volNum,
        sl: sl ? parseFloat(sl) : null,
        tp: tp ? parseFloat(tp) : null,
      };

      const result = await api.submitOrder(orderData);
      setFeedback({
        type: 'success',
        message: `${action} order queued successfully (${result.command_id}). Dispatching to MT5.`
      });

      if (onOrderSubmitted) {
        onOrderSubmitted(result);
      }
    } catch (err) {
      setFeedback({
        type: 'error',
        message: err.message || 'Failed to submit order to MT5.'
      });
    } finally {
      setLoadingAction(null);
    }
  };

  return (
    <div className="order-form-panel glass-panel" id="manual-order-widget">
      <div className="order-form-header">
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <div className="metric-icon-box" style={{ color: 'var(--accent-cyan)' }}>
            <TrendingUp size={18} />
          </div>
          <div>
            <h3 style={{ fontSize: '1.05rem', fontWeight: 700 }}>Manual Trade Execution</h3>
            <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Direct Web-to-MT5 Order Dispatch</span>
          </div>
        </div>
      </div>

      {feedback && (
        <div
          className={`order-feedback-banner ${feedback.type === 'success' ? 'success' : 'error'}`}
          id="order-feedback-banner"
        >
          {feedback.type === 'success' ? (
            <CheckCircle2 size={16} style={{ flexShrink: 0 }} />
          ) : (
            <AlertCircle size={16} style={{ flexShrink: 0 }} />
          )}
          <span>{feedback.message}</span>
        </div>
      )}

      {/* Symbol Selection */}
      <div className="form-group" style={{ marginBottom: '1rem' }}>
        <label htmlFor="symbol-input">Trading Symbol</label>
        <div style={{ display: 'flex', gap: '0.5rem', marginBottom: '0.5rem', flexWrap: 'wrap' }}>
          {QUICK_SYMBOLS.map((s) => (
            <button
              key={s}
              type="button"
              className={`chip-btn ${symbol.toUpperCase() === s ? 'active' : ''}`}
              onClick={() => setSymbol(s)}
            >
              {s}
            </button>
          ))}
        </div>
        <input
          id="symbol-input"
          type="text"
          className="form-input"
          placeholder="e.g. EURUSD, GBPUSD, XAUUSD"
          value={symbol}
          onChange={(e) => setSymbol(e.target.value.toUpperCase())}
          required
        />
      </div>

      {/* Lot Size Selection */}
      <div className="form-group" style={{ marginBottom: '1rem' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <label htmlFor="volume-input">Lot Size (Volume)</label>
          <div style={{ display: 'flex', gap: '4px' }}>
            {LOT_PRESETS.map((p) => (
              <button
                key={p}
                type="button"
                className={`chip-btn mini ${parseFloat(volume) === p ? 'active' : ''}`}
                onClick={() => setVolume(p.toFixed(2))}
              >
                {p}
              </button>
            ))}
          </div>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginTop: '0.4rem' }}>
          <button
            type="button"
            className="stepper-btn"
            onClick={() => handleLotChange(-0.01)}
            id="lot-decrement-btn"
            title="Decrease 0.01 lot"
          >
            -
          </button>
          <input
            id="volume-input"
            type="number"
            step="0.01"
            min="0.01"
            className="form-input font-mono"
            style={{ textAlign: 'center', fontSize: '1.1rem', fontWeight: 700 }}
            value={volume}
            onChange={(e) => setVolume(e.target.value)}
            required
          />
          <button
            type="button"
            className="stepper-btn"
            onClick={() => handleLotChange(0.01)}
            id="lot-increment-btn"
            title="Increase 0.01 lot"
          >
            +
          </button>
        </div>
      </div>

      {/* Advanced SL / TP Toggle */}
      <div style={{ marginBottom: '1.25rem' }}>
        <button
          type="button"
          onClick={() => setShowAdvanced(!showAdvanced)}
          style={{
            background: 'none',
            border: 'none',
            color: 'var(--accent-cyan)',
            fontSize: '0.8rem',
            cursor: 'pointer',
            fontWeight: 600,
            display: 'flex',
            alignItems: 'center',
            gap: '4px'
          }}
          id="toggle-sl-tp-btn"
        >
          {showAdvanced ? '▼ Hide Protection (SL/TP)' : '▶ Add Stop Loss & Take Profit (Optional)'}
        </button>

        {showAdvanced && (
          <div className="sl-tp-grid animate-fade-in" style={{ marginTop: '0.75rem', display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.75rem' }}>
            <div className="form-group">
              <label htmlFor="sl-input" style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                <Shield size={13} style={{ color: 'var(--accent-rose)' }} /> Stop Loss
              </label>
              <input
                id="sl-input"
                type="number"
                step="any"
                className="form-input font-mono"
                placeholder="Optional price"
                value={sl}
                onChange={(e) => setSl(e.target.value)}
              />
            </div>
            <div className="form-group">
              <label htmlFor="tp-input" style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                <Target size={13} style={{ color: 'var(--accent-emerald)' }} /> Take Profit
              </label>
              <input
                id="tp-input"
                type="number"
                step="any"
                className="form-input font-mono"
                placeholder="Optional price"
                value={tp}
                onChange={(e) => setTp(e.target.value)}
              />
            </div>
          </div>
        )}
      </div>

      {/* Buy & Sell Actions */}
      <div className="order-actions-grid" style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
        <button
          type="button"
          className="btn-order buy"
          id="buy-order-btn"
          disabled={loadingAction !== null}
          onClick={() => executeOrder('BUY')}
        >
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '8px' }}>
            <ArrowUpRight size={20} />
            <span style={{ fontSize: '1.05rem', fontWeight: 800 }}>BUY</span>
          </div>
          <span style={{ fontSize: '0.7rem', opacity: 0.8 }}>Market Long</span>
        </button>

        <button
          type="button"
          className="btn-order sell"
          id="sell-order-btn"
          disabled={loadingAction !== null}
          onClick={() => executeOrder('SELL')}
        >
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '8px' }}>
            <ArrowDownRight size={20} />
            <span style={{ fontSize: '1.05rem', fontWeight: 800 }}>SELL</span>
          </div>
          <span style={{ fontSize: '0.7rem', opacity: 0.8 }}>Market Short</span>
        </button>
      </div>
    </div>
  );
}
