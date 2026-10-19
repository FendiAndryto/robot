import time
from fastapi.testclient import TestClient
from app.main import app
from app.core.config import settings
from app.services.bridge_service import bridge_service

client = TestClient(app)


def get_auth_token():
    res = client.post(
        "/api/v1/auth/login",
        json={
            "username": settings.ADMIN_USERNAME,
            "password": settings.ADMIN_PASSWORD
        }
    )
    return res.json()["access_token"]


def test_order_submission_unauthorized():
    res = client.post(
        "/api/v1/bridge/order",
        json={"action": "BUY", "symbol": "EURUSD", "volume": 0.01}
    )
    assert res.status_code == 401


def test_order_submission_validation():
    token = get_auth_token()
    headers = {"Authorization": f"Bearer {token}"}

    # BUY without symbol
    res = client.post(
        "/api/v1/bridge/order",
        json={"action": "BUY", "volume": 0.01},
        headers=headers
    )
    assert res.status_code == 400
    assert "Symbol is required" in res.json()["detail"]

    # CLOSE without ticket
    res_close = client.post(
        "/api/v1/bridge/order",
        json={"action": "CLOSE"},
        headers=headers
    )
    assert res_close.status_code == 400
    assert "ticket ID is required" in res_close.json()["detail"]


def test_order_queueing_and_heartbeat_pop():
    token = get_auth_token()
    headers = {"Authorization": f"Bearer {token}"}

    # Clear pending commands
    with bridge_service._lock:
        bridge_service._pending_commands.clear()

    # 1. Queue a BUY order
    buy_res = client.post(
        "/api/v1/bridge/order",
        json={
            "action": "BUY",
            "symbol": "EURUSD",
            "volume": 0.05,
            "sl": 1.08500,
            "tp": 1.09500
        },
        headers=headers
    )
    assert buy_res.status_code == 200
    buy_data = buy_res.json()
    assert buy_data["status"] == "queued"
    assert "command_id" in buy_data
    assert buy_data["command"]["action"] == "BUY"
    assert buy_data["command"]["symbol"] == "EURUSD"
    assert buy_data["command"]["volume"] == 0.05

    # 2. Queue a CLOSE order
    close_res = client.post(
        "/api/v1/bridge/order",
        json={"action": "CLOSE", "ticket": 554433},
        headers=headers
    )
    assert close_res.status_code == 200
    assert close_res.json()["command"]["ticket"] == 554433

    # Status shows 2 pending commands
    status_res = client.get("/api/v1/bridge/status")
    assert status_res.status_code == 200
    assert status_res.json()["pending_commands_count"] == 2

    # 3. EA calls heartbeat -> both commands must be delivered
    hb_payload = {
        "account_number": 12345678,
        "server": "Demo-Server",
        "currency": "USD",
        "balance": 10000.0,
        "equity": 10000.0,
        "margin": 0.0,
        "free_margin": 10000.0,
        "margin_level": 0.0,
        "floating_pnl": 0.0,
        "terminal_connected": True,
        "open_positions": 0,
        "positions": [],
        "timestamp": int(time.time())
    }
    hb_res = client.post("/api/v1/bridge/heartbeat", json=hb_payload)
    assert hb_res.status_code == 200
    hb_data = hb_res.json()
    assert len(hb_data["commands"]) == 2
    assert hb_data["commands"][0]["action"] == "BUY"
    assert hb_data["commands"][1]["action"] == "CLOSE"

    # 4. Next heartbeat has 0 commands
    hb_res_2 = client.post("/api/v1/bridge/heartbeat", json=hb_payload)
    assert hb_res_2.status_code == 200
    assert len(hb_res_2.json()["commands"]) == 0


def test_positions_streaming():
    # Post telemetry containing an open position
    sample_position = {
        "ticket": 98765432,
        "symbol": "XAUUSD",
        "type": "BUY",
        "volume": 0.10,
        "open_price": 2720.50,
        "current_price": 2725.80,
        "sl": 2710.0,
        "tp": 2740.0,
        "pnl": 53.00,
        "open_time": int(time.time()),
        "magic": 778899
    }
    hb_payload = {
        "account_number": 12345678,
        "server": "Demo-Server",
        "currency": "USD",
        "balance": 10000.0,
        "equity": 10053.0,
        "margin": 272.0,
        "free_margin": 9781.0,
        "margin_level": 3695.96,
        "floating_pnl": 53.00,
        "terminal_connected": True,
        "open_positions": 1,
        "positions": [sample_position],
        "timestamp": int(time.time())
    }

    client.post("/api/v1/bridge/heartbeat", json=hb_payload)

    # Check /positions endpoint
    pos_res = client.get("/api/v1/bridge/positions")
    assert pos_res.status_code == 200
    positions = pos_res.json()
    assert len(positions) == 1
    assert positions[0]["ticket"] == 98765432
    assert positions[0]["symbol"] == "XAUUSD"
    assert positions[0]["pnl"] == 53.00

    # Check status endpoint includes positions
    status_res = client.get("/api/v1/bridge/status")
    assert status_res.status_code == 200
    assert len(status_res.json()["positions"]) == 1
