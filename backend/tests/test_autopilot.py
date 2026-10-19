import time
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.services.bridge_service import bridge_service
from app.services.strategy_engine import strategy_engine
from app.services.autopilot_service import autopilot_service
from app.core.security import create_access_token

client = TestClient(app)


@pytest.fixture(autouse=True)
def clean_state():
    bridge_service.reset_state()
    strategy_engine.reset_state()
    autopilot_service.reset_state()
    yield
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

    # 4. Attempting to place new order must be blocked by Drawdown Guard (403 Forbidden)
    order_resp = client.post("/api/v1/bridge/order", json={
        "action": "BUY",
        "symbol": "EURUSD",
        "volume": 0.1
    }, headers=auth_headers)
    assert order_resp.status_code == 403
    assert "Daily Drawdown Guard" in order_resp.json()["detail"]

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
