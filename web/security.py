"""Request security helpers: HTTPS, CSRF and in-memory rate limiting."""

from __future__ import annotations

from collections import defaultdict, deque
import ipaddress
import secrets
from threading import RLock
import time

from fastapi import HTTPException, Request

from web.config import WebSettings
from web.db import Session


class RateLimiter:
    def __init__(self, limit: int = 5, window: float = 60.0) -> None:
        self.limit = max(1, int(limit))
        self.window = max(1.0, float(window))
        self._events: dict[str, deque[float]] = defaultdict(deque)
        self._lock = RLock()

    def check(self, key: str, *, now: float | None = None) -> None:
        timestamp = time.monotonic() if now is None else float(now)
        with self._lock:
            events = self._events[key]
            while events and events[0] <= timestamp - self.window:
                events.popleft()
            if len(events) >= self.limit:
                raise HTTPException(
                    status_code=429,
                    detail="too many attempts",
                    headers={"Retry-After": str(int(self.window))},
                )
            events.append(timestamp)


def _is_trusted_proxy(host: str, settings: WebSettings) -> bool:
    peer = str(host or "").strip()
    for entry in settings.trusted_proxy_ips:
        text = str(entry or "").strip()
        if text and text.casefold() == peer.casefold():
            return True
    try:
        address = ipaddress.ip_address(peer)
    except ValueError:
        return False
    for entry in settings.trusted_proxy_ips:
        text = str(entry or "").strip()
        if not text:
            continue
        try:
            if "/" in text:
                if address in ipaddress.ip_network(text, strict=False):
                    return True
            elif address == ipaddress.ip_address(text):
                return True
        except ValueError:
            continue
    return False


def client_ip(request: Request, settings: WebSettings) -> str:
    peer = request.client.host if request.client else ""
    if not _is_trusted_proxy(peer, settings):
        return peer or "unknown"
    real = request.headers.get("x-real-ip", "").strip()
    if real:
        return real
    forwarded = request.headers.get("x-forwarded-for", "")
    if forwarded:
        # The trusted proxy appends the real peer at the end.
        last = forwarded.split(",")[-1].strip()
        if last:
            return last
    return peer or "unknown"


def request_is_https(request: Request, settings: WebSettings) -> bool:
    if request.url.scheme == "https":
        return True
    forwarded = request.headers.get("x-forwarded-proto", "").split(",")[0].strip()
    if forwarded.casefold() == "https":
        client = request.client.host if request.client else ""
        if _is_trusted_proxy(client, settings):
            return True
    return False


def require_https(request: Request, settings: WebSettings) -> None:
    if settings.allow_insecure or request_is_https(request, settings):
        return
    raise HTTPException(status_code=403, detail="https required")


def require_csrf(request: Request, session: Session) -> None:
    supplied = request.headers.get("x-csrf-token", "")
    if not supplied or not secrets.compare_digest(supplied, session.csrf_token):
        raise HTTPException(status_code=403, detail="invalid csrf token")
