import time
import uuid
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.services.bridge_service import bridge_service
from app.services.user_service import user_service
from app.core.security import create_access_token
from app.core.config import settings

client = TestClient(app)


def get_auth_context(username: str = settings.ADMIN_USERNAME):
    user = user_service.get_user(username)
    if not user:
        user = user_service.register(username, "StrongPassword123!")
    token = create_access_token(user["username"], user.get("token_version", 1))
    return {"Authorization": f"Bearer {token}"}, user["bridge_token"]


def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_root():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


def test_heartbeat_flow():
    bridge_service.reset_state()
    auth_headers, bridge_token = get_auth_context()

    # 1. Initially status should be disconnected
    res = client.get("/api/v1/bridge/status", headers=auth_headers)
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
        "bridge_token": bridge_token,
        "timestamp": int(time.time())
    }
    hb_res = client.post("/api/v1/bridge/heartbeat", json=payload)
    assert hb_res.status_code == 200
    data = hb_res.json()
    assert data["status"] == "ok"
    assert "server_time" in data
    assert isinstance(data["commands"], list)

    # 3. Check bridge status is now connected
    status_res = client.get("/api/v1/bridge/status", headers=auth_headers)
    assert status_res.status_code == 200
    status_data = status_res.json()
    assert status_data["is_connected"] is True
    assert status_data["terminal_connected"] is True
    assert status_data["metrics"]["account_number"] == 12345678
    assert status_data["metrics"]["balance"] == 10000.50
    assert status_data["metrics"]["equity"] == 10050.75
    assert status_data["metrics"]["floating_pnl"] == 50.25

    # 4. Simulate timeout on user session
    admin_key = settings.ADMIN_USERNAME.lower()
    with bridge_service._lock:
        bridge_service._sessions[admin_key].last_received_time = time.time() - 30.0

    status_timeout = client.get("/api/v1/bridge/status", headers=auth_headers)
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
    auth_headers, bridge_token = get_auth_context()

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
        "bridge_token": bridge_token,
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
    m_res = client.get("/api/v1/bridge/market", headers=auth_headers)
    assert m_res.status_code == 200
    quotes = m_res.json()
    assert len(quotes) == 2
    symbols = [q["symbol"] for q in quotes]
    assert "XAUUSD" in symbols
    assert "EURUSD" in symbols

    # 3. Check /api/v1/bridge/history
    h_res = client.get("/api/v1/bridge/history", headers=auth_headers)
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
    eq_res = client.get("/api/v1/bridge/equity-curve", headers=auth_headers)
    assert eq_res.status_code == 200
    eq_data = eq_res.json()
    assert eq_data["current_equity"] == 25150.0
    assert len(eq_data["points"]) >= 1


def test_initial_deposit_auto_detection_and_override():
    bridge_service.reset_state()
    auth_headers, bridge_token = get_auth_context()

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
        "bridge_token": bridge_token,
        "timestamp": int(time.time())
    }
    hb_res = client.post("/api/v1/bridge/heartbeat", json=hb_payload)
    assert hb_res.status_code == 200

    # 2. Check status P/L calculations against auto-detected initial deposit
    status_res = client.get("/api/v1/bridge/status", headers=auth_headers)
    assert status_res.status_code == 200
    status_data = status_res.json()
    assert status_data["initial_deposit"] == 10000.0
    assert status_data["is_deposit_overridden"] is False
    assert status_data["settled_pnl"] == 500.0
    assert status_data["settled_pnl_percent"] == 5.0
    assert status_data["all_time_pnl"] == 750.0
    assert status_data["all_time_pnl_percent"] == 7.5

    # 3. Check /api/v1/bridge/initial-deposit endpoint
    init_res = client.get("/api/v1/bridge/initial-deposit", headers=auth_headers)
    assert init_res.status_code == 200
    assert init_res.json()["initial_deposit"] == 10000.0
    assert init_res.json()["source"] == "mt5"

    # 4. Trader manually overrides initial deposit to $8,000
    override_res = client.post(
        "/api/v1/bridge/initial-deposit",
        json={"initial_deposit": 8000.0},
        headers=auth_headers
    )
    assert override_res.status_code == 200
    ov_data = override_res.json()
    assert ov_data["initial_deposit"] == 8000.0
    assert ov_data["is_overridden"] is True
    assert ov_data["settled_pnl"] == 2500.0
    assert ov_data["all_time_pnl"] == 2750.0

    # 5. Check bridge status reflects override
    status_res2 = client.get("/api/v1/bridge/status", headers=auth_headers)
    assert status_res2.json()["initial_deposit"] == 8000.0
    assert status_res2.json()["is_deposit_overridden"] is True

    # 6. Reset override back to MT5 auto-detect by passing null
    reset_res = client.post(
        "/api/v1/bridge/initial-deposit",
        json={"initial_deposit": None},
        headers=auth_headers
    )
    assert reset_res.status_code == 200
    assert reset_res.json()["initial_deposit"] == 10000.0
    assert reset_res.json()["is_overridden"] is False


def test_reconstructed_equity_curve_filters():
    bridge_service.reset_state()
    auth_headers, bridge_token = get_auth_context()
    now = int(time.time())

    # Send heartbeat with closed trades across days
    hb_payload = {
        "account_number": 998877,
        "server": "Demo-Server",
        "currency": "USD",
        "balance": 1200.0,
        "equity": 1250.0,
        "initial_deposit": 1000.0,
        "bridge_token": bridge_token,
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
                "close_time": now - 1800,
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
                "close_time": now - (2 * 86400),
                "magic": 778899
            }
        ],
        "timestamp": now
    }
    client.post("/api/v1/bridge/heartbeat", json=hb_payload)

    # 1. Day filter
    curve_day = client.get("/api/v1/bridge/equity-curve?range=Day", headers=auth_headers).json()
    assert curve_day["current_equity"] == 1250.0
    assert curve_day["initial_deposit"] == 1000.0
    assert curve_day["all_time_pnl"] == 250.0
    assert len(curve_day["points"]) >= 2

    # 2. Week filter
    curve_week = client.get("/api/v1/bridge/equity-curve?range=Week", headers=auth_headers).json()
    assert curve_week["current_equity"] == 1250.0
    assert len(curve_week["points"]) >= 3

    # 3. Month filter
    curve_month = client.get("/api/v1/bridge/equity-curve?range=Month", headers=auth_headers).json()
    assert curve_month["current_equity"] == 1250.0
    assert len(curve_month["points"]) >= 3


