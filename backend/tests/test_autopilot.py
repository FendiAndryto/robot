import time
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.services.bridge_service import bridge_service
from app.services.strategy_engine import strategy_engine
from app.services.autopilot_service import autopilot_service
from app.core.security import create_access_token

client = TestClient(app)


from app.core.config import settings

@pytest.fixture(autouse=True)
def clean_state():
    old_session_filter = settings.STRATEGY_ENABLE_SESSION_FILTER
    settings.STRATEGY_ENABLE_SESSION_FILTER = False
    bridge_service.reset_state()
    strategy_engine.reset_state()
    autopilot_service.reset_state()
    yield
    settings.STRATEGY_ENABLE_SESSION_FILTER = old_session_filter
    bridge_service.reset_state()
    strategy_engine.reset_state()
    autopilot_service.reset_state()


def get_auth_headers(username: str = "admin") -> dict:
    token = create_access_token(subject=username)
    return {"Authorization": f"Bearer {token}"}


def test_autopilot_initial_state():
    resp = client.get("/api/v1/autopilot/status")
    assert resp.status_code == 200
    data = resp.json()
    assert data["is_autopilot_active"] is False
    assert data["is_drawdown_lockout_active"] is False
    assert data["daily_drawdown_percent"] == 0.0


def test_autopilot_toggle_lifecycle():
    auth_headers = get_auth_headers("admin")

    # 1. Enable AutoPilot
    enable_resp = client.post("/api/v1/autopilot/toggle", json={"enabled": True}, headers=auth_headers)
    assert enable_resp.status_code == 200
    assert enable_resp.json()["is_autopilot_active"] is True

    status_resp = client.get("/api/v1/autopilot/status")
    assert status_resp.json()["is_autopilot_active"] is True

    # 2. Disable AutoPilot
    disable_resp = client.post("/api/v1/autopilot/toggle", json={"enabled": False}, headers=auth_headers)
    assert disable_resp.status_code == 200
    assert disable_resp.json()["is_autopilot_active"] is False


def test_autopilot_toggle_blocked_by_kill_switch():
    auth_headers = get_auth_headers("admin")

    # Engage Kill Switch
    client.post("/api/v1/risk/kill-switch", json={"reason": "Flash crash"}, headers=auth_headers)

    # Attempt to enable AutoPilot -> 403 Forbidden
    resp = client.post("/api/v1/autopilot/toggle", json={"enabled": True}, headers=auth_headers)
    assert resp.status_code == 403
    assert "Kill Switch is currently active" in resp.json()["detail"]


def test_drawdown_calculation_and_guard_breach():
    auth_headers = get_auth_headers("admin")

    # 1. Initialize baseline at $10,000 and enable AutoPilot
    autopilot_service.set_starting_equity_baseline(10000.0)
    client.post("/api/v1/autopilot/toggle", json={"enabled": True}, headers=auth_headers)

    # 2. Simulate heartbeat with $9,650 equity (3.5% drawdown, exceeding 3.0% threshold)
    client.post("/api/v1/bridge/heartbeat", json={
        "account_number": 887766,
        "server": "Demo",
        "currency": "USD",
        "balance": 10000.0,
        "equity": 9650.0,
        "floating_pnl": -350.0,
        "timestamp": int(time.time())
    })

    # 3. Check status -> Drawdown guard engaged, AutoPilot auto-shutoff
    status_resp = client.get("/api/v1/autopilot/status")
    data = status_resp.json()
    assert data["is_drawdown_lockout_active"] is True
    assert data["is_autopilot_active"] is False  # Shut down!
    assert data["daily_drawdown_percent"] == 3.50
    assert data["daily_drawdown_amount"] == 350.0

    # 4. Attempting to re-engage AutoPilot must be blocked by Drawdown Guard (403 Forbidden)
    toggle_resp = client.post("/api/v1/autopilot/toggle", json={"enabled": True}, headers=auth_headers)
    assert toggle_resp.status_code == 403
    assert "Daily Drawdown Guard" in toggle_resp.json()["detail"]

    # 5. Reset Drawdown Guard
    reset_resp = client.post("/api/v1/autopilot/reset-drawdown", json={"starting_equity": 9650.0}, headers=auth_headers)
    assert reset_resp.status_code == 200
    assert reset_resp.json()["is_drawdown_lockout_active"] is False


