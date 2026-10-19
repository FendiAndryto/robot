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

  // Bridge Status & Account Telemetry
  async getBridgeStatus() {
    const res = await fetch(`${API_BASE}/api/v1/bridge/status`, {
      method: 'GET',
      headers: getAuthHeaders()
    });
    
    if (!res.ok) {
      throw new Error(`Failed to fetch bridge telemetry (HTTP ${res.status})`);
    }
    
    return res.json();
  }
};
