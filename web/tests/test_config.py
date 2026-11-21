from __future__ import annotations

from pathlib import Path

from web.config import load_settings


def test_load_settings_reads_public_host_and_paths(
    tmp_path: Path, monkeypatch
) -> None:
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    (config_dir / "server.toml").write_text(
        "[server]\n"
        'DEFAULT_GAMES = ["u2", "mw"]\n'
        'PUBLIC_HOST = "nfs.example.com"\n'
        'ACCOUNT_DB = "data/accounts.sqlite3"\n'
        'ACCOUNT_FILES = "data/users"\n',
        encoding="utf-8",
    )
    monkeypatch.setenv("NFS_WEB_CONFIG", str(config_dir / "server.toml"))
    monkeypatch.setenv("NFS_WEB_DOWNLOADS_DIR", str(tmp_path / "downloads"))
    monkeypatch.setenv("NFS_WEB_PUBLIC_HOST", "nfs.example.com")
    monkeypatch.setenv("NFS_GAMES", "u2,mw")
    settings = load_settings()
    assert settings.public_host == "nfs.example.com"
    assert settings.games == ("u2", "mw")
    assert settings.account_db.name == "accounts.sqlite3"
    assert settings.account_db.parent == tmp_path / "data"
    assert settings.downloads_dir.name == "downloads"
    assert settings.static_dir.name == "static"
    assert settings.invite_required is True


def test_load_settings_allows_open_registration_for_lan(
    tmp_path: Path, monkeypatch
) -> None:
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    (config_dir / "server.toml").write_text("[server]\n", encoding="utf-8")
    monkeypatch.setenv("NFS_WEB_CONFIG", str(config_dir / "server.toml"))
    monkeypatch.setenv("NFS_WEB_DOWNLOADS_DIR", str(tmp_path / "downloads"))
    monkeypatch.setenv("NFS_WEB_INVITE_REQUIRED", "0")
    settings = load_settings()
    assert settings.invite_required is False