def test_autopilot_auto_execution_of_confluence_signals():
    auth_headers = get_auth_headers("admin")

    # 1. Establish baseline and turn on AutoPilot
    autopilot_service.set_starting_equity_baseline(10000.0)
    client.post("/api/v1/autopilot/toggle", json={"enabled": True}, headers=auth_headers)

    # 2. Generate test confluence signal
    sig_resp = client.post("/api/v1/strategy/generate-test-signal", json={
        "symbol": "EURUSD",
        "action": "BUY",
        "price": 1.08500
    }, headers=auth_headers)
    assert sig_resp.status_code == 200
    sig_data = sig_resp.json()

    # In Auto-Pilot mode, signal is auto-executed!
    assert sig_data["status"] == "APPROVED"
    assert "AUTOPILOT AUTO-EXECUTED" in sig_data["reason"]

    # Verify order was queued to MT5 bridge
    hb_resp = client.post("/api/v1/bridge/heartbeat", json={
        "account_number": 887766,
        "server": "Demo",
        "currency": "USD",
        "balance": 10000.0,
        "equity": 10000.0,
        "timestamp": int(time.time())
    })
    commands = hb_resp.json()["commands"]
    assert len(commands) == 1
    assert commands[0]["action"] == "BUY"
    assert commands[0]["symbol"] == "EURUSD"


def test_autopilot_auth_guards():
    # Toggle without JWT -> 401
    resp = client.post("/api/v1/autopilot/toggle", json={"enabled": True})
    assert resp.status_code == 401

    # Reset without JWT -> 401
    resp = client.post("/api/v1/autopilot/reset-drawdown")
    assert resp.status_code == 401


def test_closed_position_detection_and_pnl_accumulation():
    autopilot_service.set_starting_equity_baseline(10000.0)

    # 1. First heartbeat with an open position (Ticket 771122)
    sample_pos = {
        "ticket": 771122,
        "symbol": "EURUSD",
        "type": "BUY",
        "volume": 0.10,
        "open_price": 1.08500,
        "current_price": 1.08700,
        "sl": 1.08200,
        "tp": 1.09000,
        "pnl": 20.00,
        "open_time": int(time.time()),
        "magic": 778899
    }
    hb1 = client.post("/api/v1/bridge/heartbeat", json={
        "account_number": 887766,
        "server": "Demo",
        "currency": "USD",
        "balance": 10000.0,
        "equity": 10020.0,
        "floating_pnl": 20.0,
        "positions": [sample_pos],
        "open_positions": 1,
        "timestamp": int(time.time())
    })
    assert hb1.status_code == 200

    # 2. Second heartbeat where position 771122 is closed with +$150 profit
    hb2 = client.post("/api/v1/bridge/heartbeat", json={
        "account_number": 887766,
        "server": "Demo",
        "currency": "USD",
        "balance": 10150.0,
        "equity": 10150.0,
        "floating_pnl": 0.0,
        "positions": [],
        "open_positions": 0,
        "timestamp": int(time.time())
    })
    assert hb2.status_code == 200

    # 3. Status must reflect closed trade in closed_daily_pnl and total_daily_pnl
    status_resp = client.get("/api/v1/autopilot/status")
    assert status_resp.status_code == 200
    data = status_resp.json()
    assert data["closed_daily_pnl"] == 150.0
    assert data["total_daily_pnl"] == 150.0
    assert data["daily_drawdown_amount"] == 0.0
    assert data["daily_drawdown_percent"] == 0.0


def test_autopilot_candles_single_execution_no_duplicate():
    auth_headers = get_auth_headers("admin")
    autopilot_service.set_starting_equity_baseline(10000.0)
    client.post("/api/v1/autopilot/toggle", json={"enabled": True}, headers=auth_headers)

    candles = []
    price = 1.08000
    for i in range(35):
        step = 0.00010 if (i % 2 == 0) else -0.00008
        price += step
        candles.append({
            "time": 1700000000 + (i * 60),
            "open": round(price - 0.00005, 5),
            "high": round(price + 0.0001, 5),
            "low": round(price - 0.0001, 5),
            "close": round(price, 5),
            "volume": 100.0
        })

    # Post heartbeat with candles
    hb_resp = client.post("/api/v1/bridge/heartbeat", json={
        "account_number": 887766,
        "server": "Demo",
        "currency": "USD",
        "balance": 10000.0,
        "equity": 10000.0,
        "candles": candles,
        "chart_symbol": "EURUSD",
        "timestamp": int(time.time())
    })
    assert hb_resp.status_code == 200
    commands = hb_resp.json()["commands"]
    # Critical invariant: Exactly ONE order must be queued, never duplicates!
    assert len(commands) == 1
    assert commands[0]["action"] == "BUY"
    assert commands[0]["symbol"] == "EURUSD"


def test_autopilot_auto_active_on_mt5_connect():
    # Verify that when MT5 connects (sends heartbeat), AutoPilot engages automatically
    # without needing the user to toggle it manually
    hb = client.post("/api/v1/bridge/heartbeat", json={
        "account_number": 887766,
        "server": "Demo",
        "currency": "USD",
        "balance": 10000.0,
        "equity": 10000.0,
        "timestamp": int(time.time())
    })
    assert hb.status_code == 200

    status = client.get("/api/v1/autopilot/status")
    assert status.status_code == 200
    assert status.json()["is_autopilot_active"] is True
