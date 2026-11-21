"""FastAPI application for the community site."""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from web.config import WebSettings, load_settings


def create_app(settings: WebSettings | None = None) -> FastAPI:
    active = settings or load_settings()
    app = FastAPI(title="NFS Online", docs_url=None, redoc_url=None)
    app.state.settings = active

    if active.static_dir.is_dir():
        app.mount(
            "/static",
            StaticFiles(directory=str(active.static_dir)),
            name="static",
        )

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
