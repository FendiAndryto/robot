import time
from fastapi.testclient import TestClient
from app.main import app
from app.core.config import settings
from app.models.bridge import OrderRequest
from app.services.bridge_service import bridge_service
from app.services.user_service import user_service
from app.core.security import create_access_token

import pytest
from app.services.autopilot_service import autopilot_service

client = TestClient(app)


@pytest.fixture(autouse=True)
def clean_state():
    bridge_service.reset_state()
    autopilot_service.reset_state()
    yield
    bridge_service.reset_state()
    autopilot_service.reset_state()


def get_auth_context(username: str = settings.ADMIN_USERNAME):
    user = user_service.get_user(username)
    if not user:
        user = user_service.register(username, "AdminPassword123!")
    token = create_access_token(user["username"], user.get("token_version", 1))
    return {"Authorization": f"Bearer {token}"}, user["bridge_token"]


def test_manual_order_submission_disabled_on_api():
    """Manual order execution is explicitly disabled via web API (Full-Auto trading only)."""
    headers, _ = get_auth_context()

    res = client.post(
        "/api/v1/bridge/order",
        json={"action": "BUY", "symbol": "EURUSD", "volume": 0.01},
        headers=headers
    )
    assert res.status_code == 403
    assert "Manual order placement from web application is disabled" in res.json()["detail"]


def test_internal_order_queueing_and_heartbeat_pop():
    """Internal service order queueing (from strategy / AutoPilot) works and delivers to MT5 via heartbeat."""
    headers, bridge_token = get_auth_context()
    bridge_service.reset_state()

    # 1. Queue a BUY order internally (as AutoPilot engine does)
    buy_order = OrderRequest(
        action="BUY",
        symbol="EURUSD",
        volume=0.05,
        sl=1.08500,
        tp=1.09500
    )
    buy_res = bridge_service.submit_order(buy_order, username=settings.ADMIN_USERNAME)
    assert buy_res.status == "queued"
    assert buy_res.command.action == "BUY"
    assert buy_res.command.symbol == "EURUSD"
    assert buy_res.command.volume == 0.05

    # 2. Queue a CLOSE order internally
    close_order = OrderRequest(action="CLOSE", ticket=554433)
    close_res = bridge_service.submit_order(close_order, username=settings.ADMIN_USERNAME)
    assert close_res.status == "queued"
    assert close_res.command.ticket == 554433

    # Status shows 2 pending commands
    status_res = client.get("/api/v1/bridge/status", headers=headers)
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
        "bridge_token": bridge_token,
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
    status_res_after = client.get("/api/v1/bridge/status", headers=headers)
    assert status_res_after.json()["pending_commands_count"] == 0

    # 5. Subsequent heartbeat receives empty command list
    hb_res2 = client.post("/api/v1/bridge/heartbeat", json=hb_payload)
    assert len(hb_res2.json()["commands"]) == 0
