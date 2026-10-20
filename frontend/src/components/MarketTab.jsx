import React, { useState, useEffect } from 'react';
import { TrendingUp, BarChart2, Eye, Compass, RefreshCw, Zap } from 'lucide-react';
import { api } from '../services/api';

const getSymbolIcon = (sym) => {
  const s = sym.toUpperCase();
  if (s.includes('BTC')) return '₿';
  if (s.includes('XAU') || s.includes('GOLD')) return 'Au';
  if (s.includes('XAG') || s.includes('SILVER')) return 'Ag';
  if (s.includes('EUR')) return 'Eu';
  if (s.includes('GBP')) return 'Gu';
  if (s.includes('JPY')) return '¥';
  return s.slice(0, 2);
};

const getSymbolName = (sym) => {
  const s = sym.toUpperCase();
  if (s === 'XAUUSD') return 'Gold / US Dollar';
  if (s === 'EURUSD') return 'Euro / US Dollar';
  if (s === 'GBPUSD') return 'Pound / US Dollar';
  if (s === 'USDJPY') return 'US Dollar / Yen';
  if (s === 'BTCUSD') return 'Bitcoin / US Dollar';
  return sym;
};

export default function MarketTab({ bridgeStatus, onOpenOrder }) {
  const [quotes, setQuotes] = useState([]);
  const [selectedSymbol, setSelectedSymbol] = useState('XAUUSD');
  const [activeTf, setActiveTf] = useState('M15');
  const [loading, setLoading] = useState(false);

  const fetchQuotes = async () => {
    try {
      setLoading(true);
      const data = await api.getMarketQuotes();
      if (Array.isArray(data) && data.length > 0) {
        setQuotes(data);
      }
    } catch (err) {
      console.error('Failed to load market quotes:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    // If bridgeStatus already has quotes from telemetry, use them
    if (bridgeStatus?.market_quotes && bridgeStatus.market_quotes.length > 0) {
      setQuotes(bridgeStatus.market_quotes);
    } else {
      fetchQuotes();
    }
  }, [bridgeStatus]);

  const activeQuote = quotes.find((q) => q.symbol === selectedSymbol) || quotes[0] || {
    symbol: selectedSymbol,
    bid: 0,
    ask: 0,
    spread: 0,
    digits: 2,
    daily_change_pct: 0,
    high: 0,
    low: 0
  };

  const isPositive = activeQuote.daily_change_pct >= 0;

  return (
    <div className="market-tab-container animate-fade-in">
      <div className="heading">
        <div>
          <div className="eyebrow">MT5 LIVE BROKER STREAM</div>
          <h1>Market Overview</h1>
          <div className="sub">Feed harga dan spread real-time langsung dari broker MetaTrader 5.</div>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <button
            type="button"
            className="btn alt"
            onClick={fetchQuotes}
            title="Refresh Live Feed"
            id="market-refresh-btn"
            style={{ padding: '7px 12px' }}
          >
            <RefreshCw size={13} className={loading ? 'animate-spin' : ''} />
          </button>
          <span className="status-pill connected">
            <Eye size={12} />
            <span>REAL-TIME MT5 QUOTES</span>
          </span>
        </div>
      </div>

      <div className="grid two" style={{ marginBottom: '20px' }}>
        {/* Real Watchlist */}
        <div className="card">
          <div className="cardhead">
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <TrendingUp size={16} style={{ color: 'var(--g)' }} />
              <h3>Watchlist Broker Feed</h3>
            </div>
            <span className="tiny">{quotes.length} instruments</span>
          </div>

          {quotes.length > 0 ? (
            quotes.map((item) => {
              const isItemPos = item.daily_change_pct >= 0;
              const isSelected = item.symbol === activeQuote.symbol;
              const formattedPrice = item.bid > 0 ? item.bid.toFixed(item.digits) : '—';
              const formattedDelta = `${isItemPos ? '+' : ''}${item.daily_change_pct.toFixed(2)}%`;

              return (
                <div
                  key={item.symbol}
                  className="row"
                  onClick={() => setSelectedSymbol(item.symbol)}
                  style={{
                    cursor: 'pointer',
                    background: isSelected ? '#152b2b' : 'transparent',
                    borderRadius: '8px',
                    padding: '8px 10px',
                    transition: 'background 0.15s ease'
                  }}
                  id={`watchlist-item-${item.symbol}`}
                >
                  <div className="coin">{getSymbolIcon(item.symbol)}</div>
                  <div className="grow">
                    <div className="rowtitle" style={{ fontWeight: isSelected ? 800 : 600 }}>
                      {item.symbol}
                    </div>
                    <div className="rowsub">
                      {getSymbolName(item.symbol)} · Spread {item.spread} pts
                    </div>
                  </div>
                  <div className="end">
                    <div style={{ fontFamily: 'monospace', fontWeight: 700 }}>
                      {item.symbol.includes('XAU') || item.symbol.includes('BTC') ? `$${formattedPrice}` : formattedPrice}
                    </div>
                    <small className={isItemPos ? 'positive' : 'negative'}>
                      {formattedDelta}
                    </small>
                  </div>
                </div>
              );
            })
          ) : (
            <div style={{ padding: '24px 8px', textAlign: 'center', color: 'var(--muted)' }}>
              Menunggu feed quotes dari Bridge EA di MT5...
            </div>
          )}
        </div>

        {/* Real Market Context Card */}
        <div className="card">
          <div className="cardhead">
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <Compass size={16} style={{ color: 'var(--blue)' }} />
              <h3>Live Technical Context</h3>
            </div>
            <span className="tag blue">{activeQuote.symbol}</span>
          </div>

          <div className="eyebrow" style={{ color: 'var(--blue)' }}>
            {activeQuote.symbol} · REAL BROKER TELEMETRY
          </div>
          <h2 style={{ fontSize: '20px', margin: '8px 0', fontWeight: 800 }}>
            {activeQuote.bid > 0
              ? `${activeQuote.symbol.includes('XAU') || activeQuote.symbol.includes('BTC') ? '$' : ''}${activeQuote.bid.toFixed(activeQuote.digits)}`
              : 'Menunggu harga...'}
          </h2>
          <p className="sub" style={{ lineHeight: 1.5, marginBottom: '14px' }}>
            {isPositive
              ? `Harga menunjukkan tren menguat harian (+${activeQuote.daily_change_pct.toFixed(2)}%). Spread live tercatat ${activeQuote.spread} poin.`
              : `Harga berada dalam tekanan harian (${activeQuote.daily_change_pct.toFixed(2)}%). Spread live tercatat ${activeQuote.spread} poin.`}
          </p>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', borderTop: '1px solid var(--line)', paddingTop: '10px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '12px' }}>
              <span style={{ color: 'var(--muted)' }}>Live Bid / Ask</span>
              <b style={{ fontFamily: 'monospace' }}>
                {activeQuote.bid.toFixed(activeQuote.digits)} / {activeQuote.ask.toFixed(activeQuote.digits)}
              </b>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '12px' }}>
              <span style={{ color: 'var(--muted)' }}>Rentang Sesi (Low – High)</span>
              <b style={{ fontFamily: 'monospace' }}>
                {activeQuote.low > 0 ? activeQuote.low.toFixed(activeQuote.digits) : '—'} –{' '}
                {activeQuote.high > 0 ? activeQuote.high.toFixed(activeQuote.digits) : '—'}
              </b>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '12px' }}>
              <span style={{ color: 'var(--muted)' }}>Spread Broker</span>
              <b style={{ color: activeQuote.spread <= 25 ? 'var(--g)' : 'var(--amber)' }}>
                {activeQuote.spread} points
              </b>
            </div>
          </div>

          {onOpenOrder && (
            <button
              type="button"
              className="btn"
              style={{ marginTop: '16px', width: '100%', justifyContent: 'center' }}
              onClick={() => onOpenOrder(activeQuote.symbol)}
              id="market-trade-symbol-btn"
            >
              <Zap size={14} />
              <span>Eksekusi Order {activeQuote.symbol}</span>
            </button>
          )}
        </div>
      </div>

      {/* Market Structure Visualizer */}
      <div className="section" style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '10px' }}>
        <BarChart2 size={16} style={{ color: 'var(--g)' }} />
        <span>Market Structure & Dynamics</span>
        <span className="tiny">{activeQuote.symbol} Technical Range</span>
      </div>

      <div className="card">
        <div className="cardhead">
          <div>
            <h3>{activeQuote.symbol} · Price Action Range</h3>
            <div className="tiny">Visualisasi rentang sesi dan titik harga Bid saat ini</div>
          </div>
          <div style={{ display: 'flex', gap: '4px', background: '#0a1419', padding: '3px', borderRadius: '8px', border: '1px solid var(--line)' }}>
            {['M5', 'M15', 'H1', 'H4'].map((tf) => (
              <button
                key={tf}
                type="button"
                style={{
                  border: 0,
                  background: activeTf === tf ? '#205342' : 'transparent',
                  color: activeTf === tf ? '#b8ffe6' : 'var(--muted)',
                  fontSize: '10px',
                  fontWeight: 700,
                  padding: '5px 10px',
                  borderRadius: '6px',
                  cursor: 'pointer'
                }}
                onClick={() => setActiveTf(tf)}
              >
                {tf}
              </button>
            ))}
          </div>
        </div>

        {/* Dynamic Range Bar */}
        <div style={{ padding: '24px 10px 10px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '12px', marginBottom: '8px', color: 'var(--muted)', fontFamily: 'monospace' }}>
            <span>Low: {activeQuote.low > 0 ? activeQuote.low.toFixed(activeQuote.digits) : '—'}</span>
            <span style={{ color: 'var(--text)', fontWeight: 700 }}>Bid: {activeQuote.bid > 0 ? activeQuote.bid.toFixed(activeQuote.digits) : '—'}</span>
            <span>High: {activeQuote.high > 0 ? activeQuote.high.toFixed(activeQuote.digits) : '—'}</span>
          </div>

          {/* Progress bar representing price position within the daily high-low range */}
          <div style={{ height: '10px', background: '#10222a', borderRadius: '5px', overflow: 'hidden', position: 'relative' }}>
            {activeQuote.high > activeQuote.low ? (
              <div
                style={{
                  position: 'absolute',
                  left: 0,
                  top: 0,
                  bottom: 0,
                  width: `${Math.max(5, Math.min(95, ((activeQuote.bid - activeQuote.low) / (activeQuote.high - activeQuote.low)) * 100))}%`,
                  background: isPositive ? 'linear-gradient(90deg, #1f6b52, #45e0ad)' : 'linear-gradient(90deg, #6b242a, #ff6e7a)',
                  borderRadius: '5px',
                  transition: 'width 0.3s ease'
                }}
              />
            ) : (
              <div style={{ width: '50%', height: '100%', background: 'var(--line)' }} />
            )}
          </div>
          <div className="tiny" style={{ color: 'var(--muted)', textAlign: 'center', marginTop: '12px' }}>
            Data ditransmisikan secara langsung dari terminal MT5 laptop Anda tanpa simulasi buatan.
          </div>
        </div>
      </div>
    </div>
  );
}
