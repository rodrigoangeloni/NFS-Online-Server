from __future__ import annotations

from fastapi.testclient import TestClient

from web.api import ADMIN_COOKIE


def make_payload(client: TestClient, name: str = "RecoveryUser") -> dict[str, object]:
    code = client.app.state.web_db.create_invite("test", 1, None, "test")
    return {
        "accountName": name,
        "email": "recovery@example.com",
        "password": "secret123",
        "persona": name,
        "countryCode": "PY",
        "appearOnline": True,
        "challengeSeriesAssist": True,
        "inviteCode": code,
    }


def test_register_returns_recovery_code_and_forgot_flow(
    client: TestClient,
) -> None:
    registration = client.post("/api/account/register", json=make_payload(client))
    assert registration.status_code == 200
    body = registration.json()
    recovery = body["recoveryCode"]
    assert recovery.startswith("NFS-REC-")

    forgot = client.post(
        "/api/account/forgot",
        json={
            "accountName": "RecoveryUser",
            "email": "recovery@example.com",
            "recoveryCode": recovery,
        },
    )
    assert forgot.status_code == 200
    temporary = forgot.json()["temporaryPassword"]
    assert temporary.startswith("NFS-TMP-")

    fresh = TestClient(client.app, base_url="https://testserver")
    login = fresh.post(
        "/api/account/login",
        json={"identifier": "RecoveryUser", "password": temporary},
    )
    assert login.status_code == 200
    login_body = login.json()
    assert login_body["account"]["mustChangePassword"] is True
    csrf = login_body["csrfToken"]

    changed = fresh.post(
        "/api/account/password",
        json={"currentPassword": temporary, "newPassword": "newsecret123"},
        headers={"X-CSRF-Token": csrf},
    )
    assert changed.status_code == 200
    assert fresh.post(
        "/api/account/login",
        json={"identifier": "RecoveryUser", "password": "newsecret123"},
    ).status_code == 200


def test_user_can_update_email_with_password(client: TestClient) -> None:
    registered = client.post("/api/account/register", json=make_payload(client)).json()
    csrf = registered["csrfToken"]
    response = client.post(
        "/api/account/email",
        json={"email": "new@example.com", "password": "secret123"},
        headers={"X-CSRF-Token": csrf},
    )
    assert response.status_code == 200
    assert response.json()["account"]["email"] == "new@example.com"


def test_admin_can_reset_account_and_change_password(client: TestClient) -> None:
    login = client.post(
        "/api/admin/login",
        json={"password": "admin-test-password"},
    )
    assert login.status_code == 200
    csrf = login.json()["csrfToken"]
    assert ADMIN_COOKIE in client.cookies

    client.app.state.accounts.database.create_account(
        "ResetMe",
        "secret123",
        email="reset@example.com",
    )
    reset = client.post(
        "/api/admin/accounts/ResetMe/reset-password",
        headers={"X-CSRF-Token": csrf},
    )
    assert reset.status_code == 200
    temporary = reset.json()["temporaryPassword"]
    assert temporary.startswith("NFS-TMP-")
    fresh = TestClient(client.app, base_url="https://testserver")
    assert fresh.post(
        "/api/account/login",
        json={"identifier": "ResetMe", "password": temporary},
    ).json()["account"]["mustChangePassword"] is True

    changed = client.post(
        "/api/admin/password",
        json={
            "currentPassword": "admin-test-password",
            "newPassword": "new-admin-password",
        },
        headers={"X-CSRF-Token": csrf},
    )
    assert changed.status_code == 200
    assert client.get("/api/admin/me").json()["authenticated"] is True
    assert client.post(
        "/api/admin/login",
        json={"password": "admin-test-password"},
    ).status_code == 401
    assert client.post(
        "/api/admin/login",
        json={"password": "new-admin-password"},
    ).status_code == 200
