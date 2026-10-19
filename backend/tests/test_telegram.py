import pytest
from unittest.mock import patch, AsyncMock
from fastapi.testclient import TestClient
from app.main import app
from app.core.config import settings
from app.services.telegram_service import telegram_service
from app.core.security import create_access_token


@pytest.fixture
def auth_headers(client):
    res = client.post(
        "/api/v1/auth/login",
        json={
            "username": settings.ADMIN_USERNAME,
            "password": settings.ADMIN_PASSWORD
        }
    )
    token = res.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def client():
    return TestClient(app)


def test_telegram_status_endpoint(client):
    res = client.get("/api/v1/telegram/status")
    assert res.status_code == 200
    data = res.json()
    assert "configured" in data
    assert "enabled" in data
    assert "bot_token_set" in data
    assert "chat_id_set" in data


def test_telegram_test_alert_unconfigured(client, auth_headers):
    # Ensure empty token
    with patch.object(settings, "TELEGRAM_BOT_TOKEN", ""), patch.object(settings, "TELEGRAM_CHAT_ID", ""):
        res = client.post("/api/v1/telegram/test-alert", headers=auth_headers, json={"message": "Test"})
        assert res.status_code == 200
        data = res.json()
        assert data["delivered"] is False
        assert data["is_configured"] is False


@pytest.mark.asyncio
async def test_telegram_send_message_with_mock():
    with patch.object(settings, "TELEGRAM_BOT_TOKEN", "123456:ABC-DEF"), \
         patch.object(settings, "TELEGRAM_CHAT_ID", "998877"), \
         patch.object(settings, "TELEGRAM_NOTIFICATIONS_ENABLED", True):

        mock_response = AsyncMock()
        mock_response.status_code = 200

        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_response

            success = await telegram_service.send_message("<b>Hello World</b>")
            assert success is True
            mock_post.assert_called_once()
            args, kwargs = mock_post.call_args
            assert "123456:ABC-DEF" in args[0]
            assert kwargs["json"]["chat_id"] == "998877"
            assert kwargs["json"]["text"] == "<b>Hello World</b>"


@pytest.mark.asyncio
async def test_telegram_signal_alert_mock():
    with patch.object(settings, "TELEGRAM_BOT_TOKEN", "123456:ABC-DEF"), \
         patch.object(settings, "TELEGRAM_CHAT_ID", "998877"), \
         patch.object(settings, "TELEGRAM_NOTIFICATIONS_ENABLED", True):

        mock_response = AsyncMock()
        mock_response.status_code = 200

        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_response

            signal = {
                "symbol": "EURUSD",
                "action": "BUY",
                "confidence": 0.85,
                "current_price": 1.08500,
                "suggested_sl": 1.08250,
                "suggested_tp": 1.09000,
                "status": "APPROVED",
                "is_autopilot": True
            }

            delivered = await telegram_service.send_signal_alert(signal)
            assert delivered is True
            mock_post.assert_called_once()
            called_text = mock_post.call_args[1]["json"]["text"]
            assert "EURUSD" in called_text
            assert "BUY" in called_text
            assert "85%" in called_text
            assert "Autonomous Auto-Pilot" in called_text


def test_telegram_toggle_endpoint(client, auth_headers):
    # Toggle off
    res = client.post("/api/v1/telegram/toggle", headers=auth_headers, json={"enabled": False})
    assert res.status_code == 200
    assert res.json()["notifications_enabled"] is False

    # Toggle on
    res2 = client.post("/api/v1/telegram/toggle", headers=auth_headers, json={"enabled": True})
    assert res2.status_code == 200
    assert res2.json()["notifications_enabled"] is True
