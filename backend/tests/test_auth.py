import uuid
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.core.config import settings
from app.core.security import hash_password, verify_password, rate_limiter
from app.services.user_service import user_service

client = TestClient(app)


@pytest.fixture(autouse=True)
def reset_rate_limiter():
    rate_limiter.reset()
    yield
    rate_limiter.reset()


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
    assert "bridge_token" in data


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
    assert me_data["bridge_token"] is not None


def test_logout_and_session_revocation():
    # Login to get a valid token
    user = f"logout_{uuid.uuid4().hex[:6]}"
    client.post(
        "/api/v1/auth/register",
        json={"username": user, "password": "Password123!"}
    )
    login_res = client.post(
        "/api/v1/auth/login",
        json={"username": user, "password": "Password123!"}
    )
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Verify token works before logout
    me_before = client.get("/api/v1/auth/me", headers=headers)
    assert me_before.status_code == 200

    # Logout
    logout_res = client.post("/api/v1/auth/logout", headers=headers)
    assert logout_res.status_code == 200
    assert logout_res.json()["status"] == "ok"

    # Subsequent request with old token must now fail with 401 (token revocation!)
    me_after = client.get("/api/v1/auth/me", headers=headers)
    assert me_after.status_code == 401
    assert "revoked" in me_after.json()["detail"].lower()


def test_bcrypt_hashing_and_verification():
    raw_pass = "my_custom_secret_pass"
    hashed = hash_password(raw_pass)
    assert hashed != raw_pass
    assert verify_password(raw_pass, hashed) is True
    assert verify_password("wrong_pass", hashed) is False


def test_register_and_login_new_user():
    unique_user = f"trader_{uuid.uuid4().hex[:6]}"
    reg_res = client.post(
        "/api/v1/auth/register",
        json={
            "username": unique_user,
            "email": f"{unique_user}@tradegear.local",
            "password": "Password123!",
            "role": "trader"
        }
    )
    assert reg_res.status_code == 201
    reg_data = reg_res.json()
    assert reg_data["username"] == unique_user
    assert reg_data["role"] == "trader"
    assert reg_data["bridge_token"].startswith("tg_live_")

    # Verify duplicate fails
    dup_res = client.post(
        "/api/v1/auth/register",
        json={
            "username": unique_user,
            "password": "AnotherPassword123!"
        }
    )
    assert dup_res.status_code == 400

    # Verify login with new user
    login_res = client.post(
        "/api/v1/auth/login",
        json={
            "username": unique_user,
            "password": "Password123!"
        }
    )
    assert login_res.status_code == 200
    token = login_res.json()["access_token"]

    # Verify profile for new user
    me_res = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert me_res.status_code == 200
    assert me_res.json()["username"] == unique_user
    assert me_res.json()["role"] == "trader"
    assert me_res.json()["bridge_token"] == reg_data["bridge_token"]


def test_password_complexity_enforcement():
    u = f"pwtest_{uuid.uuid4().hex[:6]}"

    # Less than 8 chars
    res_short = client.post(
        "/api/v1/auth/register",
        json={"username": u, "password": "Ab1"}
    )
    assert res_short.status_code in (400, 422)

    # Missing numbers
    res_no_num = client.post(
        "/api/v1/auth/register",
        json={"username": u, "password": "OnlyLettersHere"}
    )
    assert res_no_num.status_code == 400

    # Missing letters
    res_no_letter = client.post(
        "/api/v1/auth/register",
        json={"username": u, "password": "1234567890"}
    )
    assert res_no_letter.status_code == 400

    # Valid alphanumeric
    res_valid = client.post(
        "/api/v1/auth/register",
        json={"username": u, "password": "ValidPassword99"}
    )
    assert res_valid.status_code == 201


