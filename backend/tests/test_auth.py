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


def test_register_and_login_new_user():
    import uuid
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


def test_change_password_flow():
    import uuid
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
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Wrong old password
    wrong_old = client.post(
        "/api/v1/auth/change-password",
        headers=headers,
        json={"old_password": "WrongPassword", "new_password": "BrandNewPassword456"}
    )
    assert wrong_old.status_code == 400

    # Success change password
    success_change = client.post(
        "/api/v1/auth/change-password",
        headers=headers,
        json={"old_password": "InitialPassword123", "new_password": "BrandNewPassword456"}
    )
    assert success_change.status_code == 200

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
    import uuid
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
    # Must be forced to trader, never allowed to escalate to admin
    assert data["role"] == "trader"


def test_deactivated_user_token_rejected():
    import uuid
    from app.services.user_service import user_service

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
    key = user.lower()
    with user_service._lock:
        user_service._users[key]["is_active"] = False
        user_service._save_users()

    # Calling /me with existing valid token must now fail with 401
    me_res = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert me_res.status_code == 401
    assert "account deactivated" in me_res.json()["detail"].lower()


def test_case_insensitive_username_handling():
    import uuid
    suffix = uuid.uuid4().hex[:6]
    orig_user = f"Trader_{suffix}"

    # Register with mixed case
    reg_res = client.post(
        "/api/v1/auth/register",
        json={"username": orig_user, "password": "Password123!"}
    )
    assert reg_res.status_code == 201

    # Login with all lowercase
    login_lower = client.post(
        "/api/v1/auth/login",
        json={"username": orig_user.lower(), "password": "Password123!"}
    )
    assert login_lower.status_code == 200

    # Duplicate registration with different casing should fail
    dup_res = client.post(
        "/api/v1/auth/register",
        json={"username": orig_user.upper(), "password": "Password123!"}
    )
    assert dup_res.status_code == 400


