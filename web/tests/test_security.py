from __future__ import annotations

from dataclasses import replace

from fastapi import HTTPException
from fastapi.testclient import TestClient
from starlette.requests import Request

from web.app import create_app
from web.security import RateLimiter, client_ip, request_is_https


def make_request(
    client: str,
    *,
    headers: dict[str, str] | None = None,
    scheme: str = "http",
) -> Request:
    raw_headers = [
        (key.lower().encode("latin-1"), value.encode("latin-1"))
        for key, value in (headers or {}).items()
    ]
    return Request(
        {
            "type": "http",
            "method": "GET",
            "path": "/",
            "query_string": b"",
            "headers": raw_headers,
            "client": (client, 12345),
            "server": ("testserver", 80),
            "scheme": scheme,
        }
    )


def test_client_ip_uses_forwarded_for_only_from_trusted_proxy(settings) -> None:
    trusted = replace(settings, trusted_proxy_ips=("172.28.0.0/16",))
    request = make_request(
        "172.28.0.5",
        headers={"x-real-ip": "203.0.113.9"},
    )
    assert client_ip(request, trusted) == "203.0.113.9"

    direct = make_request(
        "198.51.100.7",
        headers={"x-real-ip": "203.0.113.9"},
    )
    assert client_ip(direct, trusted) == "198.51.100.7"


def test_https_forwarded_proto_requires_trusted_proxy(settings) -> None:
    trusted = replace(settings, trusted_proxy_ips=("172.28.0.0/16",))
    request = make_request(
        "172.28.0.5",
        headers={"x-forwarded-proto": "https"},
    )
    assert request_is_https(request, trusted) is True
    direct = make_request(
        "198.51.100.7",
        headers={"x-forwarded-proto": "https"},
    )
    assert request_is_https(direct, trusted) is False


def test_rate_limiter_sets_retry_after() -> None:
    limiter = RateLimiter(limit=1, window=60)
    limiter.check("key")
    try:
        limiter.check("key")
    except HTTPException as exc:
        assert exc.status_code == 429
        assert exc.headers["Retry-After"] == "60"
    else:
        raise AssertionError("rate limiter did not reject")


def test_login_rate_limit_is_per_forwarded_ip(settings) -> None:
    trusted = replace(settings, trusted_proxy_ips=("testclient",))
    client = TestClient(create_app(trusted), base_url="https://testserver")
    for _ in range(5):
        client.post(
            "/api/account/login",
            json={"identifier": "x", "password": "y"},
            headers={"X-Real-IP": "203.0.113.1"},
        )
    blocked = client.post(
        "/api/account/login",
        json={"identifier": "x", "password": "y"},
        headers={"X-Real-IP": "203.0.113.1"},
    )
    assert blocked.status_code == 429
    other = client.post(
        "/api/account/login",
        json={"identifier": "x", "password": "y"},
        headers={"X-Real-IP": "203.0.113.2"},
    )
    assert other.status_code == 401
