from __future__ import annotations

from pathlib import Path
import sys

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "server"))

from web.config import WebSettings, load_settings  # noqa: E402


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
    return load_settings()