def test_change_password_flow_and_session_revocation():
    user = f"cp_user_{uuid.uuid4().hex[:6]}"
    # Register
    client.post(
        "/api/v1/auth/register",
        json={"username": user, "password": "InitialPassword123"}
    )
    # Login
    login_res = client.post(
        "/api/v1/auth/login",
        json={"username": user, "password": "InitialPassword123"}
    )
    old_token = login_res.json()["access_token"]
    old_headers = {"Authorization": f"Bearer {old_token}"}

    # Wrong old password
    wrong_old = client.post(
        "/api/v1/auth/change-password",
        headers=old_headers,
        json={"old_password": "WrongPassword", "new_password": "BrandNewPassword456"}
    )
    assert wrong_old.status_code == 400

    # Success change password
    success_change = client.post(
        "/api/v1/auth/change-password",
        headers=old_headers,
        json={"old_password": "InitialPassword123", "new_password": "BrandNewPassword456"}
    )
    assert success_change.status_code == 200

    # Verify that the old token is immediately REVOKED
    me_revoked = client.get("/api/v1/auth/me", headers=old_headers)
    assert me_revoked.status_code == 401

    # Verify login with old password fails
    fail_login = client.post(
        "/api/v1/auth/login",
        json={"username": user, "password": "InitialPassword123"}
    )
    assert fail_login.status_code == 401

    # Verify login with new password succeeds
    ok_login = client.post(
        "/api/v1/auth/login",
        json={"username": user, "password": "BrandNewPassword456"}
    )
    assert ok_login.status_code == 200


def test_registration_blocks_admin_role_escalation():
    user = f"hacker_{uuid.uuid4().hex[:6]}"
    res = client.post(
        "/api/v1/auth/register",
        json={
            "username": user,
            "password": "Password123!",
            "role": "admin"
        }
    )
    assert res.status_code == 201
    data = res.json()
    assert data["role"] == "trader"


def test_deactivated_user_token_rejected():
    user = f"deact_{uuid.uuid4().hex[:6]}"
    client.post(
        "/api/v1/auth/register",
        json={"username": user, "password": "Password123!"}
    )
    login_res = client.post(
        "/api/v1/auth/login",
        json={"username": user, "password": "Password123!"}
    )
    token = login_res.json()["access_token"]

    # Deactivate account
    user_service.deactivate_user(user)

    # Calling /me with existing valid token must now fail with 401
    me_res = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert me_res.status_code == 401
    assert "account deactivated" in me_res.json()["detail"].lower()


def test_case_insensitive_username_handling():
    suffix = uuid.uuid4().hex[:6]
    orig_user = f"Trader_{suffix}"

    reg_res = client.post(
        "/api/v1/auth/register",
        json={"username": orig_user, "password": "Password123!"}
    )
    assert reg_res.status_code == 201

    login_lower = client.post(
        "/api/v1/auth/login",
        json={"username": orig_user.lower(), "password": "Password123!"}
    )
    assert login_lower.status_code == 200

    dup_res = client.post(
        "/api/v1/auth/register",
        json={"username": orig_user.upper(), "password": "Password123!"}
    )
    assert dup_res.status_code == 400


def test_rate_limiting_brute_force_protection():
    u = f"brute_{uuid.uuid4().hex[:6]}"
    # 5 failed attempts
    for _ in range(5):
        res = client.post("/api/v1/auth/login", json={"username": u, "password": "WrongPassword1"})
        assert res.status_code == 401

    # 6th attempt must be rate-limited with 429
    res_limited = client.post("/api/v1/auth/login", json={"username": u, "password": "WrongPassword1"})
    assert res_limited.status_code == 429
    assert "too many" in res_limited.json()["detail"].lower()


def test_bridge_token_retrieval_and_regeneration():
    u = f"tokuser_{uuid.uuid4().hex[:6]}"
    client.post("/api/v1/auth/register", json={"username": u, "password": "Password123!"})
    login_res = client.post("/api/v1/auth/login", json={"username": u, "password": "Password123!"})
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Fetch token
    tok_res = client.get("/api/v1/auth/bridge-token", headers=headers)
    assert tok_res.status_code == 200
    orig_bridge_token = tok_res.json()["bridge_token"]
    assert orig_bridge_token.startswith("tg_live_")

    # Regenerate token
    regen_res = client.post("/api/v1/auth/bridge-token/regenerate", headers=headers)
    assert regen_res.status_code == 200
    new_bridge_token = regen_res.json()["bridge_token"]
    assert new_bridge_token.startswith("tg_live_")
    assert new_bridge_token != orig_bridge_token
