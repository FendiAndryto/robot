import React, { useState } from 'react';
import {
  Monitor,
  X,
  CheckCircle2,
  AlertTriangle,
  RefreshCw,
  Cpu,
  Laptop,
  Check,
  ShieldCheck,
  Zap
} from 'lucide-react';

export default function Mt5ConnectModal({
  isOpen,
  onClose,
  isConnected,
  accountNumber,
  onCheckStatus
}) {
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [copiedUrl, setCopiedUrl] = useState(false);

  if (!isOpen) return null;

  const bridgeUrl = typeof window !== 'undefined' ? window.location.origin : 'https://staging-trade-gear.homever.my.id';

  const handleRefresh = async () => {
    setIsRefreshing(true);
    try {
      if (onCheckStatus) {
        await onCheckStatus();
      }
    } finally {
      setIsRefreshing(false);
    }
  };

  const handleCopyUrl = () => {
    navigator.clipboard.writeText(bridgeUrl);
    setCopiedUrl(true);
    setTimeout(() => setCopiedUrl(false), 2000);
  };

  return (
    <div className="modal-backdrop animate-fade-in" id="mt5-connect-modal-backdrop">
      <div className="mt5-connect-modal glass-panel" id="mt5-connect-modal">
        {/* Modal Header */}
        <div className="mt5-modal-header">
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <div className="mt5-modal-icon-box">
              <Laptop size={22} style={{ color: '#45e0ad' }} />
            </div>
            <div>
              <h3 className="mt5-modal-title">KONEKSI MT5 LOKAL LAPTOP</h3>
              <span className="mt5-modal-subtitle">High-Performance Direct WinINet Bridge</span>
            </div>
          </div>
          <button
            onClick={onClose}
            className="btn-modal-close"
            id="close-mt5-connect-modal-btn"
            title="Tutup Modal"
          >
            <X size={18} />
          </button>
        </div>

        {/* Modal Body */}
        <div className="mt5-modal-body">
          {/* Current Status Pill */}
          <div
            className={`mt5-status-banner ${isConnected ? 'connected' : 'disconnected'}`}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              {isConnected ? (
                <CheckCircle2 size={18} className="text-emerald" />
              ) : (
                <AlertTriangle size={18} className="text-rose" />
              )}
              <span style={{ fontWeight: 700 }}>
                Status Bridge: {isConnected ? 'MT5 LOKAL TERHUBUNG (ONLINE)' : 'MENUNGGU KONEKSI MT5 LOKAL'}
              </span>
            </div>
            {isConnected && accountNumber ? (
              <span style={{ fontSize: '0.8rem', opacity: 0.9, fontFamily: 'monospace' }}>
                Akun #{accountNumber}
              </span>
            ) : null}
          </div>

          {/* Architecture Edge Info */}
          <div
            style={{
              padding: '12px 14px',
              background: 'rgba(69, 224, 173, 0.08)',
              border: '1px solid rgba(69, 224, 173, 0.25)',
              borderRadius: '8px',
              fontSize: '0.8rem',
              display: 'flex',
              flexDirection: 'column',
              gap: '6px'
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px', color: '#45e0ad', fontWeight: 700 }}>
              <ShieldCheck size={15} />
              <span>Direct Laptop Execution (Bebas Freeze Server):</span>
            </div>
            <div style={{ color: 'var(--text-main, #e2e8f0)', lineHeight: 1.4 }}>
              MT5 berjalan langsung pada laptop Anda dengan performa native tanpa beban Wine/VNC server.
              EA mengirimkan telemetry real-time dan mengeksekusi order dari web TradeGear secara instan.
            </div>
          </div>

          {/* Target Backend Endpoint */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
            <span style={{ fontSize: '11px', color: 'var(--muted)', fontWeight: 600 }}>
              URL Target Backend untuk BridgeEA:
            </span>
            <div style={{ display: 'flex', gap: '8px' }}>
              <input
                type="text"
                readOnly
                value={bridgeUrl}
                style={{
                  flex: 1,
                  background: '#0a1419',
                  border: '1px solid var(--line)',
                  borderRadius: '8px',
                  color: '#b8ffe6',
                  fontFamily: 'monospace',
                  fontSize: '12px',
                  padding: '8px 12px'
                }}
              />
              <button
                type="button"
                className="btn alt"
                onClick={handleCopyUrl}
                style={{ fontSize: '11px', padding: '8px 12px' }}
              >
                {copiedUrl ? <Check size={14} style={{ color: '#45e0ad' }} /> : 'Copy'}
              </button>
            </div>
          </div>

          {/* 3 Steps */}
          <div className="mt5-steps-container">
            <h4 className="mt5-steps-title">
              Cara Menghubungkan BridgeEA di MT5 Laptop:
            </h4>

            <div className="mt5-step-card">
              <div className="mt5-step-number">1</div>
              <div className="mt5-step-content">
                <strong>Buka MT5 di Laptop</strong>
                <p>
                  Pastikan akun broker Anda (cth: Exness) sudah login pada terminal MetaTrader 5 di laptop.
                </p>
              </div>
            </div>

            <div className="mt5-step-card">
              <div className="mt5-step-number">2</div>
              <div className="mt5-step-content">
                <strong>Whitelist URL di MT5</strong>
                <p>
                  Buka menu MT5: <strong>Tools &gt; Options &gt; Expert Advisors</strong>. Centang <strong>Allow WebRequest for listed URL</strong> dan tambahkan: <code>{bridgeUrl}</code>.
                </p>
              </div>
            </div>

            <div className="mt5-step-card">
              <div className="mt5-step-number">3</div>
              <div className="mt5-step-content">
                <strong>Pasang BridgeEA pada Chart</strong>
                <p>
                  Drag <code>BridgeEA</code> ke chart aktif (cth: XAUUSD M15). Pada tab <em>Common</em>, centang <strong>Allow Algo Trading</strong> (Pure WebRequest, siap untuk MQL5 VPS tanpa perlu DLL).
                </p>
              </div>
            </div>
          </div>

          <p className="mt5-success-note">
            💡 Status di dashboard ini akan otomatis menyala <strong>CONNECTED (HIJAU)</strong> dan menampilkan saldo, posisi aktif, dan riwayat secara langsung dari laptop Anda.
          </p>
        </div>

        {/* Modal Footer */}
        <div className="mt5-modal-footer">
          <button
            type="button"
            className="btn alt"
            onClick={handleRefresh}
            disabled={isRefreshing}
            id="refresh-mt5-status-btn"
          >
            <RefreshCw size={14} className={isRefreshing ? 'animate-spin' : ''} />
            <span>{isRefreshing ? 'Memeriksa...' : 'Cek Status Sekarang'}</span>
          </button>
          <button
            type="button"
            className="btn"
            onClick={onClose}
            id="close-mt5-modal-action-btn"
          >
            <span>Tutup</span>
          </button>
        </div>
      </div>
    </div>
  );
}
