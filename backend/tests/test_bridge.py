import time
from fastapi.testclient import TestClient
from app.main import app
from app.services.bridge_service import bridge_service

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


