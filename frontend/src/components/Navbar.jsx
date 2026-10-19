import React from 'react';
import { Bot, LogOut, Clock, Wifi, WifiOff } from 'lucide-react';

export default function Navbar({
  isConnected,
  latency,
  pollInterval,
  onPollIntervalChange,
  username,
  onLogout
}) {
  return (
    <header className="navbar" id="main-navbar">
      <div className="brand-wrapper">
        <div className="brand-icon-box">
          <Bot size={22} />
        </div>
        <div>
          <h2 className="brand-title">ROBOT TRADING MT5</h2>
          <span className="brand-tag">Bridge & Execution Engine</span>
        </div>
      </div>

      <div className="nav-actions">
        {/* Live Status Badge */}
        <div
          className={`status-badge ${isConnected ? 'connected' : 'disconnected'}`}
          id="connection-status-badge"
          title={isConnected ? 'Bridge EA actively streaming telemetry' : 'Bridge EA is offline or timed out'}
        >
          <span className={`pulse-dot ${isConnected ? 'online' : 'offline'}`} />
          <span>{isConnected ? 'CONNECTED' : 'DISCONNECTED'}</span>
          {latency !== null && latency !== undefined && (
            <span style={{ opacity: 0.75, fontSize: '0.75rem', marginLeft: '4px' }}>
              ({latency}s)
            </span>
          )}
        </div>

        {/* Polling Interval Selector */}
        <div className="poll-selector" title="Telemetry refresh frequency">
          <Clock size={14} />
          <label htmlFor="poll-interval-select" style={{ display: 'none' }}>Refresh Rate</label>
          <select
            id="poll-interval-select"
            value={pollInterval}
            onChange={(e) => onPollIntervalChange(Number(e.target.value))}
          >
            <option value={1000}>Refresh: 1s</option>
            <option value={2000}>Refresh: 2s</option>
            <option value={5000}>Refresh: 5s</option>
          </select>
        </div>

        {/* User Info & Logout */}
        <div className="user-badge" id="current-user-badge">
          <span>{username || 'Admin'}</span>
        </div>

        <button
          onClick={onLogout}
          className="btn-logout"
          id="logout-btn"
          title="Sign out of dashboard"
        >
          <LogOut size={16} />
          <span>Logout</span>
        </button>
      </div>
    </header>
  );
}
