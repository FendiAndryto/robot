import React, { useState } from 'react';
import { BookOpen, Calendar, ArrowUpRight } from 'lucide-react';

const INITIAL_TRADES = [
  { id: 1, symbol: 'XAUUSD', direction: 'BUY', source: 'Manual', time: 'Oct 19, 10:42', pnl: 84.20 },
  { id: 2, symbol: 'EURUSD', direction: 'SELL', source: 'EA', time: 'Oct 19, 09:18', pnl: 42.50 },
  { id: 3, symbol: 'BTCUSD', direction: 'BUY', source: 'Manual', time: 'Oct 18, 21:10', pnl: -18.00 },
  { id: 4, symbol: 'GBPUSD', direction: 'SELL', source: 'EA', time: 'Oct 18, 15:35', pnl: 126.40 },
  { id: 5, symbol: 'XAUUSD', direction: 'SELL', source: 'Unknown', time: 'Oct 17, 14:20', pnl: -55.80 },
  { id: 6, symbol: 'EURUSD', direction: 'BUY', source: 'Manual', time: 'Oct 17, 11:06', pnl: 34.60 },
  { id: 7, symbol: 'XAUUSD', direction: 'BUY', source: 'EA', time: 'Oct 16, 08:52', pnl: 98.20 },
  { id: 8, symbol: 'BTCUSD', direction: 'SELL', source: 'Manual', time: 'Oct 15, 20:11', pnl: -72.00 }
];

