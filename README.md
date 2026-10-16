# Algorithmic Trading Robot System (Web-to-MT5 Bridge)

Sistem robot trading otomatis dan semi-otomatis dengan arsitektur decoupled (Otak Robot di Web/FastAPI, Eksekutor di MT5) yang dideploy di homeserver Ubuntu via Docker dan Ansible.

## 📁 Struktur Repositori

```text
robot/
├── .scratch/robot-trading/issues/  # Tracer-bullet tickets (to-tickets)
├── docker/
│   ├── mt5/                        # Dockerfile & konfigurasi Wine + noVNC MT5
│   └── docker-compose.yml          # Orkestrasi MT5, Backend, Frontend
├── backend/                        # Python FastAPI Backend (Otak & Bridge)
│   ├── app/
│   │   ├── api/                    # REST API routes
│   │   ├── core/                   # Security, auth, config
│   │   ├── services/               # Strategy engine, MT5 bridge, risk manager
│   │   └── main.py
├── frontend/                       # Web Dashboard (Vite React + Tailwind)
├── mt5-ea/                         # Expert Advisor MQL5 (BridgeEA.mq5)
├── .env.example                    # Template environment variables
└── README.md
```

## 🚀 Panduan Tiket & Roadmap

Tiket pengerjaan vertikal (tracer-bullet) tersimpan di folder `.scratch/robot-trading/issues/`:

1. `01-mt5-docker-sandbox.md` (Running MT5 di Docker Wine + noVNC)
2. `02-ea-bridge-and-heartbeat.md` (MQL5 EA Bridge & Ping-Pong backend)
3. `03-auth-and-connection-dashboard.md` (Web login & real-time metric cards)
4. `04-web-manual-trade-execution.md` (Klik order di web -> eksekusi MT5)
5. `05-risk-calculator-and-emergency-kill-switch.md` (Kalkulasi lot dinamis & Panic button)
6. `06-strategy-engine-and-semi-auto-approval.md` (Analisis indikator & approval sinyal)
7. `07-autonomous-auto-pilot-and-drawdown-guard.md` (Auto-pilot & proteksi max drawdown harian)
8. `08-telegram-alerts-and-cloudflare-tunnel.md` (Notifikasi Telegram & remote access HP)
