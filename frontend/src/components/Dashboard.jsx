import React, { useState, useEffect, useRef } from 'react';
import TradeGearHeader from './TradeGearHeader';
import TradeGearBottomNav from './TradeGearBottomNav';
import HomeTab from './HomeTab';
import JournalTab from './JournalTab';
import MarketTab from './MarketTab';
import ComingSoonTab from './ComingSoonTab';
import ProfileTab from './ProfileTab';
import FloatingSignalWidget from './FloatingSignalWidget';
import OrderDrawer from './OrderDrawer';
import KillSwitchModal from './KillSwitchModal';
import RiskBanner from './RiskBanner';
import DrawdownBanner from './DrawdownBanner';
import Mt5ConnectModal from './Mt5ConnectModal';
import { api } from '../services/api';

export default function Dashboard({ user, onLogout }) {
  const [activeTab, setActiveTab] = useState('home');
  const [bridgeStatus, setBridgeStatus] = useState(null);
  const [pollInterval, setPollInterval] = useState(1000);
  const [signals, setSignals] = useState([]);
  const [autopilotStatus, setAutopilotStatus] = useState(null);

  // Modals & Drawers state
  const [isOrderDrawerOpen, setIsOrderDrawerOpen] = useState(false);
  const [isKillSwitchModalOpen, setIsKillSwitchModalOpen] = useState(false);
  const [isMt5ModalOpen, setIsMt5ModalOpen] = useState(false);
  const [isResettingDrawdown, setIsResettingDrawdown] = useState(false);
  const [isUnlockingEngine, setIsUnlockingEngine] = useState(false);
  const [isTestingTelegram, setIsTestingTelegram] = useState(false);
  const [telegramStatusMsg, setTelegramStatusMsg] = useState(null);
  const timerRef = useRef(null);

  const fetchSignals = async () => {
    try {
      const data = await api.getSignals();
      setSignals(data || []);
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
    } catch {
      setBridgeStatus((prev) => ({
        ...prev,
        is_connected: false,
        terminal_connected: false,
        seconds_since_last_heartbeat: null
      }));
    }
  };

  useEffect(() => {
    let isMounted = true;
    const runPoll = async () => {
      if (!isMounted) return;
      try {
        await Promise.allSettled([fetchStatus(), fetchSignals(), fetchAutoPilotStatus()]);
      } catch {
        // Polling errors handled within individual fetchers
      }
    };

    runPoll();
    timerRef.current = setInterval(runPoll, pollInterval);

    return () => {
      isMounted = false;
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

  const handleTestTelegram = async () => {
    setIsTestingTelegram(true);
    setTelegramStatusMsg(null);
    try {
      const res = await api.sendTelegramTestAlert();
      if (res.delivered) {
        setTelegramStatusMsg({ type: 'success', text: 'Telegram alert sent successfully!' });
      } else {
        setTelegramStatusMsg({ type: 'warning', text: 'Telegram bot not configured or disabled.' });
      }
    } catch (err) {
      setTelegramStatusMsg({ type: 'error', text: err.message || 'Telegram test failed.' });
    } finally {
      setIsTestingTelegram(false);
    }
  };

  const metrics = bridgeStatus?.metrics || {};
  const isConnected = bridgeStatus?.is_connected || false;
  const isKillSwitchActive = bridgeStatus?.is_kill_switch_active || false;
  const killSwitchReason = bridgeStatus?.kill_switch_reason;
  const killSwitchTime = bridgeStatus?.kill_switch_time;
  const secondsSinceHeartbeat = bridgeStatus?.seconds_since_last_heartbeat ?? null;
  const equity = metrics.equity ?? 10000;
  const currency = metrics.currency || 'USD';
  const openPositions = metrics.open_positions ?? 0;
  const floatingPnl = metrics.floating_pnl ?? 0;

  return (
    <div className="app-shell" id="tradegear-dashboard">
      {/* Sticky Header with Logo, Navigation Tabs & Status */}
      <TradeGearHeader
        activeTab={activeTab}
        onSelectTab={setActiveTab}
        isConnected={isConnected}
        latency={secondsSinceHeartbeat}
        onOpenMt5Modal={() => setIsMt5ModalOpen(true)}
        onOpenNewTrade={() => setIsOrderDrawerOpen(true)}
      />

      {/* Main Container */}
      <main className="app-main">
        {/* Global Emergency Kill Switch Warning Banner */}
        {isKillSwitchActive && (
          <RiskBanner
            reason={killSwitchReason}
            triggeredAt={killSwitchTime}
            onUnlock={handleUnlockEngine}
            isUnlocking={isUnlockingEngine}
          />
        )}

        {/* Global Daily Drawdown Lockout Warning Banner */}
        {autopilotStatus?.is_drawdown_lockout_active && (
          <DrawdownBanner
            reason={autopilotStatus.drawdown_lockout_reason}
            lockoutTime={autopilotStatus.lockout_time}
            onResetGuard={handleResetDrawdown}
            isResetting={isResettingDrawdown}
          />
        )}

        {/* Tab 1: Home Command Center */}
        <div className={`page-container ${activeTab === 'home' ? 'active' : ''}`} id="tab-home">
          <HomeTab
            bridgeStatus={bridgeStatus}
            autopilotStatus={autopilotStatus}
            onOpenNewTrade={() => setIsOrderDrawerOpen(true)}
            onNavigateJournal={() => setActiveTab('journal')}
            onNavigateAI={() => setActiveTab('ai')}
            onNavigateMarket={() => setActiveTab('market')}
            onRefresh={fetchStatus}
          />
        </div>

        {/* Tab 2: Trading Journal */}
        <div className={`page-container ${activeTab === 'journal' ? 'active' : ''}`} id="tab-journal">
          <JournalTab onNavigateAI={() => setActiveTab('ai')} />
        </div>

        {/* Tab 3: Market Overview */}
        <div className={`page-container ${activeTab === 'market' ? 'active' : ''}`} id="tab-market">
          <MarketTab
            bridgeStatus={bridgeStatus}
            onOpenOrder={(sym) => {
              setIsOrderDrawerOpen(true);
            }}
          />
        </div>

        {/* Tab 4: AI Assistant (Coming Soon) */}
        <div className={`page-container ${activeTab === 'ai' ? 'active' : ''}`} id="tab-ai">
          <ComingSoonTab type="ai" onBackToHome={() => setActiveTab('home')} />
        </div>

        {/* Tab 5: Replay & Backtest (Coming Soon) */}
        <div className={`page-container ${activeTab === 'replay' ? 'active' : ''}`} id="tab-replay">
          <ComingSoonTab type="replay" onBackToHome={() => setActiveTab('home')} />
        </div>

        {/* Tab 6: Profile & Settings */}
        <div className={`page-container ${activeTab === 'profile' ? 'active' : ''}`} id="tab-profile">
          <ProfileTab
            user={user}
            onLogout={onLogout}
            bridgeStatus={bridgeStatus}
            autopilotStatus={autopilotStatus}
            pollInterval={pollInterval}
            onPollIntervalChange={setPollInterval}
            onOpenMt5Modal={() => setIsMt5ModalOpen(true)}
            onTriggerKillSwitch={() => setIsKillSwitchModalOpen(true)}
            onUnlockEngine={handleUnlockEngine}
            isUnlockingEngine={isUnlockingEngine}
            onResetDrawdown={handleResetDrawdown}
            isResettingDrawdown={isResettingDrawdown}
            onTestTelegram={handleTestTelegram}
            isTestingTelegram={isTestingTelegram}
            telegramStatusMsg={telegramStatusMsg}
          />
        </div>
      </main>

      {/* Mobile Fixed Bottom Navigation Bar */}
      <TradeGearBottomNav activeTab={activeTab} onSelectTab={setActiveTab} />

      {/* Floating Strategy Recommendation Signals Widget */}
      <FloatingSignalWidget
        signals={signals}
        onRefreshSignals={fetchSignals}
        isKillSwitchActive={isKillSwitchActive}
        isAutoPilotActive={autopilotStatus?.is_autopilot_active ?? false}
        onToggleAutoPilot={handleToggleAutoPilot}
        onOrderExecuted={() => {
          fetchStatus();
          fetchSignals();
          fetchAutoPilotStatus();
        }}
      />

      {/* Slide-over Manual Order Execution Drawer */}
      <OrderDrawer
        isOpen={isOrderDrawerOpen}
        onClose={() => setIsOrderDrawerOpen(false)}
        equity={equity}
        currency={currency}
        isKillSwitchActive={isKillSwitchActive}
        onOrderSubmitted={() => {
          fetchStatus();
          fetchSignals();
        }}
      />

      {/* Emergency Kill Switch Confirmation Modal */}
      <KillSwitchModal
        isOpen={isKillSwitchModalOpen}
        onClose={() => setIsKillSwitchModalOpen(false)}
        onConfirm={handleTriggerKillSwitch}
        openPositionsCount={openPositions}
        floatingPnl={floatingPnl}
        currency={currency}
      />

      {/* MT5 Web-GUI Connect & Broker Screen Modal */}
      <Mt5ConnectModal
        isOpen={isMt5ModalOpen}
        onClose={() => setIsMt5ModalOpen(false)}
        isConnected={isConnected}
        accountNumber={metrics.account_number}
        onCheckStatus={fetchStatus}
      />
    </div>
  );
}
