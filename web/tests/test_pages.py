from __future__ import annotations

from fastapi.testclient import TestClient


def test_landing_and_static_assets(client: TestClient) -> None:
    page = client.get("/")
    assert page.status_code == 200
    assert 'id="downloadGrid"' in page.text
    assert 'id="copyServerAddress"' in page.text
    css = client.get("/static/styles.css")
    assert css.status_code == 200
    assert "--acid" in css.text
    script = client.get("/static/app.js")
    assert script.status_code == 200
    assert "refreshAll" in script.text


def test_account_page_has_forms(client: TestClient) -> None:
    page = client.get("/account")
    assert page.status_code == 200
    assert 'id="loginForm"' in page.text
    assert 'id="createForm"' in page.text
    assert 'id="accountPanel"' in page.text
    assert 'id="inviteCode"' not in page.text  # the input id is createInviteCode
    assert 'id="createInviteCode"' in page.text


def test_admin_page_has_forms(client: TestClient) -> None:
    page = client.get("/admin")
    assert page.status_code == 200
    assert 'id="adminLoginForm"' in page.text
    assert 'id="adminCreateForm"' in page.text
    assert 'id="inviteTable"' in page.text
    script = client.get("/static/admin.js")
    assert script.status_code == 200
    assert "loadInvites" in script.text


def test_live_payload_without_runtime_file(client: TestClient) -> None:
    response = client.get("/api/live")
    assert response.status_code == 200
    body = response.json()
    assert body["connected"] is False
    assert body["rooms"] == []
