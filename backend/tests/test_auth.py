from fastapi.testclient import TestClient
from app.main import app
from app.core.config import settings
from app.core.security import hash_password, verify_password

client = TestClient(app)


def test_login_success():
    response = client.post(
        "/api/v1/auth/login",
        json={
            "username": settings.ADMIN_USERNAME,
            "password": settings.ADMIN_PASSWORD
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["expires_in"] == settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60


def test_login_invalid_password():
    response = client.post(
        "/api/v1/auth/login",
        json={
            "username": settings.ADMIN_USERNAME,
            "password": "wrong_password_123"
        }
    )
    assert response.status_code == 401
    assert "Invalid username or password" in response.json()["detail"]


def test_login_invalid_username():
    response = client.post(
        "/api/v1/auth/login",
        json={
            "username": "unknown_user",
            "password": settings.ADMIN_PASSWORD
        }
    )
    assert response.status_code == 401


def test_get_me_unauthorized():
    response = client.get("/api/v1/auth/me")
    assert response.status_code == 401


def test_get_me_invalid_token():
    response = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": "Bearer invalid_token_xyz"}
    )
    assert response.status_code == 401


def test_get_me_authorized():
    # Login first
    login_res = client.post(
        "/api/v1/auth/login",
        json={
            "username": settings.ADMIN_USERNAME,
            "password": settings.ADMIN_PASSWORD
        }
    )
    token = login_res.json()["access_token"]
    
    # Request profile
    me_res = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert me_res.status_code == 200
    me_data = me_res.json()
    assert me_data["username"] == settings.ADMIN_USERNAME
    assert me_data["is_authenticated"] is True


def test_logout():
    response = client.post("/api/v1/auth/logout")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_bcrypt_hashing_and_verification():
    raw_pass = "my_custom_secret_pass"
    hashed = hash_password(raw_pass)
    assert hashed != raw_pass
    assert verify_password(raw_pass, hashed) is True
    assert verify_password("wrong_pass", hashed) is False
