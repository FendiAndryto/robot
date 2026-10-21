import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.services.bridge_service import bridge_service
from app.core.security import create_access_token
from app.core.config import settings

client = TestClient(app)


@pytest.fixture(autouse=True)
def clean_state():
    bridge_service.reset_state()
    yield
    bridge_service.reset_state()


def get_auth_headers(username: str = "admin") -> dict:
    token = create_access_token(subject=username)
    return {"Authorization": f"Bearer {token}"}


def test_calculate_lot_eurusd():
    payload = {
        "symbol": "EURUSD",
        "stop_loss_pips": 20.0,
        "risk_percent": 1.0,
        "equity": 10000.0
    }
    response = client.post("/api/v1/risk/calculate-lot", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["symbol"] == "EURUSD"
    assert data["equity"] == 10000.0
    assert data["risk_percent"] == 1.0
    assert data["risk_amount"] == 100.0
    assert data["stop_loss_pips"] == 20.0
    assert data["pip_value_per_lot"] == 10.0
    # 100 / (20 * 10) = 0.50 lots
    assert data["calculated_lot"] == 0.50


def test_calculate_lot_xauusd():
    payload = {
        "symbol": "XAUUSD",
        "stop_loss_pips": 50.0,
        "risk_percent": 2.0,
        "equity": 5000.0
    }
    response = client.post("/api/v1/risk/calculate-lot", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["symbol"] == "XAUUSD"
    assert data["risk_amount"] == 100.0
    # 100 / (50 * 10) = 0.20 lots
    assert data["calculated_lot"] == 0.20


def test_calculate_lot_usdjpy():
    payload = {
        "symbol": "USDJPY",
        "stop_loss_pips": 30.0,
        "risk_percent": 1.0,
        "equity": 10000.0,
        "market_price": 150.0
    }
    response = client.post("/api/v1/risk/calculate-lot", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["symbol"] == "USDJPY"
    assert data["risk_amount"] == 100.0
    # pip_val = 1000 / 150 = 6.6667; 100 / (30 * 6.6667) = 0.50 lots
    assert data["calculated_lot"] == 0.50


def test_calculate_lot_min_clamping():
    # Tiny risk amount with massive SL distance
    payload = {
        "symbol": "EURUSD",
        "stop_loss_pips": 500.0,
        "risk_percent": 0.05,
        "equity": 100.0
    }
    response = client.post("/api/v1/risk/calculate-lot", json=payload)
    assert response.status_code == 200
    data = response.json()
    # Clamped to MIN_LOT_SIZE (0.01)
    assert data["calculated_lot"] == settings.MIN_LOT_SIZE


def test_calculate_lot_max_risk_rejection():
    payload = {
        "symbol": "EURUSD",
        "stop_loss_pips": 20.0,
        "risk_percent": 25.0,  # Exceeds max ceiling (10.0%)
        "equity": 10000.0
    }
    response = client.post("/api/v1/risk/calculate-lot", json=payload)
    assert response.status_code == 400
    assert "exceeds maximum allowed safety ceiling" in response.json()["detail"]


def test_calculate_lot_uses_live_equity_when_omitted():
    # Simulate a heartbeat sending account equity of $30,000
    heartbeat_payload = {
        "account_number": 998877,
        "server": "Demo-Server",
        "currency": "USD",
        "balance": 30000.0,
        "equity": 30000.0,
        "margin": 0.0,
        "free_margin": 30000.0,
        "margin_level": 0.0,
        "floating_pnl": 0.0,
        "terminal_connected": True,
        "open_positions": 0,
        "positions": [],
        "timestamp": 1700000000
    }
    hb_resp = client.post("/api/v1/bridge/heartbeat", json=heartbeat_payload)
    assert hb_resp.status_code == 200

    # Calculate lot without providing equity
    payload = {
        "symbol": "EURUSD",
        "stop_loss_pips": 30.0,
        "risk_percent": 1.0
    }
    response = client.post("/api/v1/risk/calculate-lot", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["equity"] == 30000.0
    assert data["risk_amount"] == 300.0
    # 300 / (30 * 10) = 1.00 lots
    assert data["calculated_lot"] == 1.00


def test_kill_switch_lifecycle():
    auth_headers = get_auth_headers("admin")

    # 1. Initial status: kill switch disarmed
    status_resp = client.get("/api/v1/risk/status")
    assert status_resp.status_code == 200
    assert status_resp.json()["is_kill_switch_active"] is False

    # 2. Trigger kill switch
    trigger_payload = {"reason": "Test Market Volatility Spike"}
    kill_resp = client.post("/api/v1/risk/kill-switch", json=trigger_payload, headers=auth_headers)
    assert kill_resp.status_code == 200
    kill_data = kill_resp.json()
    assert kill_data["status"] == "engaged"
    assert kill_data["is_kill_switch_active"] is True
    assert kill_data["reason"] == "Test Market Volatility Spike"

    # 3. Verify bridge status reflects kill switch engagement
    bridge_status = client.get("/api/v1/bridge/status").json()
    assert bridge_status["is_kill_switch_active"] is True
    assert bridge_status["kill_switch_reason"] == "Test Market Volatility Spike"

    # 4. Verify CLOSE_ALL command is queued for MT5
    hb_resp = client.post("/api/v1/bridge/heartbeat", json={
        "account_number": 12345,
        "server": "Demo",
        "currency": "USD",
        "balance": 10000.0,
        "equity": 10000.0,
        "timestamp": 1700000000
    })
    assert hb_resp.status_code == 200
    commands = hb_resp.json()["commands"]
    assert len(commands) == 1
    assert commands[0]["action"] == "CLOSE_ALL"

    # 5. Internal service BUY or SELL must raise HTTPException 403 while Kill Switch is active
    from app.models.bridge import OrderRequest
    from fastapi import HTTPException
    import pytest
    with pytest.raises(HTTPException) as exc_info:
        bridge_service.submit_order(OrderRequest(action="BUY", symbol="EURUSD", volume=0.1))
    assert exc_info.value.status_code == 403
    assert "locked by emergency Kill Switch" in exc_info.value.detail

    # 6. Web API always returns 403 (manual order execution disabled)
    buy_resp = client.post("/api/v1/bridge/order", json={
        "action": "BUY",
        "symbol": "EURUSD",
        "volume": 0.1
    }, headers=auth_headers)
    assert buy_resp.status_code == 403
    assert "Manual order placement from web application is disabled" in buy_resp.json()["detail"]

    # 7. Disarm / unlock the kill switch
    unlock_resp = client.post("/api/v1/risk/unlock", headers=auth_headers)
    assert unlock_resp.status_code == 200
    assert unlock_resp.json()["status"] == "disarmed"
    assert unlock_resp.json()["is_kill_switch_active"] is False

    # 8. Internal service BUY is now permitted again
    buy_again_resp = bridge_service.submit_order(OrderRequest(action="BUY", symbol="EURUSD", volume=0.1))
    assert buy_again_resp.status == "queued"


def test_kill_switch_unauthorized():
    # Attempting to trigger without token -> 401
    resp = client.post("/api/v1/risk/kill-switch", json={"reason": "Hacker attempt"})
    assert resp.status_code == 401

    # Attempting to unlock without token -> 401
    resp = client.post("/api/v1/risk/unlock")
    assert resp.status_code == 401
