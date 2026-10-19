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

export default function Mt5ConnectModal({
  isOpen,
  onClose,
  isConnected,
  accountNumber,
  onCheckStatus
}) {
  const defaultUrl =
    import.meta.env.VITE_MT5_VNC_URL ||
    `${window.location.protocol}//${window.location.hostname}:8088`;

  const [vncUrl, setVncUrl] = useState(() => {
    return localStorage.getItem('robot_mt5_vnc_url') || defaultUrl;
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
