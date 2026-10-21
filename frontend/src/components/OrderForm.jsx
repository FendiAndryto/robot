import React, { useState, useMemo, useEffect } from 'react';
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
  Zap,
  HelpCircle
} from 'lucide-react';
import { api } from '../services/api';

const QUICK_SYMBOLS = ['EURUSD', 'GBPUSD', 'USDJPY', 'XAUUSD', 'BTCUSD'];
const LOT_PRESETS = [0.01, 0.05, 0.10, 0.50, 1.00];
const RISK_PRESETS = [0.5, 1.0, 2.0, 3.0];
const SL_PIP_PRESETS = [25, 30, 45, 60, 100];
const SL_PERCENT_PRESETS = [0.2, 0.3, 0.5, 1.0, 1.5];

export default function OrderForm({
  equity = 10000,
  currency = 'USD',
  isKillSwitchActive = false,
  marketQuotes = [],
  initialSymbol = 'EURUSD',
  onOrderSubmitted
}) {
  const [symbol, setSymbol] = useState(initialSymbol || 'EURUSD');
  const [volume, setVolume] = useState('0.01');
  const [sl, setSl] = useState('');
  const [tp, setTp] = useState('');
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [showRiskCalc, setShowRiskCalc] = useState(true);

  // Stop Loss & Sizing Mode: 'pips' | 'price' | 'percent'
  const [slMode, setSlMode] = useState('pips');
  const [riskPercent, setRiskPercent] = useState(1.0);
  const [slPips, setSlPips] = useState(30.0);
  const [slPriceCustom, setSlPriceCustom] = useState('');
  const [slPercent, setSlPercent] = useState(0.5);
  const [rrRatio, setRrRatio] = useState(1.8);

  const [loadingAction, setLoadingAction] = useState(null); // 'BUY' | 'SELL' | null
  const [feedback, setFeedback] = useState(null); // { type: 'success' | 'error', message: string }

  // Sync initialSymbol when changed from parent
  useEffect(() => {
    if (initialSymbol) {
      const symClean = initialSymbol.toUpperCase().trim();
      setSymbol(symClean);
      if (symClean.includes('XAU') || symClean.includes('GOLD')) {
        setSlPips(45.0);
      } else if (symClean.includes('BTC')) {
        setSlPips(150.0);
      } else {
        setSlPips(30.0);
      }
    }
  }, [initialSymbol]);

  // Find live quote and market specifications for current symbol
  const activeQuote = useMemo(() => {
    const symClean = symbol.toUpperCase().trim().replace(/M$/, '');
    const found = marketQuotes.find(
      (q) => q.symbol.toUpperCase().replace(/M$/, '') === symClean
    );

    if (found && found.bid > 0) return found;

    // Fallback sensible defaults if quotes stream is loading
    if (symClean.includes('XAU') || symClean.includes('GOLD')) {
      return { symbol: symClean, bid: 4135.0, ask: 4135.25, spread: 25, digits: 3 };
    }
    if (symClean.includes('BTC')) {
      return { symbol: symClean, bid: 95000.0, ask: 95015.0, spread: 15, digits: 2 };
    }
    if (symClean.includes('JPY')) {
      return { symbol: symClean, bid: 158.20, ask: 158.21, spread: 10, digits: 3 };
    }
    return { symbol: symClean, bid: 1.12350, ask: 1.12360, spread: 10, digits: 5 };
  }, [symbol, marketQuotes]);

  // Dynamic Pip Size, Pip Value, and Sizing Calculation
  const calculation = useMemo(() => {
    const sym = symbol.toUpperCase().trim();
    const currentPrice = activeQuote.bid > 0 ? activeQuote.bid : 1.0;
    const digits = activeQuote.digits || 5;

    let pipSize = 0.0001;
    let pipVal = 10.0; // standard default for USD quote (EURUSD, GBPUSD, etc.)

    if (sym.includes('BTC')) {
      pipSize = 1.00;
      pipVal = 1.0;
    } else if (sym.includes('XAU') || sym.includes('GOLD')) {
      pipSize = 0.10; // 1 pip gold = $0.10
      pipVal = 10.0;  // 100 oz * $0.10 = $10.00 per lot
    } else if (sym.includes('JPY')) {
      pipSize = 0.01;
      pipVal = 1000.0 / currentPrice; // ~6.30 - 6.70 USD
    } else if (sym.startsWith('USD')) {
      pipSize = 0.0001;
      pipVal = 10.0 / currentPrice;
    }

    // Determine Effective Stop Loss Distance based on slMode ('pips', 'price', 'percent')
    const defaultSymPips = (sym.includes('XAU') || sym.includes('GOLD')) ? 45.0 : (sym.includes('BTC') ? 150.0 : 30.0);
    let effectivePips = defaultSymPips;
    let distPrice = defaultSymPips * pipSize;
    let distPercent = (distPrice / currentPrice) * 100;

    if (slMode === 'pips') {
      effectivePips = Math.max(1.0, Number(slPips) || defaultSymPips);
      distPrice = effectivePips * pipSize;
      distPercent = (distPrice / currentPrice) * 100;
    } else if (slMode === 'price') {
      const targetPrice = Number(slPriceCustom);
      if (targetPrice > 0 && Math.abs(currentPrice - targetPrice) > 0) {
        distPrice = Math.abs(currentPrice - targetPrice);
        effectivePips = Math.max(1.0, distPrice / pipSize);
        distPercent = (distPrice / currentPrice) * 100;
      } else {
        effectivePips = defaultSymPips;
        distPrice = defaultSymPips * pipSize;
        distPercent = (distPrice / currentPrice) * 100;
      }
    } else if (slMode === 'percent') {
      const pct = Math.max(0.02, Number(slPercent) || 0.5);
      distPrice = currentPrice * (pct / 100);
      effectivePips = Math.max(1.0, distPrice / pipSize);
      distPercent = pct;
    }

    const currentEquity = Number(equity) > 0 ? Number(equity) : 10000;
    const riskPct = Math.max(0.01, Math.min(10.0, Number(riskPercent) || 1.0));
    const riskAmount = currentEquity * (riskPct / 100.0);
    const rawLot = riskAmount / (effectivePips * pipVal);
    const clampedLot = Math.max(0.01, Math.min(100.0, Math.round(rawLot * 100) / 100));

    // Calculate Target SL & TP for both BUY and SELL directions
    const buySL = (currentPrice - distPrice).toFixed(digits);
    const buyTP = (currentPrice + (distPrice * rrRatio)).toFixed(digits);
    const sellSL = (currentPrice + distPrice).toFixed(digits);
    const sellTP = (currentPrice - (distPrice * rrRatio)).toFixed(digits);

    return {
      currentPrice,
      digits,
      pipSize,
      pipVal,
      effectivePips,
      distPrice,
      distPercent,
      riskAmount,
      clampedLot,
      rawLot,
      buySL,
      buyTP,
      sellSL,
      sellTP
    };
  }, [symbol, activeQuote, equity, riskPercent, slMode, slPips, slPriceCustom, slPercent, rrRatio]);

  // Apply calculated lot size and SL/TP into the form
  const applyCalculatedSizing = (direction = 'BUY') => {
    setVolume(calculation.clampedLot.toFixed(2));
    if (direction === 'BUY') {
      setSl(calculation.buySL);
      setTp(calculation.buyTP);
    } else {
      setSl(calculation.sellSL);
      setTp(calculation.sellTP);
    }

    setShowAdvanced(true);
    const currSymbol = currency === 'USD' ? '$' : `${currency} `;
    setFeedback({
      type: 'success',
      message: `Applied ${calculation.clampedLot.toFixed(2)} lot for ${direction} (Risk ${riskPercent}% = ${currSymbol}${calculation.riskAmount.toFixed(2)}, SL @ ${direction === 'BUY' ? calculation.buySL : calculation.sellSL}, TP @ ${direction === 'BUY' ? calculation.buyTP : calculation.sellTP}).`
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

    // If SL or TP fields are empty, use the calculated protection levels
    const finalSL = sl ? parseFloat(sl) : (action === 'BUY' ? parseFloat(calculation.buySL) : parseFloat(calculation.sellSL));
    const finalTP = tp ? parseFloat(tp) : (action === 'BUY' ? parseFloat(calculation.buyTP) : parseFloat(calculation.sellTP));

    try {
      const orderData = {
        action,
        symbol: symbol.trim().toUpperCase(),
        volume: volNum,
        sl: finalSL || null,
        tp: finalTP || null,
      };

      const result = await api.submitOrder(orderData);
      setFeedback({
        type: 'success',
        message: `${action} order queued successfully (${result.command_id}) with SL: ${finalSL || 'None'}, TP: ${finalTP || 'None'}. Dispatching to MT5!`
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
            <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
              Direct Web-to-MT5 · {symbol} ({activeQuote.bid > 0 ? activeQuote.bid.toFixed(activeQuote.digits) : '—'})
            </span>
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

      {/* Dynamic Position Sizing Risk Calculator with Pip / Price / % of Entry Toggle */}
      {showRiskCalc && (
        <div className="risk-calc-box animate-fade-in" id="risk-calculator-section" style={{ background: '#09151d', border: '1px solid var(--line)', borderRadius: '12px', padding: '14px', marginBottom: '16px' }}>
          <div className="risk-calc-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
              <Percent size={14} style={{ color: 'var(--accent-cyan)' }} />
              <span style={{ fontSize: '0.8rem', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.04em' }}>
                Risk & Position Sizer
              </span>
            </div>
            <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
              Equity: <strong style={{ color: 'var(--text-primary)' }}>${Number(equity || 10000).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</strong>
            </span>
          </div>

          {/* Sizing Mode Selector: Pips | Price | % of Entry */}
          <div style={{ marginBottom: '12px' }}>
            <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginBottom: '5px', fontWeight: 600 }}>
              Sizing Method (Pilih Mode Pengukuran SL):
            </div>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '4px', background: '#050c10', padding: '3px', borderRadius: '8px', border: '1px solid var(--line)' }}>
              <button
                type="button"
                className={`chip-btn ${slMode === 'pips' ? 'active' : ''}`}
                style={{ textAlign: 'center', padding: '5px', borderRadius: '6px', fontWeight: 700 }}
                onClick={() => setSlMode('pips')}
                id="btn-mode-pips"
              >
                Pips Distance
              </button>
              <button
                type="button"
                className={`chip-btn ${slMode === 'price' ? 'active' : ''}`}
                style={{ textAlign: 'center', padding: '5px', borderRadius: '6px', fontWeight: 700 }}
                onClick={() => {
                  setSlMode('price');
                  if (!slPriceCustom && calculation.currentPrice > 0) {
                    setSlPriceCustom((calculation.currentPrice - (15 * calculation.pipSize)).toFixed(calculation.digits));
                  }
                }}
                id="btn-mode-price"
              >
                Exact Price
              </button>
              <button
                type="button"
                className={`chip-btn ${slMode === 'percent' ? 'active' : ''}`}
                style={{ textAlign: 'center', padding: '5px', borderRadius: '6px', fontWeight: 700 }}
                onClick={() => setSlMode('percent')}
                id="btn-mode-percent"
              >
                % of Entry
              </button>
            </div>
          </div>

          <div className="risk-calc-grid" style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px', marginBottom: '12px' }}>
            {/* Risk of Equity % */}
            <div className="form-group">
              <label htmlFor="risk-percent-input" style={{ fontSize: '0.75rem' }}>Risk of Equity (%)</label>
              <div style={{ display: 'flex', gap: '3px', marginBottom: '4px' }}>
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

            {/* Dynamic Stop Loss Input Based on Selected Mode */}
            <div className="form-group">
              {slMode === 'pips' && (
                <>
                  <label htmlFor="sl-pips-input" style={{ fontSize: '0.75rem' }}>SL Distance (Pips)</label>
                  <div style={{ display: 'flex', gap: '3px', marginBottom: '4px' }}>
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
                  <span className="tiny" style={{ color: 'var(--text-muted)', marginTop: '2px', display: 'block' }}>
                    ≈ {calculation.distPercent.toFixed(2)}% of entry (${calculation.distPrice.toFixed(calculation.digits)})
                  </span>
                </>
              )}

              {slMode === 'price' && (
                <>
                  <label htmlFor="sl-price-input" style={{ fontSize: '0.75rem' }}>Exact SL Price</label>
                  <div style={{ display: 'flex', gap: '3px', marginBottom: '4px' }}>
                    <button
                      type="button"
                      className="chip-btn mini"
                      onClick={() => setSlPriceCustom((calculation.currentPrice - (15 * calculation.pipSize)).toFixed(calculation.digits))}
                    >
                      -15p
                    </button>
                    <button
                      type="button"
                      className="chip-btn mini"
                      onClick={() => setSlPriceCustom((calculation.currentPrice - (25 * calculation.pipSize)).toFixed(calculation.digits))}
                    >
                      -25p
                    </button>
                    <button
                      type="button"
                      className="chip-btn mini"
                      onClick={() => setSlPriceCustom((calculation.currentPrice + (15 * calculation.pipSize)).toFixed(calculation.digits))}
                    >
                      +15p
                    </button>
                  </div>
                  <input
                    id="sl-price-input"
                    type="number"
                    step="any"
                    className="form-input font-mono"
                    style={{ padding: '0.35rem 0.5rem', fontSize: '0.85rem' }}
                    placeholder="Contoh: 4130.50"
                    value={slPriceCustom}
                    onChange={(e) => setSlPriceCustom(e.target.value)}
                  />
                  <span className="tiny" style={{ color: 'var(--text-muted)', marginTop: '2px', display: 'block' }}>
                    Diff: {calculation.effectivePips.toFixed(1)} pips ({calculation.distPercent.toFixed(2)}%)
                  </span>
                </>
              )}

              {slMode === 'percent' && (
                <>
                  <label htmlFor="sl-percent-input" style={{ fontSize: '0.75rem' }}>SL (% of Entry Price)</label>
                  <div style={{ display: 'flex', gap: '3px', marginBottom: '4px' }}>
                    {SL_PERCENT_PRESETS.map((p) => (
                      <button
                        key={p}
                        type="button"
                        className={`chip-btn mini ${Number(slPercent) === p ? 'active' : ''}`}
                        onClick={() => setSlPercent(p)}
                      >
                        {p}%
                      </button>
                    ))}
                  </div>
                  <input
                    id="sl-percent-input"
                    type="number"
                    step="0.05"
                    min="0.02"
                    max="10.0"
                    className="form-input font-mono"
                    style={{ padding: '0.35rem 0.5rem', fontSize: '0.85rem' }}
                    value={slPercent}
                    onChange={(e) => setSlPercent(e.target.value)}
                  />
                  <span className="tiny" style={{ color: 'var(--text-muted)', marginTop: '2px', display: 'block' }}>
                    ≈ {calculation.effectivePips.toFixed(1)} pips (${calculation.distPrice.toFixed(calculation.digits)})
                  </span>
                </>
              )}
            </div>
          </div>

          {/* Sizing Output Display & Multi-Direction Quick Apply */}
          <div className="risk-calc-results" style={{ display: 'flex', flexDirection: 'column', gap: '8px', borderTop: '1px solid var(--line)', paddingTop: '10px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <div>
                <span className="risk-calc-metric-lbl" style={{ fontSize: '11px', color: 'var(--text-muted)' }}>Max Risk Amount: </span>
                <strong style={{ color: 'var(--accent-rose)', fontSize: '12px' }}>${calculation.riskAmount.toFixed(2)}</strong>
              </div>
              <div>
                <span className="risk-calc-metric-lbl" style={{ fontSize: '11px', color: 'var(--text-muted)' }}>Calculated Lot: </span>
                <strong style={{ color: 'var(--accent-cyan)', fontSize: '14px', fontFamily: 'monospace' }}>
                  {calculation.clampedLot.toFixed(2)}
                </strong>
              </div>
            </div>

            {/* Target SL/TP Preview */}
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '6px', fontSize: '11px', background: '#050c10', padding: '8px', borderRadius: '6px' }}>
              <div>
                <span style={{ color: '#45e0ad', fontWeight: 700 }}>BUY Target: </span>
                <span style={{ color: 'var(--text-muted)' }}>SL: {calculation.buySL} | TP: {calculation.buyTP}</span>
              </div>
              <div>
                <span style={{ color: '#ff6e7a', fontWeight: 700 }}>SELL Target: </span>
                <span style={{ color: 'var(--text-muted)' }}>SL: {calculation.sellSL} | TP: {calculation.sellTP}</span>
              </div>
            </div>

            {/* Quick Apply Buttons */}
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px', marginTop: '4px' }}>
              <button
                type="button"
                className="btn-apply-lot"
                style={{ justifyContent: 'center', background: '#103328', borderColor: '#29785e', color: '#45e0ad', padding: '6px 10px', fontSize: '11px', borderRadius: '6px', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '4px' }}
                onClick={() => applyCalculatedSizing('BUY')}
                id="apply-buy-sizing-btn"
                title="Apply calculated Lot and BUY SL/TP"
              >
                <Zap size={12} />
                <span>Apply BUY Sizing</span>
              </button>

              <button
                type="button"
                className="btn-apply-lot"
                style={{ justifyContent: 'center', background: '#3d1217', borderColor: '#732c38', color: '#ff6e7a', padding: '6px 10px', fontSize: '11px', borderRadius: '6px', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '4px' }}
                onClick={() => applyCalculatedSizing('SELL')}
                id="apply-sell-sizing-btn"
                title="Apply calculated Lot and SELL SL/TP"
              >
                <Zap size={12} />
                <span>Apply SELL Sizing</span>
              </button>
            </div>
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
          {showAdvanced ? '▼ Hide Protection (SL/TP)' : '▶ Protection Inputs (SL / TP)'}
        </button>

        {showAdvanced && (
          <div className="sl-tp-grid animate-fade-in" style={{ marginTop: '0.75rem', display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.75rem' }}>
            <div className="form-group">
              <label htmlFor="sl-input" style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                <Shield size={13} style={{ color: 'var(--accent-rose)' }} /> Stop Loss Price
              </label>
              <input
                id="sl-input"
                type="number"
                step="any"
                className="form-input font-mono"
                placeholder={calculation.buySL}
                value={sl}
                onChange={(e) => setSl(e.target.value)}
              />
            </div>
            <div className="form-group">
              <label htmlFor="tp-input" style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                <Target size={13} style={{ color: 'var(--accent-emerald)' }} /> Take Profit Price
              </label>
              <input
                id="tp-input"
                type="number"
                step="any"
                className="form-input font-mono"
                placeholder={calculation.buyTP}
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
            {isKillSwitchActive ? 'LOCKED' : `Market @ ${calculation.currentPrice.toFixed(calculation.digits)}`}
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
            {isKillSwitchActive ? 'LOCKED' : `Market @ ${calculation.currentPrice.toFixed(calculation.digits)}`}
          </span>
        </button>
      </div>
    </div>
  );
}
