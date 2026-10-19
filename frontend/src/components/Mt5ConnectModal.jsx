import React, { useState } from 'react';
import {
  Monitor,
  X,
  ExternalLink,
  CheckCircle2,
  AlertTriangle,
  RefreshCw,
  KeyRound,
  Server,
  Settings2
} from 'lucide-react';

const getDefaultVncUrl = () => {
  if (import.meta.env.VITE_MT5_VNC_URL) {
    return import.meta.env.VITE_MT5_VNC_URL;
  }
  if (typeof window === 'undefined') return 'http://localhost:8088';

  const host = window.location.hostname;
  // Local development or direct IP
  if (host === 'localhost' || host === '127.0.0.1' || /^(\d+\.){3}\d+$/.test(host)) {
    return `${window.location.protocol}//${host}:8088`;
  }
  // Staging deployment
  if (host.includes('staging-trade-gear.homever.my.id')) {
    return 'https://staging-mt5.homever.my.id';
  }
  // Production deployment
  if (host.includes('trade-gear.homever.my.id')) {
    return 'https://mt5.trade-gear.homever.my.id';
  }
  // Fallback for custom homever.my.id subdomains
  if (host.endsWith('homever.my.id')) {
    if (host.startsWith('staging-')) {
      return 'https://staging-mt5.homever.my.id';
    }
    return 'https://mt5.trade-gear.homever.my.id';
  }
  return `${window.location.protocol}//${host}:8088`;
};

