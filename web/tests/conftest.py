from __future__ import annotations

from pathlib import Path
import sys

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "server"))

from web.config import WebSettings, load_settings  # noqa: E402
from web.db import WebDatabase  # noqa: E402
from web.accounts import AccountService  # noqa: E402
from web.admin import AdminService  # noqa: E402
from web.downloads import DownloadService  # noqa: E402
from web.app import create_app  # noqa: E402
from common.accounts import SQLiteAccountDatabase  # noqa: E402


@pytest.fixture
def client(settings: WebSettings):
    from fastapi.testclient import TestClient

    return TestClient(create_app(settings), base_url="https://testserver")
from common.accounts import SQLiteAccountDatabase  # noqa: E402


@pytest.fixture
def settings(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> WebSettings:
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    (config_dir / "server.toml").write_text(
        "[server]\n"
        'ACCOUNT_DB = "data/accounts.sqlite3"\n'
        'ACCOUNT_FILES = "data/users"\n',
        encoding="utf-8",
    )
    downloads = tmp_path / "downloads"
    downloads.mkdir()
    monkeypatch.setenv("NFS_WEB_CONFIG", str(config_dir / "server.toml"))
    monkeypatch.setenv("NFS_WEB_DOWNLOADS_DIR", str(downloads))
    monkeypatch.setenv("NFS_WEB_PUBLIC_HOST", "testserver")
    monkeypatch.setenv("NFS_WEB_ALLOW_INSECURE", "1")
    monkeypatch.setenv(
        "NFS_WEB_ADMIN_PASSWORD_HASH",
        SQLiteAccountDatabase.encode_password("admin-test-password"),
    )
    return load_settings()


@pytest.fixture
def database(settings: WebSettings) -> SQLiteAccountDatabase:
    return SQLiteAccountDatabase(settings.account_db, settings.account_files)


@pytest.fixture
def web_db(settings: WebSettings) -> WebDatabase:
    return WebDatabase(settings.account_db, session_seconds=settings.session_seconds)


@pytest.fixture
def service(
    database: SQLiteAccountDatabase,
    web_db: WebDatabase,
    settings: WebSettings,
) -> AccountService:
    return AccountService(database, web_db, settings)


@pytest.fixture
def admin_service(
    database: SQLiteAccountDatabase,
    web_db: WebDatabase,
    settings: WebSettings,
) -> AdminService:
    return AdminService(web_db, settings, database)


@pytest.fixture
def downloads(settings: WebSettings) -> DownloadService:
    filename = "NFS-Online-Client-Pack-v0.2.22.zip"
    (settings.downloads_dir / filename).write_bytes(b"test-package")
    manifest = {
        "downloads": [
            {
                "id": "all",
                "title": "NFS Online Client Pack",
                "description": "U2 and MW clients",
                "game": "all",
                "version": "0.2.22",
                "recommended": True,
                "available": True,
                "filename": filename,
                "size": 12,
                "sizeLabel": "12 B",
                "sha256": "0" * 64,
            }
        ]
    }
    (settings.downloads_dir / "manifest.json").write_text(
        __import__("json").dumps(manifest),
        encoding="utf-8",
    )
    return DownloadService(settings.downloads_dir)
