from __future__ import annotations

from fastapi.testclient import TestClient

from web.app import create_app


def test_healthz_returns_ok(settings) -> None:
    client = TestClient(create_app(settings))
    response = client.get("/healthz")
    assert response.status_code == 200
    assert response.json() == {"ok": True}
