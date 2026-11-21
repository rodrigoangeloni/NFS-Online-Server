"""Request security helpers: HTTPS, CSRF and in-memory rate limiting."""

from __future__ import annotations

from collections import defaultdict, deque
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
                raise HTTPException(status_code=429, detail="too many attempts")
            events.append(timestamp)


def request_is_https(request: Request, settings: WebSettings) -> bool:
    if request.url.scheme == "https":
        return True
    forwarded = request.headers.get("x-forwarded-proto", "").split(",")[0].strip()
    if forwarded.casefold() == "https":
        client = request.client.host if request.client else ""
        if client in settings.trusted_proxy_ips:
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
