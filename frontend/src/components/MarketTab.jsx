import React, { useState } from 'react';
import { TrendingUp, BarChart2, Eye, Compass } from 'lucide-react';

const WATCHLIST = [
  { symbol: 'XAUUSD', name: 'Gold / US Dollar', price: '$4,218.60', delta: '+0.42%', positive: true, icon: 'Au' },
  { symbol: 'EURUSD', name: 'Euro / US Dollar', price: '1.16420', delta: '+0.11%', positive: true, icon: 'Eu' },
  { symbol: 'GBPUSD', name: 'Pound / US Dollar', price: '1.33840', delta: '−0.08%', positive: false, icon: 'Gu' },
  { symbol: 'BTCUSD', name: 'Bitcoin / US Dollar', price: '$67,240', delta: '−0.18%', positive: false, icon: '₿' }
];

export default function MarketTab() {
  const [activeTf, setActiveTf] = useState('M15');

  return (
    <div className="market-tab-container animate-fade-in">
      <div className="heading">
        <div>
          <div className="eyebrow">MARKET CONTEXT & SENTIMENT</div>
          <h1>Market Overview</h1>
          <div className="sub">Pantau watchlist utama dan analisis skenario struktur teknikal.</div>
        </div>
        <span className="status-pill connected">
          <Eye size={12} />
          <span>REAL-TIME WATCHLIST</span>
        </span>
      </div>

      <div className="grid two" style={{ marginBottom: '20px' }}>
        {/* Watchlist */}
        <div className="card">
          <div className="cardhead">
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <TrendingUp size={16} style={{ color: 'var(--g)' }} />
              <h3>Watchlist</h3>
            </div>
            <span className="tiny">{WATCHLIST.length} instruments</span>
          </div>

          {WATCHLIST.map((item) => (
            <div key={item.symbol} className="row">
              <div className="coin">{item.icon}</div>
              <div className="grow">
                <div className="rowtitle">{item.symbol}</div>
                <div className="rowsub">{item.name}</div>
              </div>
              <div className="end">
                {item.price}
                <small className={item.positive ? 'positive' : 'negative'}>
                  {item.delta}
                </small>
              </div>
            </div>
          ))}
        </div>

        {/* AI Market Analyst Card */}
        <div className="card">
          <div className="cardhead">
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <Compass size={16} style={{ color: 'var(--blue)' }} />
              <h3>AI Market Analyst</h3>
            </div>
            <span className="tag blue">CONFLUENCE</span>
          </div>

          <div className="eyebrow" style={{ color: 'var(--blue)' }}>XAUUSD · M15 STRUCTURE</div>
          <h2 style={{ fontSize: '18px', margin: '8px 0', fontWeight: 800 }}>
            Wait for confirmation at 4,210 area
          </h2>
          <p className="sub" style={{ lineHeight: 1.5, marginBottom: '14px' }}>
            Harga sedang mendekati area key resistance. Tunggu konfirmasi penolakan (rejection wick)
            atau break struktur sebelum memicu entry BUY lanjutan.
          </p>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', borderTop: '1px solid var(--line)', paddingTop: '10px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '12px' }}>
              <span style={{ color: 'var(--muted)' }}>Bias Confluence</span>
              <b style={{ color: 'var(--amber)' }}>Neutral / Bullish Retest</b>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '12px' }}>
              <span style={{ color: 'var(--muted)' }}>Key Zone</span>
              <b>4,205 – 4,225</b>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '12px' }}>
              <span style={{ color: 'var(--muted)' }}>Invalidation</span>
              <b style={{ color: 'var(--red)' }}>Break below 4,195</b>
            </div>
          </div>
        </div>
      </div>

      {/* Market Structure Visualizer */}
      <div className="section" style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '10px' }}>
        <BarChart2 size={16} style={{ color: 'var(--g)' }} />
        <span>Market Structure & Timeframes</span>
        <span className="tiny">XAUUSD Technical Curve</span>
      </div>

      <div className="card">
        <div className="cardhead">
          <h3>XAUUSD · {activeTf} Confluence</h3>
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

        {/* SVG Multi-wave chart */}
        <svg
          style={{ width: '100%', height: '170px', display: 'block', margin: '12px 0' }}
          viewBox="0 0 600 170"
          preserveAspectRatio="none"
        >
          <g stroke="#20353e" strokeDasharray="4 6">
            <path d="M0 30H600M0 70H600M0 110H600M0 145H600" />
          </g>
          <path
            d="M0 135 L40 120 L75 128 L110 88 L145 106 L185 78 L220 95 L260 55 L300 75 L340 45 L380 70 L420 85 L460 62 L500 88 L545 70 L600 50"
            fill="none"
            stroke="#83bdff"
            strokeWidth="2.5"
            strokeLinecap="round"
          />
        </svg>

        <div className="tiny" style={{ color: 'var(--muted)', textAlign: 'center' }}>
          Visualisasi struktur swing high & swing low secara real-time.
        </div>
      </div>
    </div>
  );
}
