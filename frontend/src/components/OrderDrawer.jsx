import React, { useEffect } from 'react';
import { X, PlusCircle } from 'lucide-react';
import OrderForm from './OrderForm';

export default function OrderDrawer({
  isOpen,
  onClose,
  equity = 10000,
  currency = 'USD',
  isKillSwitchActive = false,
  marketQuotes = [],
  initialSymbol = 'EURUSD',
  onOrderSubmitted
}) {
  useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.key === 'Escape' && isOpen) {
        onClose();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  return (
    <div
      className="order-drawer-overlay animate-fade-in"
      id="order-drawer-backdrop"
      style={{
        position: 'fixed',
        inset: 0,
        background: 'rgba(5, 10, 14, 0.75)',
        backdropFilter: 'blur(8px)',
        WebkitBackdropFilter: 'blur(8px)',
        zIndex: 60,
        display: 'flex',
        justifyContent: 'flex-end',
        alignItems: 'stretch'
      }}
      onClick={(e) => {
        if (e.target.id === 'order-drawer-backdrop') onClose();
      }}
    >
      <div
        className="order-drawer-panel"
        style={{
          width: '460px',
          maxWidth: '100vw',
          height: '100%',
          background: '#0d171e',
          borderLeft: '1px solid var(--line)',
          display: 'flex',
          flexDirection: 'column',
          boxShadow: '-10px 0 35px rgba(0, 0, 0, 0.6)',
          animation: 'drawerSlide 0.25s cubic-bezier(0.16, 1, 0.3, 1)'
        }}
      >
        {/* Drawer Header */}
        <div
          style={{
            padding: '16px 20px',
            borderBottom: '1px solid var(--line)',
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            background: 'rgba(13, 23, 30, 0.95)'
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <PlusCircle size={18} style={{ color: 'var(--g)' }} />
            <div>
              <h2 style={{ fontSize: '15px', fontWeight: 800, margin: 0 }}>New Trade Execution</h2>
              <span className="tiny" style={{ color: 'var(--muted)' }}>Direct MT5 Terminal Market Order</span>
            </div>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="btn ghost"
            style={{ padding: '6px 8px', borderRadius: '8px' }}
            id="order-drawer-close-btn"
          >
            <X size={16} />
          </button>
        </div>

        {/* Drawer Content */}
        <div
          style={{
            flex: 1,
            overflowY: 'auto',
            padding: '18px 20px'
          }}
        >
          <OrderForm
            equity={equity}
            currency={currency}
            isKillSwitchActive={isKillSwitchActive}
            marketQuotes={marketQuotes}
            initialSymbol={initialSymbol}
            onOrderSubmitted={() => {
              if (onOrderSubmitted) onOrderSubmitted();
              onClose();
            }}
          />
        </div>
      </div>
      <style>{`
        @keyframes drawerSlide {
          from { transform: translateX(100%); }
          to { transform: translateX(0); }
        }
        @media (max-width: 600px) {
          .order-drawer-panel {
            width: 100vw !important;
          }
        }
      `}</style>
    </div>
  );
}
