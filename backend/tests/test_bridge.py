import time
from fastapi.testclient import TestClient
from app.main import app
from app.services.bridge_service import bridge_service
from app.core.security import create_access_token

client = TestClient(app)



def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_root():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


def test_heartbeat_flow():
    # 1. Initially status should be disconnected
    res = client.get("/api/v1/bridge/status")
    assert res.status_code == 200
    assert res.json()["is_connected"] is False

    # 2. Post a valid heartbeat
    payload = {
        "account_number": 12345678,
        "server": "Demo-Server",
        "currency": "USD",
        "balance": 10000.50,
        "equity": 10050.75,
        "margin": 200.0,
        "free_margin": 9850.75,
        "margin_level": 5025.37,
        "floating_pnl": 50.25,
        "terminal_connected": True,
        "open_positions": 1,
        "timestamp": int(time.time())
    }
    hb_res = client.post("/api/v1/bridge/heartbeat", json=payload)
    assert hb_res.status_code == 200
    data = hb_res.json()
    assert data["status"] == "ok"
    assert "server_time" in data
    assert isinstance(data["commands"], list)

    # 3. Check bridge status is now connected
    status_res = client.get("/api/v1/bridge/status")
    assert status_res.status_code == 200
    status_data = status_res.json()
    assert status_data["is_connected"] is True
    assert status_data["terminal_connected"] is True
    assert status_data["metrics"]["account_number"] == 12345678
    assert status_data["metrics"]["balance"] == 10000.50
    assert status_data["metrics"]["equity"] == 10050.75
    assert status_data["metrics"]["floating_pnl"] == 50.25

    # 4. Simulate timeout: terminal_connected should become False when disconnected
    with bridge_service._lock:
        bridge_service._last_received_time = time.time() - 30.0

    status_timeout = client.get("/api/v1/bridge/status")
    assert status_timeout.status_code == 200
    data_timeout = status_timeout.json()
    assert data_timeout["is_connected"] is False
    assert data_timeout["terminal_connected"] is False
    assert data_timeout["seconds_since_last_heartbeat"] >= 30.0


def test_bridge_ping():
    response = client.get("/api/v1/bridge/ping")
    assert response.status_code == 200
    assert response.json()["status"] == "pong"
    assert "timestamp" in response.json()


def test_invalid_heartbeat_payload():
    # Missing required fields should return 422 Unprocessable Entity
    invalid_payload = {"account_number": 12345}
    response = client.post("/api/v1/bridge/heartbeat", json=invalid_payload)
    assert response.status_code == 422


def test_cors_settings():
    from app.core.config import settings
    origins = settings.cors_origins
    assert "http://localhost:5173" in origins
    assert "http://127.0.0.1:5173" in origins
    assert "http://localhost:3000" in origins


def test_market_and_history_and_equity_curve():
    bridge_service.reset_state()

    # 1. Heartbeat with real market quotes and closed trades
    now = int(time.time())
    payload = {
        "account_number": 99887766,
        "server": "Exness-Real",
        "currency": "USD",
        "balance": 25000.0,
        "equity": 25150.0,
        "margin": 500.0,
        "free_margin": 24650.0,
        "margin_level": 5030.0,
        "floating_pnl": 150.0,
        "terminal_connected": True,
        "open_positions": 0,
        "market_quotes": [
            {
                "symbol": "XAUUSD",
                "bid": 2725.50,
                "ask": 2725.80,
                "spread": 30,
                "digits": 2,
                "daily_change_pct": 0.45,
                "high": 2732.10,
                "low": 2718.00
            },
            {
                "symbol": "EURUSD",
                "bid": 1.08520,
                "ask": 1.08535,
                "spread": 15,
                "digits": 5,
                "daily_change_pct": -0.12,
                "high": 1.08700,
                "low": 1.08300
            }
        ],
        "closed_trades": [
            {
                "ticket": 1001,
                "symbol": "XAUUSD",
                "type": "BUY",
                "volume": 0.05,
                "open_price": 2715.00,
                "close_price": 2725.00,
                "profit": 50.00,
                "open_time": now - 3600,
                "close_time": now - 1800,
                "magic": 778899
            },
            {
                "ticket": 1002,
                "symbol": "EURUSD",
                "type": "SELL",
                "volume": 0.10,
                "open_price": 1.08600,
                "close_price": 1.08800,
                "profit": -20.00,
                "open_time": now - 7200,
                "close_time": now - 3600,
                "magic": 0
            }
        ],
        "chart_symbol": "XAUUSD",
        "timestamp": now
    }

    res = client.post("/api/v1/bridge/heartbeat", json=payload)
    assert res.status_code == 200

    # 2. Check /api/v1/bridge/market
    m_res = client.get("/api/v1/bridge/market")
    assert m_res.status_code == 200
    quotes = m_res.json()
    assert len(quotes) == 2
    symbols = [q["symbol"] for q in quotes]
    assert "XAUUSD" in symbols
    assert "EURUSD" in symbols

    # 3. Check /api/v1/bridge/history
    h_res = client.get("/api/v1/bridge/history")
    assert h_res.status_code == 200
    hist = h_res.json()
    assert hist["total_trades"] == 2
    assert hist["winning_trades"] == 1
    assert hist["losing_trades"] == 1
    assert hist["net_pnl"] == 30.00
    assert hist["win_rate"] == 50.0
    assert hist["gross_profit"] == 50.00
    assert hist["gross_loss"] == 20.00
    assert hist["profit_factor"] == 2.5

    # 4. Check /api/v1/bridge/equity-curve
    eq_res = client.get("/api/v1/bridge/equity-curve")
    assert eq_res.status_code == 200
    eq_data = eq_res.json()
    assert eq_data["current_equity"] == 25150.0
    assert len(eq_data["points"]) >= 1


