"""FastAPI application for the community site."""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from common.accounts import SQLiteAccountDatabase
from web.accounts import AccountService
from web.api import build_router
from web.config import WebSettings, load_settings
from web.db import WebDatabase
from web.downloads import DownloadService
from web.security import RateLimiter


def create_app(settings: WebSettings | None = None) -> FastAPI:
    active = settings or load_settings()
    app = FastAPI(title="NFS Online", docs_url=None, redoc_url=None)

    web_db = WebDatabase(active.account_db, session_seconds=active.session_seconds)
    account_service = AccountService(
        SQLiteAccountDatabase(active.account_db, active.account_files),
        web_db,
        active,
    )
    downloads = DownloadService(active.downloads_dir)
    limiter = RateLimiter(limit=5, window=60.0)

    app.state.settings = active
    app.state.web_db = web_db
    app.state.accounts = account_service
    app.state.downloads = downloads
    app.state.limiter = limiter

    if active.static_dir.is_dir():
        app.mount(
            "/static",
            StaticFiles(directory=str(active.static_dir)),
            name="static",
        )

    app.include_router(build_router(active, account_service, downloads, limiter))

    @app.middleware("http")
    async def security_headers(request: Request, call_next):
        response = await call_next(request)
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "same-origin")
        response.headers.setdefault("Permissions-Policy", "geolocation=(), microphone=()")
        return response

    @app.get("/healthz")
    def healthz() -> dict[str, bool]:
        return {"ok": True}

    @app.get("/", include_in_schema=False)
    def landing() -> FileResponse:
        return _page(active.static_dir / "index.html")

    @app.get("/account", include_in_schema=False)
    def account_page() -> FileResponse:
        return _page(active.static_dir / "account.html")

    return app


def _page(path: Path) -> FileResponse:
    if not path.is_file():
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail="page not found")
    return FileResponse(path)


app = create_app()