export default function JournalTab({ onNavigateAI }) {
  const [filter, setFilter] = useState('All');
  const [search, setSearch] = useState('');
  const [selectedDate, setSelectedDate] = useState(null);

  const filteredTrades = INITIAL_TRADES.filter((trade) => {
    const matchesFilter = filter === 'All' || trade.source === filter;
    const matchesSearch =
      trade.symbol.toLowerCase().includes(search.toLowerCase()) ||
      trade.source.toLowerCase().includes(search.toLowerCase());
    return matchesFilter && matchesSearch;
  });

  return (
    <div className="journal-tab-container animate-fade-in">
      <div className="heading">
        <div>
          <div className="eyebrow">YOUR TRADING HISTORY</div>
          <h1>Trading Journal</h1>
          <div className="sub">Satu jurnal terpadu untuk transaksi manual dan EA algorithmic.</div>
        </div>
        <button
          type="button"
          className="btn alt"
          onClick={() => alert('Export jurnal akan tersedia saat koneksi riwayat MT5 penuh aktif.')}
          id="journal-export-btn"
        >
          <ArrowUpRight size={14} />
          <span>Export ↗</span>
        </button>
      </div>

      {/* KPIs Grid */}
      <div className="grid kpis">
        <div className="card">
          <div className="metric positive">+$1,842.60</div>
          <div className="label">Net P/L · 30 hari</div>
        </div>
        <div className="card">
          <div className="metric">64.8%</div>
          <div className="label">Win Rate</div>
        </div>
        <div className="card">
          <div className="metric">1.72</div>
          <div className="label">Profit Factor</div>
        </div>
        <div className="card">
          <div className="metric negative">−4.6%</div>
          <div className="label">Max Drawdown</div>
        </div>
      </div>

      {/* Filter Tabs */}
      <div style={{ display: 'flex', gap: '7px', overflowX: 'auto', padding: '4px 0 12px' }}>
        {['All', 'Manual', 'EA', 'Unknown'].map((f) => (
          <button
            key={f}
            type="button"
            className={`btn ${filter === f ? '' : 'alt'}`}
            style={{ fontSize: '11px', padding: '7px 14px' }}
            onClick={() => setFilter(f)}
          >
            {f === 'All' ? 'All Trades' : f === 'EA' ? 'EA Trading' : f}
          </button>
        ))}
      </div>

      {/* Search Bar */}
      <div style={{ marginBottom: '14px' }}>
        <input
          type="text"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Cari instrumen atau sumber (cth: XAUUSD, EA, Manual)..."
          style={{
            width: '100%',
            background: '#0b151b',
            border: '1px solid var(--line)',
            color: 'var(--text)',
            padding: '10px 14px',
            borderRadius: '10px',
            outline: 'none',
            fontSize: '12px'
          }}
          id="journal-search-input"
        />
      </div>

      {/* Trade History Table */}
      <div className="card" style={{ marginBottom: '20px' }}>
        <div className="cardhead">
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <BookOpen size={16} style={{ color: 'var(--g)' }} />
            <h3>Trade History</h3>
          </div>
          <span className="tiny">{filteredTrades.length} records</span>
        </div>

        <div style={{ overflowX: 'auto' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '12px' }}>
            <thead>
              <tr style={{ borderBottom: '1px solid var(--line)', textAlign: 'left' }}>
                <th style={{ padding: '10px 8px', color: 'var(--muted)', fontSize: '10px' }}>INSTRUMEN</th>
                <th style={{ padding: '10px 8px', color: 'var(--muted)', fontSize: '10px' }}>ARAH</th>
                <th style={{ padding: '10px 8px', color: 'var(--muted)', fontSize: '10px' }}>SUMBER</th>
                <th style={{ padding: '10px 8px', color: 'var(--muted)', fontSize: '10px' }}>WAKTU</th>
                <th style={{ padding: '10px 8px', color: 'var(--muted)', fontSize: '10px', textAlign: 'right' }}>NET P/L</th>
              </tr>
            </thead>
            <tbody>
              {filteredTrades.map((t) => (
                <tr key={t.id} style={{ borderBottom: '1px solid #1c2b33' }}>
                  <td style={{ padding: '12px 8px', fontWeight: 800 }}>{t.symbol}</td>
                  <td style={{ padding: '12px 8px' }}>
                    <span className={`tag ${t.direction === 'SELL' ? 'red' : ''}`}>
                      {t.direction}
                    </span>
                  </td>
                  <td style={{ padding: '12px 8px' }}>
                    <span className={`tag ${t.source === 'EA' ? 'blue' : t.source === 'Unknown' ? 'amber' : ''}`}>
                      {t.source}
                    </span>
                  </td>
                  <td style={{ padding: '12px 8px', color: 'var(--muted)', fontSize: '11px' }}>{t.time}</td>
                  <td
                    style={{
                      padding: '12px 8px',
                      textAlign: 'right',
                      fontWeight: 800,
                      color: t.pnl >= 0 ? 'var(--g)' : 'var(--red)'
                    }}
                  >
                    {t.pnl >= 0 ? '+' : '−'}${Math.abs(t.pnl).toFixed(2)}
                  </td>
                </tr>
              ))}
              {filteredTrades.length === 0 && (
                <tr>
                  <td colSpan={5} style={{ padding: '24px 8px', textAlign: 'center', color: 'var(--muted)' }}>
                    Tidak ada transaksi yang cocok dengan pencarian.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Trading Calendar */}
      <div className="section" style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '10px' }}>
        <Calendar size={16} style={{ color: 'var(--g)' }} />
        <span>Trading Calendar</span>
        <span className="tiny">Oktober</span>
      </div>

      <div className="card" style={{ marginBottom: '20px' }}>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(7, minmax(0, 1fr))', gap: '6px' }}>
          {['Sen', 'Sel', 'Rab', 'Kam', 'Jum', 'Sab', 'Min'].map((day, idx) => (
            <div key={idx} className="tiny" style={{ textAlign: 'center', padding: '4px', fontWeight: 700 }}>
              {day}
            </div>
          ))}
          {Array.from({ length: 31 }, (_, i) => i + 1).map((d) => {
            const isLoss = d % 7 === 0;
            const isWin = d % 7 !== 0 && d % 3 === 0;
            const bg = isLoss ? '#48242a' : isWin ? '#164236' : '#142229';
            const color = isLoss ? '#ff9ba5' : isWin ? '#7ce8be' : '#8fa2a8';
            return (
              <button
                key={d}
                type="button"
                onClick={() => setSelectedDate(d)}
                style={{
                  border: selectedDate === d ? '1px solid var(--g)' : '1px solid #23373f',
                  borderRadius: '8px',
                  padding: '7px 2px',
                  background: bg,
                  color: color,
                  fontSize: '9.5px',
                  cursor: 'pointer',
                  textAlign: 'center'
                }}
              >
                {d}
                <br />
                {isLoss ? '−$48' : isWin ? '+$42' : '·'}
              </button>
            );
          })}
        </div>
        {selectedDate && (
          <div className="tiny" style={{ marginTop: '12px', color: 'var(--g)' }}>
            Tanggal {selectedDate} Oktober terpilih. Ringkasan performa harian aktif.
          </div>
        )}
      </div>

      {/* AI Pattern Review Card */}
      <div className="card">
        <div className="eyebrow">PATTERN FOUND · AI INSIGHT</div>
        <h3 style={{ margin: '8px 0', fontSize: '14px' }}>Loss cenderung muncul setelah entry terlambat</h3>
        <p className="sub" style={{ lineHeight: 1.5 }}>
          Berdasarkan riwayat transaksi, transaksi BUY memiliki win-rate 68% saat dieksekusi di sesi London,
          namun mengalami penurunan performa jika dieksekusi saat fase konsolidasi New York.
        </p>
        {onNavigateAI && (
          <button
            type="button"
            className="btn alt"
            style={{ marginTop: '12px' }}
            onClick={onNavigateAI}
            id="journal-ai-coach-btn"
          >
            Buka AI Assistant →
          </button>
        )}
      </div>
    </div>
  );
}