def test_initial_deposit_auto_detection_and_override():
    # 1. Post heartbeat with initial_deposit from MT5 deal history
    hb_payload = {
        "account_number": 112233,
        "server": "Demo-Server",
        "currency": "USD",
        "balance": 10500.0,
        "equity": 10750.0,
        "initial_deposit": 10000.0,
        "margin": 100.0,
        "free_margin": 10650.0,
        "margin_level": 10750.0,
        "floating_pnl": 250.0,
        "terminal_connected": True,
        "open_positions": 1,
        "positions": [],
        "timestamp": int(time.time())
    }
    hb_res = client.post("/api/v1/bridge/heartbeat", json=hb_payload)
    assert hb_res.status_code == 200

    # 2. Check status P/L calculations against auto-detected initial deposit
    status_res = client.get("/api/v1/bridge/status")
    assert status_res.status_code == 200
    status_data = status_res.json()
    assert status_data["initial_deposit"] == 10000.0
    assert status_data["is_deposit_overridden"] is False
    assert status_data["settled_pnl"] == 500.0 # 10500 - 10000
    assert status_data["settled_pnl_percent"] == 5.0 # 5%
    assert status_data["all_time_pnl"] == 750.0 # 10750 - 10000
    assert status_data["all_time_pnl_percent"] == 7.5 # 7.5%

    # 3. Check /api/v1/bridge/initial-deposit endpoint
    init_res = client.get("/api/v1/bridge/initial-deposit")
    assert init_res.status_code == 200
    assert init_res.json()["initial_deposit"] == 10000.0
    assert init_res.json()["source"] == "mt5"

    # 4. Trader manually overrides initial deposit to $8,000
    auth_headers = {"Authorization": f"Bearer {create_access_token('admin')}"}
    override_res = client.post(
        "/api/v1/bridge/initial-deposit",
        json={"initial_deposit": 8000.0},
        headers=auth_headers
    )
    assert override_res.status_code == 200
    ov_data = override_res.json()
    assert ov_data["initial_deposit"] == 8000.0
    assert ov_data["is_overridden"] is True
    assert ov_data["settled_pnl"] == 2500.0 # 10500 - 8000
    assert ov_data["all_time_pnl"] == 2750.0 # 10750 - 8000

    # 5. Check bridge status reflects override
    status_res2 = client.get("/api/v1/bridge/status")
    assert status_res2.json()["initial_deposit"] == 8000.0
    assert status_res2.json()["is_deposit_overridden"] is True

    # 6. Reset override back to MT5 auto-detect by passing null/0
    reset_res = client.post(
        "/api/v1/bridge/initial-deposit",
        json={"initial_deposit": None},
        headers=auth_headers
    )
    assert reset_res.status_code == 200
    assert reset_res.json()["initial_deposit"] == 10000.0
    assert reset_res.json()["is_overridden"] is False


def test_reconstructed_equity_curve_filters():
    now = int(time.time())
    # Send heartbeat with closed trades across days
    hb_payload = {
        "account_number": 998877,
        "server": "Demo-Server",
        "currency": "USD",
        "balance": 1200.0,
        "equity": 1250.0,
        "initial_deposit": 1000.0,
        "closed_trades": [
            {
                "ticket": 101,
                "symbol": "EURUSD",
                "type": "BUY",
                "volume": 0.1,
                "open_price": 1.0800,
                "close_price": 1.0850,
                "profit": 50.0,
                "open_time": now - 3600,
                "close_time": now - 1800, # Today
                "magic": 0
            },
            {
                "ticket": 102,
                "symbol": "XAUUSD",
                "type": "SELL",
                "volume": 0.05,
                "open_price": 2700.0,
                "close_price": 2690.0,
                "profit": 150.0,
                "open_time": now - (3 * 86400),
                "close_time": now - (2 * 86400), # 2 days ago
                "magic": 778899
            }
        ],
        "timestamp": now
    }
    client.post("/api/v1/bridge/heartbeat", json=hb_payload)

    # 1. Day filter (only ticket 101 should be inside today)
    curve_day = client.get("/api/v1/bridge/equity-curve?range=Day").json()
    assert curve_day["current_equity"] == 1250.0
    assert curve_day["initial_deposit"] == 1000.0
    assert curve_day["all_time_pnl"] == 250.0 # 1250 - 1000
    assert len(curve_day["points"]) >= 2

    # 2. Week filter (both ticket 101 and 102 inside 7 days)
    curve_week = client.get("/api/v1/bridge/equity-curve?range=Week").json()
    assert curve_week["current_equity"] == 1250.0
    # Both trades are in the week
    assert len(curve_week["points"]) >= 3

    # 3. Month filter
    curve_month = client.get("/api/v1/bridge/equity-curve?range=Month").json()
    assert curve_month["current_equity"] == 1250.0
    assert len(curve_month["points"]) >= 3



