import React, { useState, useMemo } from 'react';
import {
  ArrowUpRight,
  ArrowDownRight,
  TrendingUp,
  AlertCircle,
  CheckCircle2,
  Shield,
  Target,
  Calculator,
  Percent,
  Lock,
  Zap
} from 'lucide-react';
import { api } from '../services/api';

const QUICK_SYMBOLS = ['EURUSD', 'GBPUSD', 'USDJPY', 'XAUUSD', 'BTCUSD'];
const LOT_PRESETS = [0.01, 0.05, 0.10, 0.50, 1.00];
const RISK_PRESETS = [0.5, 1.0, 2.0, 3.0];
const SL_PIP_PRESETS = [15, 25, 50, 100];

export default function OrderForm({
  equity = 10000,
  currency = 'USD',
  isKillSwitchActive = false,
  onOrderSubmitted
}) {
  const [symbol, setSymbol] = useState('EURUSD');
  const [volume, setVolume] = useState('0.01');
  const [sl, setSl] = useState('');
  const [tp, setTp] = useState('');
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [showRiskCalc, setShowRiskCalc] = useState(true);

  // Risk Calculator Inputs
  const [riskPercent, setRiskPercent] = useState(1.0);
  const [slPips, setSlPips] = useState(25.0);

  const [loadingAction, setLoadingAction] = useState(null); // 'BUY' | 'SELL' | null
  const [feedback, setFeedback] = useState(null); // { type: 'success' | 'error', message: string }

  // Dynamic Pip Value & Lot Calculation
  const calculation = useMemo(() => {
    const sym = symbol.toUpperCase().trim();
    let pipVal = 10.0; // standard default for USD quote (EURUSD, GBPUSD, etc.)

    if (sym.includes('BTC')) {
      pipVal = 1.0;
    } else if (sym.includes('XAU') || sym.includes('GOLD')) {
      pipVal = 10.0; // 100 oz * $0.10
    } else if (sym.includes('JPY')) {
      pipVal = 1000.0 / 150.0; // ~6.67 USD
    } else if (sym.startsWith('USD')) {
      pipVal = 10.0 / 1.35; // ~7.41 USD
    }

    const currentEquity = Number(equity) > 0 ? Number(equity) : 10000;
    const riskPct = Math.max(0.01, Math.min(10.0, Number(riskPercent) || 1.0));
    const pips = Math.max(1.0, Number(slPips) || 25.0);

    const riskAmount = currentEquity * (riskPct / 100.0);
    const rawLot = riskAmount / (pips * pipVal);
    const clampedLot = Math.max(0.01, Math.min(100.0, Math.round(rawLot * 100) / 100));

    return {
      riskAmount,
      clampedLot,
      rawLot,
      pipVal
    };
  }, [symbol, equity, riskPercent, slPips]);

  // Apply calculated lot size into the volume field
  const applyCalculatedLot = () => {
    setVolume(calculation.clampedLot.toFixed(2));
    const currSymbol = currency === 'USD' ? '$' : `${currency} `;
    setFeedback({
      type: 'success',
      message: `Applied ${calculation.clampedLot.toFixed(2)} lots based on ${riskPercent}% risk (${currSymbol}${calculation.riskAmount.toFixed(2)}) & ${slPips} pips SL.`
    });
  };

  const handleLotChange = (delta) => {
    const current = parseFloat(volume) || 0.01;
    const next = Math.max(0.01, Math.round((current + delta) * 100) / 100);
    setVolume(next.toFixed(2));
  };

  const executeOrder = async (action) => {
    if (isKillSwitchActive) {
      setFeedback({
        type: 'error',
        message: 'Trading engine is locked by emergency Kill Switch. Disarm Kill Switch before submitting orders.'
      });
      return;
    }

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

        {/* Risk Calculator Toggle Button */}
        <button
          type="button"
          className={`btn-risk-toggle ${showRiskCalc ? 'active' : ''}`}
          onClick={() => setShowRiskCalc(!showRiskCalc)}
          id="toggle-risk-calculator-btn"
          title="Toggle dynamic risk % lot calculator"
        >
          <Calculator size={14} />
          <span>Risk Sizer</span>
        </button>
      </div>

      {/* Emergency Kill Switch Lock Alert */}
      {isKillSwitchActive && (
        <div className="order-lock-banner" id="order-locked-alert">
          <Lock size={16} style={{ flexShrink: 0, color: 'var(--accent-rose)' }} />
          <span>
            <strong>ENGINE DISARMED:</strong> Kill Switch is active. BUY and SELL order transmissions are blocked.
          </span>
        </div>
      )}

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

      {/* Dynamic Position Sizing Risk Calculator */}
      {showRiskCalc && (
        <div className="risk-calc-box animate-fade-in" id="risk-calculator-section">
          <div className="risk-calc-header">
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
              <Percent size={14} style={{ color: 'var(--accent-cyan)' }} />
              <span style={{ fontSize: '0.8rem', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.04em' }}>
                Automated Risk Calculator
              </span>
            </div>
            <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
              Equity: <strong style={{ color: 'var(--text-primary)' }}>${Number(equity || 10000).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</strong>
            </span>
          </div>

          <div className="risk-calc-grid">
            {/* Risk Percentage */}
            <div className="form-group">
              <label htmlFor="risk-percent-input" style={{ fontSize: '0.75rem' }}>Risk of Equity (%)</label>
              <div style={{ display: 'flex', gap: '4px', marginBottom: '4px' }}>
                {RISK_PRESETS.map((p) => (
                  <button
                    key={p}
                    type="button"
                    className={`chip-btn mini ${Number(riskPercent) === p ? 'active' : ''}`}
                    onClick={() => setRiskPercent(p)}
                  >
                    {p}%
                  </button>
                ))}
              </div>
              <input
                id="risk-percent-input"
                type="number"
                step="0.1"
                min="0.1"
                max="10.0"
                className="form-input font-mono"
                style={{ padding: '0.35rem 0.5rem', fontSize: '0.85rem' }}
                value={riskPercent}
                onChange={(e) => setRiskPercent(e.target.value)}
              />
            </div>

            {/* Stop Loss Distance */}
            <div className="form-group">
              <label htmlFor="sl-pips-input" style={{ fontSize: '0.75rem' }}>Stop Loss Distance (Pips)</label>
              <div style={{ display: 'flex', gap: '4px', marginBottom: '4px' }}>
                {SL_PIP_PRESETS.map((p) => (
                  <button
                    key={p}
                    type="button"
                    className={`chip-btn mini ${Number(slPips) === p ? 'active' : ''}`}
                    onClick={() => setSlPips(p)}
                  >
                    {p}p
                  </button>
                ))}
              </div>
              <input
                id="sl-pips-input"
                type="number"
                step="1"
                min="1"
                className="form-input font-mono"
                style={{ padding: '0.35rem 0.5rem', fontSize: '0.85rem' }}
                value={slPips}
                onChange={(e) => setSlPips(e.target.value)}
              />
            </div>
          </div>

          {/* Sizing Output Display & Quick Apply */}
          <div className="risk-calc-results">
            <div className="risk-calc-metric">
              <span className="risk-calc-metric-lbl">Max Risk ($)</span>
              <span className="risk-calc-metric-val" style={{ color: 'var(--accent-rose)' }}>
                ${calculation.riskAmount.toFixed(2)}
              </span>
            </div>

            <div className="risk-calc-metric">
              <span className="risk-calc-metric-lbl">Calculated Lot</span>
              <span className="risk-calc-metric-val font-mono" style={{ color: 'var(--accent-cyan)', fontSize: '1.1rem' }}>
                {calculation.clampedLot.toFixed(2)}
              </span>
            </div>

            <button
              type="button"
              className="btn-apply-lot"
              onClick={applyCalculatedLot}
              id="apply-calculated-lot-btn"
              title="Apply computed lot size to order form"
            >
              <Zap size={13} />
              <span>Apply Lot</span>
            </button>
          </div>
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
          className={`btn-order buy ${isKillSwitchActive ? 'disabled' : ''}`}
          id="buy-order-btn"
          disabled={isKillSwitchActive || loadingAction !== null}
          onClick={() => executeOrder('BUY')}
          title={isKillSwitchActive ? 'Trading locked by Kill Switch' : 'Execute Market BUY'}
        >
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '8px' }}>
            {isKillSwitchActive ? <Lock size={18} /> : <ArrowUpRight size={20} />}
            <span style={{ fontSize: '1.05rem', fontWeight: 800 }}>BUY</span>
          </div>
          <span style={{ fontSize: '0.7rem', opacity: 0.8 }}>
            {isKillSwitchActive ? 'LOCKED' : 'Market Long'}
          </span>
        </button>

        <button
          type="button"
          className={`btn-order sell ${isKillSwitchActive ? 'disabled' : ''}`}
          id="sell-order-btn"
          disabled={isKillSwitchActive || loadingAction !== null}
          onClick={() => executeOrder('SELL')}
          title={isKillSwitchActive ? 'Trading locked by Kill Switch' : 'Execute Market SELL'}
        >
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '8px' }}>
            {isKillSwitchActive ? <Lock size={18} /> : <ArrowDownRight size={20} />}
            <span style={{ fontSize: '1.05rem', fontWeight: 800 }}>SELL</span>
          </div>
          <span style={{ fontSize: '0.7rem', opacity: 0.8 }}>
            {isKillSwitchActive ? 'LOCKED' : 'Market Short'}
          </span>
        </button>
      </div>
    </div>
  );
}
