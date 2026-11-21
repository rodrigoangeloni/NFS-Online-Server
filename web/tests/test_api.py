from __future__ import annotations

from dataclasses import replace

from fastapi.testclient import TestClient

from web.app import create_app


def register_payload(client: TestClient, name: str = "Driver") -> dict[str, object]:
    code = client.app.state.web_db.create_invite("test", 1, None, "test")
    return {
        "accountName": name,
        "email": "driver@example.com",
        "password": "secret123",
        "persona": name,
        "countryCode": "PY",
        "appearOnline": True,
        "challengeSeriesAssist": True,
        "inviteCode": code,
    }


def test_register_flow_returns_authenticated_account(client: TestClient) -> None:
    response = client.post("/api/account/register", json=register_payload(client))
    assert response.status_code == 200
    body = response.json()
    assert body["authenticated"] is True
    assert body["account"]["accountName"] == "Driver"
    assert body["csrfToken"]
    assert "nfs_web_session" in client.cookies


def test_me_and_logout(client: TestClient) -> None:
    created = client.post("/api/account/register", json=register_payload(client)).json()
    me = client.get("/api/account/me")
    assert me.status_code == 200
    assert me.json()["account"]["accountName"] == "Driver"
    csrf = created["csrfToken"]
    logout = client.post("/api/account/logout", headers={"X-CSRF-Token": csrf})
    assert logout.status_code == 200
    assert client.get("/api/account/me").json()["authenticated"] is False


def test_post_without_csrf_is_rejected(client: TestClient) -> None:
    client.post("/api/account/register", json=register_payload(client))
    response = client.post("/api/account/preferences", json={"appearOnline": False})
    assert response.status_code == 403


def test_preferences_with_csrf(client: TestClient) -> None:
    created = client.post("/api/account/register", json=register_payload(client)).json()
    response = client.post(
        "/api/account/preferences",
        json={"appearOnline": False},
        headers={"X-CSRF-Token": created["csrfToken"]},
    )
    assert response.status_code == 200
    assert response.json()["appearOnline"] is False


def test_insecure_register_is_rejected(settings) -> None:
    insecure = replace(settings, allow_insecure=False)
    client = TestClient(create_app(insecure), base_url="http://testserver")
    response = client.post("/api/account/register", json={})
    assert response.status_code == 403


def test_login_rate_limit(client: TestClient) -> None:
    for _ in range(5):
        client.post("/api/account/login", json={"identifier": "x", "password": "y"})
    response = client.post(
        "/api/account/login", json={"identifier": "x", "password": "y"}
    )
    assert response.status_code == 429


def test_download_is_served_as_attachment(client: TestClient, downloads) -> None:
    response = client.get("/downloads/all")
    assert response.status_code == 200
    assert response.content == b"test-package"
    assert "attachment" in response.headers["content-disposition"]
