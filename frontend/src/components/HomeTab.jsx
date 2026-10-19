import React, { useState } from 'react';
import {
  DollarSign,
  Activity,
  TrendingUp,
  TrendingDown,
  Layers,
  Plus,
  RefreshCw,
  XCircle
} from 'lucide-react';
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

export default function HomeTab({
  bridgeStatus,
  onOpenNewTrade,
  onNavigateJournal,
  onNavigateAI,
  onNavigateMarket,
  onRefresh
}) {
  const [chartRange, setChartRange] = useState('1M');
  const [closingTicket, setClosingTicket] = useState(null);

  const metrics = bridgeStatus?.metrics || {};
  const isConnected = bridgeStatus?.is_connected || false;
  const currency = metrics.currency || 'USD';
  const balance = metrics.balance ?? 0;
  const equity = metrics.equity ?? 0;
  const floatingPnl = metrics.floating_pnl ?? 0;
  const openPositionsCount = metrics.open_positions ?? 0;
  const positions = bridgeStatus?.positions || metrics.positions || [];

  const handleClosePosition = async (ticket) => {
    if (!window.confirm(`Konfirmasi tutup posisi ticket #${ticket}?`)) return;
    setClosingTicket(ticket);
    try {
      await api.closePosition(ticket);
      if (onRefresh) onRefresh();
    } catch (err) {
      alert(`Gagal menutup posisi: ${err.message || 'Error'}`);
    } finally {
      setClosingTicket(null);
    }
  };

  return (
    <div className="home-tab-container animate-fade-in">
      {/* Heading & Account Pill */}
      <div className="heading">
        <div>
          <div className="eyebrow">TRADING COMMAND CENTER</div>
          <h1>Good morning, Trader.</h1>
          <div className="sub">Semua metrik dan eksekusi MT5, dalam satu tampilan terpadu.</div>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <select
            style={{
              border: '1px solid var(--line)',
              background: '#0d171d',
              color: '#d4e0e1',
              padding: '7px 12px',
              borderRadius: '10px',
              fontSize: '11px',
              outline: 'none',
              cursor: 'pointer'
            }}
            id="home-account-select"
            defaultValue="main"
          >
            <option value="main">MT5 • Main Account</option>
            <option value="ea">MT5 • EA Confluence</option>
            <option value="demo">Demo • Sandbox</option>
          </select>
          {onRefresh && (
            <button
              type="button"
              className="btn alt"
              onClick={onRefresh}
              title="Refresh Telemetry"
              style={{ padding: '7px 10px', fontSize: '11px' }}
              id="home-refresh-btn"
            >
              <RefreshCw size={13} />
            </button>
          )}
        </div>
      </div>

      {/* Hero Edge Banner */}
      <div className="banner" style={{ marginBottom: '16px' }}>
        <div className="eyebrow">YOUR EDGE, IN ONE PLACE</div>
        <h2>Trade smarter. Review deeper.</h2>
        <p>
          Pantau posisi aktif, pahami performa akun secara objektif, dan eksekusi sinyal presisi
          dengan proteksi risiko drawdown otomatis.
        </p>
        <div className="btns" style={{ marginTop: '14px' }}>
          {onOpenNewTrade && (
            <button
              type="button"
              className="btn"
              onClick={onOpenNewTrade}
              id="home-banner-new-trade-btn"
            >
              <Plus size={14} />
              <span>Buka Order Baru</span>
            </button>
          )}
          {onNavigateJournal && (
            <button
              type="button"
              className="btn alt"
              onClick={onNavigateJournal}
              id="home-banner-journal-btn"
            >
              <span>Buka Jurnal</span>
            </button>
          )}
          {onNavigateAI && (
            <button
              type="button"
              className="btn ghost"
              onClick={onNavigateAI}
              id="home-banner-ai-btn"
            >
              <span>Tanya AI Assistant ↗</span>
            </button>
          )}
        </div>
      </div>

      {/* KPIs Grid */}
      <div className="grid kpis">
        {/* Total Balance */}
        <div className="card" id="home-kpi-balance">
          <div className="cardhead">
            <span className="label">Total Balance</span>
            <span className="icon-box">
              <DollarSign size={16} />
            </span>
          </div>
          <div className="metric">{formatCurrency(balance, currency)}</div>
          <div className="delta">Settled funds</div>
        </div>

        {/* Equity */}
        <div className="card" id="home-kpi-equity">
          <div className="cardhead">
            <span className="label">Account Equity</span>
            <span className="icon-box">
              <Activity size={16} />
            </span>
          </div>
          <div className="metric">{formatCurrency(equity, currency)}</div>
          <div className="delta" style={{ color: floatingPnl >= 0 ? 'var(--g)' : 'var(--red)' }}>
            Floating {floatingPnl >= 0 ? '+' : ''}{formatCurrency(floatingPnl, currency)}
          </div>
        </div>

        {/* Today's P/L */}
        <div className="card" id="home-kpi-today-pnl">
          <div className="cardhead">
            <span className="label">Floating P/L</span>
            <span className="icon-box">
              {floatingPnl >= 0 ? <TrendingUp size={16} /> : <TrendingDown size={16} />}
            </span>
          </div>
          <div className={`metric ${floatingPnl >= 0 ? 'positive' : 'negative'}`}>
            {floatingPnl >= 0 ? '+' : ''}{formatCurrency(floatingPnl, currency)}
          </div>
          <div className="delta">
            {openPositionsCount > 0 ? `${openPositionsCount} active position(s)` : 'Zero active risk'}
          </div>
        </div>

        {/* Open Positions */}
        <div className="card" id="home-kpi-positions">
          <div className="cardhead">
            <span className="label">Active Positions</span>
            <span className="icon-box">
              <Layers size={16} />
            </span>
          </div>
          <div className="metric">
            {openPositionsCount.toString().padStart(2, '0')}{' '}
            <span className="sub" style={{ fontSize: '12px' }}>posisi</span>
          </div>
          <div className="delta" style={{ color: 'var(--amber)' }}>
            {isConnected ? 'Bridge Synchronized' : 'Bridge Offline'}
          </div>
        </div>
      </div>

      {/* Account Performance Curve & Market Brief */}
      <div className="grid two" style={{ marginBottom: '20px' }}>
        {/* Performance Chart */}
        <div className="card">
          <div className="cardhead">
            <div>
              <h3>Account Performance</h3>
              <div className="tiny">Equity growth curve · live MT5 tracking</div>
            </div>
            <div style={{ display: 'flex', gap: '3px', background: '#0a1419', padding: '3px', borderRadius: '8px', border: '1px solid var(--line)' }}>
              {['1W', '1M', '3M', 'ALL'].map((rng) => (
                <button
                  key={rng}
                  type="button"
                  style={{
                    border: 0,
                    background: chartRange === rng ? '#205342' : 'transparent',
                    color: chartRange === rng ? '#b8ffe6' : 'var(--muted)',
                    fontSize: '10px',
                    fontWeight: 700,
                    padding: '5px 8px',
                    borderRadius: '6px',
                    cursor: 'pointer'
                  }}
                  onClick={() => setChartRange(rng)}
                >
                  {rng}
                </button>
              ))}
            </div>
          </div>

          <svg className="chart" viewBox="0 0 600 180" preserveAspectRatio="none" style={{ width: '100%', height: '175px', display: 'block' }}>
            <defs>
              <linearGradient id="tradegear-area" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0" stopColor="#45e0ad" stopOpacity="0.25" />
                <stop offset="1" stopColor="#45e0ad" stopOpacity="0" />
              </linearGradient>
            </defs>
            <g stroke="#1e343d" strokeDasharray="4 7">
              <path d="M0 35H600M0 75H600M0 115H600M0 155H600" />
            </g>
            <path
              d="M0 153 C35 143 38 155 68 129 S105 135 135 111 S175 127 207 94 S245 111 276 84 S312 98 342 69 S378 88 407 62 S450 79 478 48 S515 68 540 39 S573 50 600 22 L600 180 L0 180Z"
              fill="url(#tradegear-area)"
            />
            <path
              d="M0 153 C35 143 38 155 68 129 S105 135 135 111 S175 127 207 94 S245 111 276 84 S312 98 342 69 S378 88 407 62 S450 79 478 48 S515 68 540 39 S573 50 600 22"
              fill="none"
              stroke="#45e0ad"
              strokeWidth="2.5"
              strokeLinecap="round"
            />
          </svg>
          <div style={{ display: 'flex', justifyContent: 'space-between', color: 'var(--muted)', fontSize: '9px', marginTop: '6px' }}>
            <span>Sep 19</span>
            <span>Sep 26</span>
            <span>Oct 03</span>
            <span>Oct 10</span>
            <span>Today</span>
          </div>
        </div>

        {/* AI Market Brief Card */}
        <div className="card">
          <div className="cardhead">
            <h3>AI Market Brief</h3>
            <span className="tag blue">LIVE BRIEF</span>
          </div>
          <div className="row">
            <div className="coin">Au</div>
            <div className="grow">
              <div className="rowtitle">XAUUSD</div>
              <div className="rowsub">Momentum bullish menguat · pantau 4,210</div>
            </div>
            <div className="end">
              $4,218.60<small className="positive">+0.42%</small>
            </div>
          </div>
          <div className="row">
            <div className="coin">₿</div>
            <div className="grow">
              <div className="rowtitle">BTCUSD</div>
              <div className="rowsub">Range konsolidasi · tunggu konfirmasi breakout</div>
            </div>
            <div className="end">
              $67,240<small className="negative">−0.18%</small>
            </div>
          </div>
          <div className="sub" style={{ marginTop: '10px', fontSize: '11px', color: 'var(--muted)' }}>
            Ringkasan korelasi dan tren teknikal terintegrasi dengan MT5 tick stream.
          </div>
          {onNavigateMarket && (
            <button
              type="button"
              className="btn alt"
              style={{ marginTop: '12px', width: '100%' }}
              onClick={onNavigateMarket}
              id="home-open-market-btn"
            >
              <span>Buka Market Overview →</span>
            </button>
          )}
        </div>
      </div>

      {/* Active Trades Section */}
      <div className="section" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '10px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <Layers size={16} style={{ color: 'var(--g)' }} />
          <span style={{ fontSize: '14px', fontWeight: 800 }}>Active Trades</span>
          <span className="tiny">({positions.length} running on MT5)</span>
        </div>
        {onNavigateJournal && (
          <button
            type="button"
            className="btn ghost"
            style={{ fontSize: '11px', padding: '5px 10px' }}
            onClick={onNavigateJournal}
            id="home-view-all-trades-btn"
          >
            <span>Semua transaksi →</span>
          </button>
        )}
      </div>

      <div className="card" style={{ marginBottom: '20px' }}>
        {positions.length > 0 ? (
          positions.map((pos) => {
            const isBuy = String(pos.type || '').toUpperCase() === 'BUY' || pos.type === 0;
            const profit = pos.profit ?? 0;
            return (
              <div key={pos.ticket} className="row">
                <div className="coin">
                  {pos.symbol?.slice(0, 2).toUpperCase() || 'FX'}
                </div>
                <div className="grow">
                  <div className="rowtitle" style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                    <span>{pos.symbol}</span>
                    <span className={`tag ${!isBuy ? 'red' : ''}`}>
                      {isBuy ? 'BUY' : 'SELL'}
                    </span>
                    <span className="tiny" style={{ color: 'var(--muted)' }}>
                      #{pos.ticket}
                    </span>
                  </div>
                  <div className="rowsub">
                    {pos.volume} lot · Entry @ {pos.open_price}
                    {pos.sl ? ` · SL ${pos.sl}` : ''}
                    {pos.tp ? ` · TP ${pos.tp}` : ''}
                  </div>
                </div>
                <div className="end" style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                  <div style={{ textAlign: 'right' }}>
                    <div style={{ color: profit >= 0 ? 'var(--g)' : 'var(--red)', fontWeight: 800 }}>
                      {profit >= 0 ? '+' : ''}{formatCurrency(profit, currency)}
                    </div>
                    <small>Floating PnL</small>
                  </div>
                  <button
                    type="button"
                    className="btn alt"
                    style={{ padding: '6px 8px', fontSize: '11px', color: 'var(--red)' }}
                    onClick={() => handleClosePosition(pos.ticket)}
                    disabled={closingTicket === pos.ticket}
                    title="Close position immediately on MT5"
                    id={`close-pos-${pos.ticket}-btn`}
                  >
                    <XCircle size={14} />
                  </button>
                </div>
              </div>
            );
          })
        ) : (
          <div style={{ padding: '24px 16px', textAlign: 'center', color: 'var(--muted)' }}>
            <div>Tidak ada posisi aktif yang sedang berjalan di terminal MT5.</div>
            {onOpenNewTrade && (
              <button
                type="button"
                className="btn alt"
                style={{ marginTop: '12px', fontSize: '11px' }}
                onClick={onOpenNewTrade}
              >
                <Plus size={13} />
                <span>Buka Posisi Baru</span>
              </button>
            )}
          </div>
        )}
      </div>

      {/* Performance Snapshot */}
      <div className="section" style={{ fontSize: '14px', fontWeight: 800, marginBottom: '10px' }}>
        Performance Snapshot
      </div>
      <div className="grid three">
        <div className="card">
          <div className="metric">64.8%</div>
          <div className="label">Win Rate</div>
          <div className="tiny">Sample 125 trades</div>
        </div>
        <div className="card">
          <div className="metric">1.72</div>
          <div className="label">Profit Factor</div>
          <div className="tiny">Risk-adjusted return</div>
        </div>
        <div className="card">
          <div className="metric negative">−4.6%</div>
          <div className="label">Max Drawdown</div>
          <div className="tiny">Within 3% daily guard buffer</div>
        </div>
      </div>
    </div>
  );
}