def test_user_isolated_mt5_telemetry():
    """Verify that User Alice and User Bob have completely isolated MT5 sessions."""
    bridge_service.reset_state()

    alice = f"alice_{uuid.uuid4().hex[:6]}"
    bob = f"bob_{uuid.uuid4().hex[:6]}"

    # Register Alice & Bob
    alice_data = user_service.register(alice, "AliceSecure123!")
    bob_data = user_service.register(bob, "BobSecure123!")

    alice_token = create_access_token(alice_data["username"], alice_data["token_version"])
    bob_token = create_access_token(bob_data["username"], bob_data["token_version"])

    alice_headers = {"Authorization": f"Bearer {alice_token}"}
    bob_headers = {"Authorization": f"Bearer {bob_token}"}

    # 1. Heartbeat without any token must fail with 401
    unauth_res = client.post("/api/v1/bridge/heartbeat", json={
        "account_number": 99999,
        "server": "Hacker-Server",
        "balance": 100.0,
        "equity": 100.0,
        "timestamp": int(time.time())
    })
    assert unauth_res.status_code == 401

    # 2. Heartbeat with invalid token must fail with 401
    bad_res = client.post("/api/v1/bridge/heartbeat", json={
        "account_number": 99999,
        "server": "Hacker-Server",
        "balance": 100.0,
        "equity": 100.0,
        "bridge_token": "tg_live_invalid_token_123456",
        "timestamp": int(time.time())
    })
    assert bad_res.status_code == 401

    # 3. Alice connects her MT5 terminal (Account #11111, Balance $5,000)
    now = int(time.time())
    alice_payload = {
        "account_number": 11111,
        "server": "Exness-Real-Alice",
        "currency": "USD",
        "balance": 5000.0,
        "equity": 5050.0,
        "margin": 100.0,
        "free_margin": 4950.0,
        "margin_level": 5050.0,
        "floating_pnl": 50.0,
        "terminal_connected": True,
        "open_positions": 1,
        "positions": [
            {
                "ticket": 5001,
                "symbol": "XAUUSD",
                "type": "BUY",
                "volume": 0.05,
                "open_price": 2700.0,
                "current_price": 2710.0,
                "sl": 2690.0,
                "tp": 2720.0,
                "pnl": 50.0,
                "open_time": now - 600,
                "magic": 778899
            }
        ],
        "bridge_token": alice_data["bridge_token"],
        "timestamp": now
    }
    alice_hb = client.post("/api/v1/bridge/heartbeat", json=alice_payload)
    assert alice_hb.status_code == 200

    # 4. Bob connects his MT5 terminal via header X-Bridge-Token (Account #22222, Balance $25,000)
    bob_payload = {
        "account_number": 22222,
        "server": "ICMarkets-Live-Bob",
        "currency": "USD",
        "balance": 25000.0,
        "equity": 25300.0,
        "margin": 200.0,
        "free_margin": 25100.0,
        "margin_level": 12650.0,
        "floating_pnl": 300.0,
        "terminal_connected": True,
        "open_positions": 1,
        "positions": [
            {
                "ticket": 6001,
                "symbol": "EURUSD",
                "type": "SELL",
                "volume": 0.50,
                "open_price": 1.0850,
                "current_price": 1.0820,
                "sl": 1.0890,
                "tp": 1.0780,
                "pnl": 300.0,
                "open_time": now - 300,
                "magic": 778899
            }
        ],
        "timestamp": now
    }
    bob_hb = client.post(
        "/api/v1/bridge/heartbeat",
        headers={"X-Bridge-Token": bob_data["bridge_token"]},
        json=bob_payload
    )
    assert bob_hb.status_code == 200

    # 5. Alice checks her status -> sees ONLY her MT5 account #11111
    alice_status = client.get("/api/v1/bridge/status", headers=alice_headers).json()
    assert alice_status["is_connected"] is True
    assert alice_status["metrics"]["account_number"] == 11111
    assert alice_status["metrics"]["balance"] == 5000.0
    assert alice_status["metrics"]["equity"] == 5050.0
    assert len(alice_status["positions"]) == 1
    assert alice_status["positions"][0]["ticket"] == 5001

    # 6. Bob checks his status -> sees ONLY his MT5 account #22222
    bob_status = client.get("/api/v1/bridge/status", headers=bob_headers).json()
    assert bob_status["is_connected"] is True
    assert bob_status["metrics"]["account_number"] == 22222
    assert bob_status["metrics"]["balance"] == 25000.0
    assert bob_status["metrics"]["equity"] == 25300.0
    assert len(bob_status["positions"]) == 1
    assert bob_status["positions"][0]["ticket"] == 6001

    # 7. Check positions endpoint isolation
    alice_pos = client.get("/api/v1/bridge/positions", headers=alice_headers).json()
    bob_pos = client.get("/api/v1/bridge/positions", headers=bob_headers).json()
    assert len(alice_pos) == 1 and alice_pos[0]["ticket"] == 5001
    assert len(bob_pos) == 1 and bob_pos[0]["ticket"] == 6001
