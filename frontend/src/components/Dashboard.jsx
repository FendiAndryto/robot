import React, { useState, useEffect, useRef } from 'react';
import {
  DollarSign,
  Activity,
  TrendingUp,
  TrendingDown,
  ShieldAlert,
  ShieldCheck,
  CreditCard,
  Layers,
  Server,
  AlertTriangle,
  RefreshCw,
  Radio
} from 'lucide-react';
import Navbar from './Navbar';
import MetricCard from './MetricCard';
import OrderForm from './OrderForm';
import PositionsTable from './PositionsTable';
import KillSwitchModal from './KillSwitchModal';
import RiskBanner from './RiskBanner';
import SignalsPanel from './SignalsPanel';
import DrawdownGuardCard from './DrawdownGuardCard';
import DrawdownBanner from './DrawdownBanner';
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

export default function Dashboard({ user, onLogout }) {
  const [bridgeStatus, setBridgeStatus] = useState(null);
  const [loading, setLoading] = useState(true);
  const [pollInterval, setPollInterval] = useState(1000);
  const [signals, setSignals] = useState([]);
  const [autopilotStatus, setAutopilotStatus] = useState(null);
  const [isResettingDrawdown, setIsResettingDrawdown] = useState(false);
  const [isKillSwitchModalOpen, setIsKillSwitchModalOpen] = useState(false);
  const [isUnlockingEngine, setIsUnlockingEngine] = useState(false);
  const timerRef = useRef(null);

  const fetchSignals = async () => {
    try {
      const data = await api.getSignals();
      setSignals(data);
    } catch {
      // Ignore transient network errors during polling
    }
  };

  const fetchAutoPilotStatus = async () => {
    try {
      const data = await api.getAutoPilotStatus();
      setAutopilotStatus(data);
    } catch {
      // Ignore transient network errors during polling
    }
  };

  const fetchStatus = async () => {
    try {
      const data = await api.getBridgeStatus();
      setBridgeStatus(data);
    } catch (err) {
      // In case backend is unreachable or returns error
      setBridgeStatus((prev) => ({
        ...prev,
        is_connected: false,
        terminal_connected: false,
        seconds_since_last_heartbeat: null
      }));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchStatus();
    fetchSignals();
    fetchAutoPilotStatus();
    timerRef.current = setInterval(() => {
      fetchStatus();
      fetchSignals();
      fetchAutoPilotStatus();
    }, pollInterval);

    return () => {
      if (timerRef.current) clearInterval(timerRef.current);
    };
  }, [pollInterval]);

  const handleTriggerKillSwitch = async (reason) => {
    await api.triggerKillSwitch(reason);
    await fetchStatus();
    await fetchAutoPilotStatus();
  };

  const handleUnlockEngine = async () => {
    setIsUnlockingEngine(true);
    try {
      await api.disarmKillSwitch();
      await fetchStatus();
      await fetchAutoPilotStatus();
    } finally {
      setIsUnlockingEngine(false);
    }
  };

  const handleToggleAutoPilot = async (enabled) => {
    try {
      await api.toggleAutoPilot(enabled);
      await fetchAutoPilotStatus();
    } catch (err) {
      console.error('Failed to toggle AutoPilot:', err);
    }
  };

  const handleResetDrawdown = async (newBaseline) => {
    setIsResettingDrawdown(true);
    try {
      await api.resetDrawdownGuard(newBaseline);
      await fetchAutoPilotStatus();
      await fetchStatus();
    } catch (err) {
      console.error('Failed to reset Drawdown Guard:', err);
    } finally {
      setIsResettingDrawdown(false);
    }
  };

  const metrics = bridgeStatus?.metrics || {};
  const isConnected = bridgeStatus?.is_connected || false;
  const terminalConnected = bridgeStatus?.terminal_connected || false;
  const isKillSwitchActive = bridgeStatus?.is_kill_switch_active || false;
  const killSwitchReason = bridgeStatus?.kill_switch_reason;
  const killSwitchTime = bridgeStatus?.kill_switch_time;

  const currency = metrics.currency || 'USD';
  const balance = metrics.balance ?? 0;
  const equity = metrics.equity ?? 0;
  const floatingPnl = metrics.floating_pnl ?? 0;
  const margin = metrics.margin ?? 0;
  const freeMargin = metrics.free_margin ?? 0;
  const marginLevel = metrics.margin_level ?? 0;
  const openPositions = metrics.open_positions ?? 0;
  const server = metrics.server || 'Unknown Server';
  const accountNumber = metrics.account_number || 0;
  const lastHeartbeatAt = bridgeStatus?.last_heartbeat_at;
  const secondsSinceHeartbeat = bridgeStatus?.seconds_since_last_heartbeat ?? null;
  const positions = bridgeStatus?.positions || metrics.positions || [];

  // Margin progress bar calculation
  let marginProgress = 100;
  let marginColor = 'var(--accent-emerald)';
  if (marginLevel > 0) {
    if (marginLevel < 150) {
      marginProgress = 20;
      marginColor = 'var(--accent-rose)';
    } else if (marginLevel < 500) {
      marginProgress = 50;
      marginColor = 'var(--accent-amber)';
    } else {
      marginProgress = Math.min(100, marginLevel / 50);
      marginColor = 'var(--accent-emerald)';
    }
  }

  return (
    <div className="app-container" id="dashboard-view">
      <Navbar
        isConnected={isConnected}
        latency={secondsSinceHeartbeat}
        pollInterval={pollInterval}
        onPollIntervalChange={setPollInterval}
        username={user?.username}
        onLogout={onLogout}
        onTriggerKillSwitch={() => setIsKillSwitchModalOpen(true)}
        isKillSwitchActive={isKillSwitchActive}
        isAutoPilotActive={autopilotStatus?.is_autopilot_active ?? false}
        isDrawdownLocked={autopilotStatus?.is_drawdown_lockout_active ?? false}
        onToggleAutoPilot={handleToggleAutoPilot}
      />

      <main className="dashboard-content animate-fade-in">
        {/* Emergency Kill Switch Banner */}
        {isKillSwitchActive && (
          <RiskBanner
            reason={killSwitchReason}
            triggeredAt={killSwitchTime}
            onUnlock={handleUnlockEngine}
            isUnlocking={isUnlockingEngine}
          />
        )}

        {/* Daily Drawdown Lockout Banner */}
        {autopilotStatus?.is_drawdown_lockout_active && (
          <DrawdownBanner
            reason={autopilotStatus.drawdown_lockout_reason}
            lockoutTime={autopilotStatus.lockout_time}
            onResetGuard={handleResetDrawdown}
            isResetting={isResettingDrawdown}
          />
        )}

        {/* Offline / Disconnected Alert Banner */}
        {!isConnected && (
          <div className="disconnect-alert" id="disconnect-alert-banner">
            <AlertTriangle size={22} style={{ flexShrink: 0 }} />
            <div>
              <strong>MT5 Bridge Disconnected:</strong> Telemetry stream is currently inactive.
              The bridge drops to disconnected status within seconds when the MT5 terminal is closed or offline.
            </div>
          </div>
        )}

        {isConnected && !terminalConnected && (
          <div className="disconnect-alert" style={{ background: 'rgba(245, 158, 11, 0.15)', borderColor: 'var(--accent-amber)', color: '#fef3c7' }}>
            <AlertTriangle size={22} style={{ flexShrink: 0, color: 'var(--accent-amber)' }} />
            <div>
              <strong>Broker Offline:</strong> MT5 terminal is running and connected to FastAPI, but terminal reports no connection to the broker server.
            </div>
          </div>
        )}

        {/* Account Info Bar */}
        <div className="account-banner glass-panel">
          <div className="account-info-left">
            <div className="server-pill" id="broker-server-pill">
              <Server size={14} style={{ display: 'inline', marginRight: '5px', verticalAlign: 'text-bottom' }} />
              {server}
            </div>
            <div>
              <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', textTransform: 'uppercase' }}>MT5 Login</div>
              <div className="account-num" id="account-number-display">
                {accountNumber ? `#${accountNumber}` : 'Account Disconnected'}
              </div>
            </div>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
            <div style={{ textAlign: 'right' }}>
              <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>TERMINAL STATE</div>
              <div style={{ fontSize: '0.85rem', fontWeight: 700, color: terminalConnected ? 'var(--accent-emerald)' : 'var(--accent-rose)' }}>
                {terminalConnected ? 'BROKER ONLINE' : 'BROKER OFFLINE'}
              </div>
            </div>
            <button
              onClick={fetchStatus}
              className="btn-logout"
              style={{ background: 'rgba(255,255,255,0.06)', borderColor: 'var(--border-subtle)', color: 'var(--text-primary)' }}
              id="manual-refresh-btn"
              title="Refresh telemetry immediately"
            >
              <RefreshCw size={14} />
            </button>
          </div>
        </div>

        {/* Daily Drawdown Guard Progress & AutoPilot Telemetry Card */}
        <DrawdownGuardCard
          autopilotStatus={autopilotStatus}
          currency={currency}
        />

        {/* Metric Cards Grid */}
        <div className="metrics-grid" id="metrics-cards-grid">
          {/* Balance Card */}
          <MetricCard
            id="metric-balance-card"
            label="Account Balance"
            value={formatCurrency(balance, currency)}
            subtext="Settled account funds"
            icon={DollarSign}
            variant="cyan"
          />

          {/* Equity Card */}
          <MetricCard
            id="metric-equity-card"
            label="Account Equity"
            value={formatCurrency(equity, currency)}
            subtext={
              floatingPnl !== 0
                ? `${floatingPnl >= 0 ? '+' : ''}${formatCurrency(floatingPnl, currency)} vs Balance`
                : 'Equal to balance'
            }
            icon={Activity}
            variant={floatingPnl >= 0 ? 'profit' : 'loss'}
          />

          {/* Floating PnL Card */}
          <MetricCard
            id="metric-floating-pnl-card"
            label="Floating Profit / Loss"
            value={`${floatingPnl >= 0 ? '+' : ''}${formatCurrency(floatingPnl, currency)}`}
            subtext={openPositions > 0 ? `Across ${openPositions} open position(s)` : 'Zero active floating risk'}
            icon={floatingPnl >= 0 ? TrendingUp : TrendingDown}
            variant={floatingPnl > 0 ? 'profit' : floatingPnl < 0 ? 'loss' : 'default'}
          />

          {/* Margin Level Card */}
          <MetricCard
            id="metric-margin-level-card"
            label="Margin Level"
            value={margin > 0 ? `${marginLevel.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}%` : 'Unlimited'}
            subtext={margin > 0 ? `Margin health indicator` : 'No active trade leverage used'}
            icon={marginLevel > 200 || margin === 0 ? ShieldCheck : ShieldAlert}
            variant={marginLevel > 200 || margin === 0 ? 'profit' : 'loss'}
            progressPercent={marginProgress}
            progressColor={marginColor}
          />

          {/* Free Margin Card */}
          <MetricCard
            id="metric-free-margin-card"
            label="Free Margin"
            value={formatCurrency(freeMargin, currency)}
            subtext={`Margin Used: ${formatCurrency(margin, currency)}`}
            icon={CreditCard}
            variant="default"
          />

          {/* Open Positions Card */}
          <MetricCard
            id="metric-open-positions-card"
            label="Active Positions"
            value={`${openPositions} Trade${openPositions === 1 ? '' : 's'}`}
            subtext="Currently running on MT5"
            icon={Layers}
            variant={openPositions > 0 ? 'cyan' : 'default'}
          />
        </div>

        {/* Strategy Recommendations & Semi-Auto Signal Approval */}
        <SignalsPanel
          signals={signals}
          onRefreshSignals={fetchSignals}
          isKillSwitchActive={isKillSwitchActive}
          isAutoPilotActive={autopilotStatus?.is_autopilot_active ?? false}
          onOrderExecuted={() => {
            fetchStatus();
            fetchSignals();
            fetchAutoPilotStatus();
          }}
        />

        {/* Manual Trading Workbench (Order Form + Live Positions Table) */}
        <div className="trading-workbench" id="trading-workbench">
          <OrderForm
            equity={equity}
            currency={currency}
            isKillSwitchActive={isKillSwitchActive}
            onOrderSubmitted={fetchStatus}
          />
          <PositionsTable
            positions={positions}
            currency={currency}
            onActionCompleted={fetchStatus}
          />
        </div>

        {/* Live Telemetry Diagnostics Box */}
        <section className="telemetry-section glass-panel" id="telemetry-diagnostics-section">
          <h3 className="section-title">
            <Radio size={18} style={{ color: 'var(--accent-cyan)' }} />
            Live Bridge Diagnostics
          </h3>

          <div className="telemetry-grid">
            <div className="telemetry-item">
              <div className="telemetry-item-label">Bridge Connectivity</div>
              <div className="telemetry-item-val" style={{ color: isConnected ? 'var(--accent-emerald)' : 'var(--accent-rose)' }}>
                {isConnected ? 'ACTIVE (Pinging)' : 'OFFLINE (Timed out)'}
              </div>
            </div>

            <div className="telemetry-item">
              <div className="telemetry-item-label">Heartbeat Latency</div>
              <div className="telemetry-item-val">
                {secondsSinceHeartbeat !== null ? `${secondsSinceHeartbeat}s ago` : 'No ping received'}
              </div>
            </div>

            <div className="telemetry-item">
              <div className="telemetry-item-label">Engine Security</div>
              <div className="telemetry-item-val" style={{ color: isKillSwitchActive ? 'var(--accent-rose)' : 'var(--accent-emerald)' }}>
                {isKillSwitchActive ? 'LOCKED (Kill Switch)' : 'NORMAL (Ready)'}
              </div>
            </div>

            <div className="telemetry-item">
              <div className="telemetry-item-label">Base Currency</div>
              <div className="telemetry-item-val">{currency}</div>
            </div>
          </div>
        </section>
      </main>

      {/* Emergency Kill Switch Modal */}
      <KillSwitchModal
        isOpen={isKillSwitchModalOpen}
        onClose={() => setIsKillSwitchModalOpen(false)}
        onConfirm={handleTriggerKillSwitch}
        openPositionsCount={openPositions}
        floatingPnl={floatingPnl}
        currency={currency}
      />
    </div>
  );
}
