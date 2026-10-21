import time
from fastapi.testclient import TestClient
from app.main import app
from app.core.config import settings
from app.models.bridge import OrderRequest
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


def test_manual_order_submission_disabled_on_api():
    """Manual order execution is explicitly disabled via web API (Full-Auto trading only)."""
    token = get_auth_token()
    headers = {"Authorization": f"Bearer {token}"}

    res = client.post(
        "/api/v1/bridge/order",
        json={"action": "BUY", "symbol": "EURUSD", "volume": 0.01},
        headers=headers
    )
    assert res.status_code == 403
    assert "Manual order placement from web application is disabled" in res.json()["detail"]


def test_internal_order_queueing_and_heartbeat_pop():
    """Internal service order queueing (from strategy / AutoPilot) works and delivers to MT5 via heartbeat."""
    # Clear pending commands
    with bridge_service._lock:
        bridge_service._pending_commands.clear()

    # 1. Queue a BUY order internally (as AutoPilot engine does)
    buy_order = OrderRequest(
        action="BUY",
        symbol="EURUSD",
        volume=0.05,
        sl=1.08500,
        tp=1.09500
    )
    buy_res = bridge_service.submit_order(buy_order)
    assert buy_res.status == "queued"
    assert buy_res.command.action == "BUY"
    assert buy_res.command.symbol == "EURUSD"
    assert buy_res.command.volume == 0.05

    # 2. Queue a CLOSE order internally
    close_order = OrderRequest(action="CLOSE", ticket=554433)
    close_res = bridge_service.submit_order(close_order)
    assert close_res.status == "queued"
    assert close_res.command.ticket == 554433

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
    commands = hb_res.json()["commands"]
    assert len(commands) == 2
    assert commands[0]["action"] == "BUY"
    assert commands[0]["symbol"] == "EURUSD"
    assert commands[1]["action"] == "CLOSE"
    assert commands[1]["ticket"] == 554433

    # 4. Status reflects pending_commands_count == 0 after dispatch
    status_res_after = client.get("/api/v1/bridge/status")
    assert status_res_after.json()["pending_commands_count"] == 0

    # 5. Subsequent heartbeat receives empty command list
    hb_res2 = client.post("/api/v1/bridge/heartbeat", json=hb_payload)
    assert len(hb_res2.json()["commands"]) == 0
