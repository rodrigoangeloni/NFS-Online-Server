from __future__ import annotations

from fastapi.testclient import TestClient

from web.api import ADMIN_COOKIE


def admin_login(client: TestClient) -> str:
    response = client.post(
        "/api/admin/login",
        json={"password": "admin-test-password"},
    )
    assert response.status_code == 200
    assert ADMIN_COOKIE in client.cookies
    return response.json()["csrfToken"]


def test_admin_invites_require_login(client: TestClient) -> None:
    assert client.get("/api/admin/invites").status_code == 401


def test_admin_wrong_password(client: TestClient) -> None:
    response = client.post(
        "/api/admin/login",
        json={"password": "wrong"},
    )
    assert response.status_code == 401


def test_admin_create_list_and_revoke_invite(client: TestClient) -> None:
    csrf = admin_login(client)
    created = client.post(
        "/api/admin/invites",
        json={"label": "amigos", "maxUses": 3, "days": 30},
        headers={"X-CSRF-Token": csrf},
    )
    assert created.status_code == 200
    invite = created.json()["invite"]
    assert invite["code"].startswith("NFS-")
    listing = client.get("/api/admin/invites")
    assert listing.status_code == 200
    assert listing.json()["invites"][0]["code"] == invite["code"]

    revoked = client.post(
        f"/api/admin/invites/{invite['codeHash']}/revoke",
        headers={"X-CSRF-Token": csrf},
    )
    assert revoked.status_code == 200
    assert client.get("/api/admin/invites").json()["invites"][0]["status"] == "revoked"


def test_admin_write_requires_csrf(client: TestClient) -> None:
    admin_login(client)
    response = client.post(
        "/api/admin/invites",
        json={"label": "x", "maxUses": 1, "days": 1},
    )
    assert response.status_code == 403
