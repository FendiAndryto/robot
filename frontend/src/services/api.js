// API service with dynamic base URL and JWT token handling
// Reads from Vite environment variable or falls back to relative path for reverse proxy
const API_BASE = import.meta.env.VITE_API_URL ? import.meta.env.VITE_API_URL.replace(/\/$/, '') : '';
const TOKEN_KEY = 'robot_trading_jwt_token';

export const getToken = () => localStorage.getItem(TOKEN_KEY);
export const setToken = (token) => localStorage.setItem(TOKEN_KEY, token);
export const clearToken = () => localStorage.removeItem(TOKEN_KEY);

const getAuthHeaders = () => {
  const token = getToken();
  return {
    'Content-Type': 'application/json',
    ...(token ? { Authorization: `Bearer ${token}` } : {})
  };
};

export const api = {
  // Authentication
  async login(username, password) {
    const res = await fetch(`${API_BASE}/api/v1/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, password })
    });
    
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: 'Login failed' }));
      throw new Error(err.detail || 'Authentication failed');
    }
    
    const data = await res.json();
    setToken(data.access_token);
    return data;
  },

  async getMe() {
    const res = await fetch(`${API_BASE}/api/v1/auth/me`, {
      method: 'GET',
      headers: getAuthHeaders()
    });
    
    if (!res.ok) {
      if (res.status === 401) {
        clearToken();
      }
      throw new Error('Unauthorized');
    }
    
    return res.json();
  },

  async logout() {
    try {
      await fetch(`${API_BASE}/api/v1/auth/logout`, {
        method: 'POST',
        headers: getAuthHeaders()
      });
    } catch {
      // Ignore network errors on logout
    } finally {
      clearToken();
    }
  },

  // Bridge Status & Telemetry
  async getBridgeStatus() {
    const res = await fetch(`${API_BASE}/api/v1/bridge/status`, {
      method: 'GET',
      headers: getAuthHeaders()
    });
    
    if (!res.ok) {
      throw new Error(`Failed to fetch bridge telemetry (HTTP ${res.status})`);
    }
    
    return res.json();
  },

  // Trade Execution
  async submitOrder(orderData) {
    const res = await fetch(`${API_BASE}/api/v1/bridge/order`, {
      method: 'POST',
      headers: getAuthHeaders(),
      body: JSON.stringify(orderData)
    });

    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: 'Order failed' }));
      throw new Error(err.detail || 'Order execution failed');
    }

    return res.json();
  },

  async getPositions() {
    const res = await fetch(`${API_BASE}/api/v1/bridge/positions`, {
      method: 'GET',
      headers: getAuthHeaders()
    });

    if (!res.ok) {
      throw new Error('Failed to retrieve open positions');
    }

    return res.json();
  },

  async closePosition(ticket) {
    return this.submitOrder({
      action: 'CLOSE',
      ticket: Number(ticket)
    });
  },

  async closeAllPositions() {
    return this.submitOrder({
      action: 'CLOSE_ALL'
    });
  },

  // Risk Management & Emergency Kill Switch
  async getRiskStatus() {
    const res = await fetch(`${API_BASE}/api/v1/risk/status`, {
      method: 'GET',
      headers: getAuthHeaders()
    });
    if (!res.ok) {
      throw new Error('Failed to retrieve risk configuration');
    }
    return res.json();
  },

  async calculateLot(params) {
    const res = await fetch(`${API_BASE}/api/v1/risk/calculate-lot`, {
      method: 'POST',
      headers: getAuthHeaders(),
      body: JSON.stringify(params)
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: 'Lot calculation failed' }));
      throw new Error(err.detail || 'Position sizing calculation failed');
    }
    return res.json();
  },

  async triggerKillSwitch(reason = 'Manual emergency kill switch triggered') {
    const res = await fetch(`${API_BASE}/api/v1/risk/kill-switch`, {
      method: 'POST',
      headers: getAuthHeaders(),
      body: JSON.stringify({ reason })
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: 'Failed to engage Kill Switch' }));
      throw new Error(err.detail || 'Emergency Kill Switch activation failed');
    }
    return res.json();
  },

  async disarmKillSwitch() {
    const res = await fetch(`${API_BASE}/api/v1/risk/unlock`, {
      method: 'POST',
      headers: getAuthHeaders()
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: 'Failed to disarm Kill Switch' }));
      throw new Error(err.detail || 'Failed to unlock trading engine');
    }
    return res.json();
  }
};
