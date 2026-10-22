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
    """Order execution is explicitly disabled via web API under Pure Read-Only SaaS architecture."""
    headers, _ = get_auth_context()

    res = client.post(
        "/api/v1/bridge/order",
        json={"action": "BUY", "symbol": "EURUSD", "volume": 0.01},
        headers=headers
    )
    assert res.status_code == 403
    assert "TradeGear is a 100% Pure Read-Only SaaS platform" in res.json()["detail"]


def test_pure_read_only_saas_rejects_order_execution_and_commands_empty():
    """Under Pure Read-Only SaaS architecture, order submission is permanently disabled and heartbeat returns zero commands."""
    headers, bridge_token = get_auth_context()
    bridge_service.reset_state()

    # 1. Direct submit_order call must raise HTTPException 403 Forbidden
    from fastapi import HTTPException
    buy_order = OrderRequest(
        action="BUY",
        symbol="EURUSD",
        volume=0.05,
        sl=1.08500,
        tp=1.09500
    )
    with pytest.raises(HTTPException) as exc_info:
        bridge_service.submit_order(buy_order, username=settings.ADMIN_USERNAME)
    assert exc_info.value.status_code == 403
    assert "TradeGear is a 100% Pure Read-Only SaaS platform" in exc_info.value.detail

    # 2. Status shows 0 pending commands
    status_res = client.get("/api/v1/bridge/status", headers=headers)
    assert status_res.status_code == 200
    assert status_res.json()["pending_commands_count"] == 0

    # 3. EA calls heartbeat -> commands must be empty list
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
    assert commands == []