export default function Mt5ConnectModal({
  isOpen,
  onClose,
  isConnected,
  accountNumber,
  onCheckStatus
}) {
  const defaultUrl = getDefaultVncUrl();

  const [vncUrl, setVncUrl] = useState(() => {
    const saved = localStorage.getItem('robot_mt5_vnc_url');
    // Sanitize stale URL with port :8088 on public domain that causes timeouts
    if (
      saved &&
      saved.includes(':8088') &&
      !saved.includes('localhost') &&
      !saved.includes('127.0.0.1') &&
      !/(\d+\.){3}\d+/.test(saved)
    ) {
      const fresh = getDefaultVncUrl();
      localStorage.setItem('robot_mt5_vnc_url', fresh);
      return fresh;
    }
    return saved || defaultUrl;
  });
  const [showConfig, setShowConfig] = useState(false);
  const [isRefreshing, setIsRefreshing] = useState(false);

  if (!isOpen) return null;

  const handleOpenVnc = () => {
    window.open(vncUrl, '_blank', 'noopener,noreferrer');
  };

  const handleSaveUrl = (newUrl) => {
    setVncUrl(newUrl);
    localStorage.setItem('robot_mt5_vnc_url', newUrl);
  };

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

  return (
    <div className="modal-backdrop animate-fade-in" id="mt5-connect-modal-backdrop">
      <div className="mt5-connect-modal glass-panel" id="mt5-connect-modal">
        {/* Modal Header */}
        <div className="mt5-modal-header">
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <div className="mt5-modal-icon-box">
              <Monitor size={22} />
            </div>
            <div>
              <h3 className="mt5-modal-title">KONEKSI & LOGIN MT5 TERMINAL</h3>
              <span className="mt5-modal-subtitle">Web-to-MT5 Visual Interface (noVNC)</span>
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
              <span style={{ fontWeight: 600 }}>
                Status Jembatan: {isConnected ? 'TERHUBUNG (ONLINE)' : 'TERPUTUS (OFFLINE)'}
              </span>
            </div>
            {isConnected && accountNumber ? (
              <span style={{ fontSize: '0.8rem', opacity: 0.9 }}>
                Akun #{accountNumber}
              </span>
            ) : (
              <span style={{ fontSize: '0.8rem', opacity: 0.85 }}>
                Memerlukan login broker
              </span>
            )}
          </div>

          {/* VNC Terminal Web Credentials Card */}
          <div
            style={{
              padding: '12px 14px',
              background: 'rgba(56, 189, 248, 0.08)',
              border: '1px solid rgba(56, 189, 248, 0.25)',
              borderRadius: '8px',
              fontSize: '0.8rem',
              display: 'flex',
              flexDirection: 'column',
              gap: '6px'
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px', color: '#38bdf8', fontWeight: 600 }}>
              <KeyRound size={14} />
              <span>Kredensial Akses Terminal Web MT5 (Browser Prompt):</span>
            </div>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '16px', color: 'var(--text-main, #e2e8f0)', fontFamily: 'monospace' }}>
              <div>User: <strong>fendi</strong></div>
              <div>Password: <strong>fendi123</strong></div>
            </div>
            <div style={{ fontSize: '0.72rem', color: 'var(--text-muted, #94a3b8)' }}>
              * Masukkan user & password di atas jika browser Anda meminta otentikasi saat halaman MT5 terbuka.
            </div>
          </div>

          {/* 3-Step Guided Walkthrough */}
          <div className="mt5-steps-container">
            <h4 className="mt5-steps-title">
              Cara Login Akun Broker (Tanpa Coding / Tanpa Terminal):
            </h4>

            <div className="mt5-step-card">
              <div className="mt5-step-number">1</div>
              <div className="mt5-step-content">
                <strong>Buka Layar Visual MT5</strong>
                <p>
                  Klik tombol <em>"Buka Layar MT5 di Tab Baru"</em> di bawah. Jendela visual MT5 asli akan muncul di tab browser Anda.
                </p>
              </div>
            </div>

            <div className="mt5-step-card">
              <div className="mt5-step-number">2</div>
              <div className="mt5-step-content">
                <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                  <KeyRound size={14} style={{ color: 'var(--accent-cyan)' }} />
                  <strong>Pilih Menu Login</strong>
                </div>
                <p>
                  Di pojok kiri atas jendela MT5, klik menu:
                  <br />
                  <code className="mt5-inline-code">File ➔ Login to Trade Account</code>
                </p>
              </div>
            </div>

            <div className="mt5-step-card">
              <div className="mt5-step-number">3</div>
              <div className="mt5-step-content">
                <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                  <Server size={14} style={{ color: 'var(--accent-cyan)' }} />
                  <strong>Masukkan Data Broker Anda</strong>
                </div>
                <p>
                  Isi <strong>Login (No. Akun)</strong>, <strong>Password</strong>, dan pilih <strong>Server Broker</strong> Anda, lalu klik <strong>OK</strong>.
                </p>
              </div>
            </div>
          </div>

          <p className="mt5-success-note">
            💡 Begitu MT5 Anda berhasil login dan chart aktif, dashboard ini akan <strong>otomatis langsung berubah menjadi HIJAU (CONNECTED)</strong> dan menampilkan saldo Anda secara live.
          </p>

          {/* Advanced / Custom URL Config */}
          <div className="mt5-config-section">
            <button
              type="button"
              className="btn-toggle-config"
              onClick={() => setShowConfig(!showConfig)}
            >
              <Settings2 size={13} />
              <span>{showConfig ? 'Sembunyikan Pengaturan URL' : 'Kustomisasi URL MT5 (Jika Pakai Domain Khusus)'}</span>
            </button>

            {showConfig && (
              <div className="mt5-config-input-box animate-fade-in">
                <label htmlFor="mt5-vnc-url-input" style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                  Target Web-GUI URL:
                </label>
                <div style={{ display: 'flex', gap: '8px', marginTop: '4px' }}>
                  <input
                    id="mt5-vnc-url-input"
                    type="text"
                    value={vncUrl}
                    onChange={(e) => handleSaveUrl(e.target.value)}
                    placeholder="http://localhost:8088"
                    className="mt5-url-input"
                  />
                  <button
                    type="button"
                    onClick={() => handleSaveUrl(defaultUrl)}
                    className="btn-reset-url"
                    title="Kembalikan ke URL default"
                  >
                    Reset
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Modal Footer */}
        <div className="mt5-modal-footer">
          <button
            type="button"
            onClick={handleRefresh}
            disabled={isRefreshing}
            className="btn-check-status"
            id="refresh-mt5-status-btn"
          >
            <RefreshCw size={14} className={isRefreshing ? 'animate-spin' : ''} />
            <span>{isRefreshing ? 'Memeriksa...' : 'Cek Status Sekarang'}</span>
          </button>

          <button
            type="button"
            onClick={handleOpenVnc}
            className="btn-open-mt5-primary"
            id="open-mt5-vnc-primary-btn"
          >
            <ExternalLink size={16} />
            <span>Buka Layar MT5 di Tab Baru</span>
          </button>
        </div>
      </div>
    </div>
  );
}
