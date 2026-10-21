import React, { useState } from 'react';
import {
  Zap,
  ChevronDown,
  ChevronUp,
  Activity,
  Radio
} from 'lucide-react';

export default function FloatingSignalWidget({
  signals = [],
  onRefreshSignals,
  isAutoPilotActive = false,
  onToggleAutoPilot
}) {
  const [isOpen, setIsOpen] = useState(false);
  const signalCount = signals.length;

  return (
    <div
      className="floating-signals-container"
      id="floating-strategy-signals"
    >
      {/* Expanded Floating Signal Card (Read-Only Telemetry) */}
      {isOpen && (
        <div
          className="floating-signals-card"
          id="floating-signals-expanded-card"
        >
          {/* Card Header */}
          <div
            style={{
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
              padding: '12px 14px',
              borderBottom: '1px solid var(--line)',
              background: 'rgba(12, 22, 28, 0.98)',
              position: 'sticky',
              top: 0,
              zIndex: 3
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
              <Zap size={15} style={{ color: 'var(--g)' }} />
              <h3 style={{ fontSize: '13px', margin: 0, fontWeight: 800 }}>Strategy Signals Telemetry</h3>
              <span className="tiny" style={{ background: '#1c342c', color: '#45e0ad', padding: '1px 6px', borderRadius: '10px', fontWeight: 700 }}>
                {signalCount}
              </span>
            </div>
            <button
              type="button"
              className="btn ghost"
              style={{ padding: '3px 6px', fontSize: '10.5px' }}
              onClick={() => setIsOpen(false)}
            >
              <ChevronDown size={14} />
            </button>
          </div>

          <div style={{ padding: '12px 14px' }}>
            {/* AutoPilot Mode Indicator */}
            <div
              style={{
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
                padding: '8px 10px',
                borderRadius: '8px',
                background: isAutoPilotActive ? '#122e23' : '#1c262c',
                border: `1px solid ${isAutoPilotActive ? '#216147' : 'var(--line)'}`,
                marginBottom: '10px'
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <Radio size={14} style={{ color: isAutoPilotActive ? 'var(--g)' : 'var(--muted)' }} />
                <div>
                  <div style={{ fontSize: '11px', fontWeight: 700, color: isAutoPilotActive ? 'var(--g)' : '#fff' }}>
                    {isAutoPilotActive ? 'AutoPilot: Autonomous Active' : 'AutoPilot: Standby (Observing)'}
                  </div>
                  <div className="tiny" style={{ color: 'var(--muted)', fontSize: '9.5px' }}>
                    {isAutoPilotActive
                      ? 'Semua sinyal konfluensi dieksekusi otomatis oleh robot'
                      : 'Eksekusi otomatis dijeda'}
                  </div>
                </div>
              </div>
              {onToggleAutoPilot && (
                <button
                  type="button"
                  className={`btn ${isAutoPilotActive ? 'alt' : ''}`}
                  style={{ fontSize: '10px', padding: '3px 8px' }}
                  onClick={() => onToggleAutoPilot(!isAutoPilotActive)}
                >
                  {isAutoPilotActive ? 'Jeda' : 'Aktifkan'}
                </button>
              )}
            </div>

            {/* Read-Only Signal Feed */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
              {signals.length > 0 ? (
                signals.map((sig, idx) => {
                  const sigId = sig.signal_id || sig.id;
                  const isBuy = sig.action === 'BUY';
                  const lot = sig.recommended_lot || sig.volume || 0.01;
                  return (
                    <div
                      key={sigId || `signal-${idx}`}
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
                            {sig.action} {lot} lot
                          </span>
                        </div>
                        <span className="tag" style={{ fontSize: '9px', background: 'rgba(69, 224, 173, 0.1)', color: 'var(--g)' }}>
                          {isAutoPilotActive ? 'AUTO-ROBOT' : 'TELEMETRY'}
                        </span>
                      </div>

                      <div style={{ fontSize: '10.5px', color: 'var(--muted)', marginBottom: '4px' }}>
                        {sig.reason || 'EMA 9/21 Confluence + RSI Momentum'}
                      </div>

                      {(sig.entry_price || sig.sl || sig.tp) && (
                        <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '9.5px', color: 'var(--muted)', marginTop: '6px' }}>
                          <span>Entry: <strong style={{ color: 'var(--text)' }}>{sig.entry_price ? sig.entry_price.toFixed(sig.symbol?.includes('XAU') ? 2 : (sig.symbol?.includes('JPY') ? 3 : 5)) : '-'}</strong></span>
                          <span>SL: <strong style={{ color: 'var(--red)' }}>{sig.sl ? sig.sl.toFixed(sig.symbol?.includes('XAU') ? 2 : (sig.symbol?.includes('JPY') ? 3 : 5)) : '-'}</strong></span>
                          <span>TP: <strong style={{ color: 'var(--g)' }}>{sig.tp ? sig.tp.toFixed(sig.symbol?.includes('XAU') ? 2 : (sig.symbol?.includes('JPY') ? 3 : 5)) : '-'}</strong></span>
                        </div>
                      )}
                    </div>
                  );
                })
              ) : (
                <div style={{ padding: '16px 8px', textAlign: 'center', color: 'var(--muted)', fontSize: '11px' }}>
                  <Activity size={20} style={{ opacity: 0.3, margin: '0 auto 6px' }} />
                  <div>Tidak ada sinyal konfluensi baru saat ini.</div>
                  <div style={{ fontSize: '10px', marginTop: '2px' }}>Engine memindai timeframe M15 & M5 secara otomatis.</div>
                </div>
              )}
            </div>
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
        title="Live Strategy Signals Telemetry (Read-Only)"
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
