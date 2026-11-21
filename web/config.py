"""Web settings derived from ``config/server.toml`` and environment overrides."""

from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
from typing import Mapping

from common.config import (
    ConfigurationError,
    load_configuration,
    normalize_games,
    package_root_for,
    resolve_package_path,
)


REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_SESSION_SECONDS = 7 * 24 * 3600


@dataclass(frozen=True)
class WebSettings:
    package_root: Path
    config_path: Path
    account_db: Path
    account_files: Path
    runtime_dir: Path
    downloads_dir: Path
    static_dir: Path
    public_host: str
    site_url: str
    games: tuple[str, ...]
    admin_password_hash: str
    session_seconds: int
    invite_required: bool
    allow_insecure: bool
    trusted_proxy_ips: tuple[str, ...]


def _env(environ: Mapping[str, str], name: str, default: str = "") -> str:
    return str(environ.get(name, default) or "").strip()


def _env_bool(environ: Mapping[str, str], name: str, default: bool) -> bool:
    value = _env(environ, name)
    if not value:
        return default
    return value.casefold() in {"1", "true", "yes", "on"}


def _env_int(environ: Mapping[str, str], name: str, default: int) -> int:
    value = _env(environ, name)
    if not value:
        return default
    try:
        return int(value)
    except ValueError as exc:
        raise ConfigurationError(f"{name} must be an integer") from exc


def _csv(value: str) -> tuple[str, ...]:
    return tuple(item.strip() for item in value.replace(" ", ",").split(",") if item.strip())


def load_settings(environ: Mapping[str, str] | None = None) -> WebSettings:
    env = os.environ if environ is None else environ
    config_path = Path(
        _env(env, "NFS_WEB_CONFIG", str(REPO_ROOT / "config" / "server.toml"))
    ).expanduser().resolve()
    if not config_path.is_file():
        raise ConfigurationError(f"web configuration not found: {config_path}")

    configuration = load_configuration(config_path)
    global_values = configuration["global"]
    config_root = package_root_for(config_path)

    public_host = _env(env, "NFS_WEB_PUBLIC_HOST") or _env(
        env, "NFS_PUBLIC_HOST"
    ) or global_values["PUBLIC_HOST"].strip()
    games_value = _env(env, "NFS_GAMES") or global_values["DEFAULT_GAMES"]
    games = normalize_games(games_value)

    downloads_default = REPO_ROOT.parent / "artifacts" / "downloads"
    sibling_downloads = REPO_ROOT.parent / "NFS-Online-Artifacts" / "downloads"
    if not downloads_default.is_dir() and sibling_downloads.is_dir():
        downloads_default = sibling_downloads
    downloads_dir = Path(
        _env(env, "NFS_WEB_DOWNLOADS_DIR", str(downloads_default))
    ).expanduser().resolve()
    session_seconds = _env_int(env, "NFS_WEB_SESSION_SECONDS", DEFAULT_SESSION_SECONDS)
    if session_seconds <= 0:
        raise ConfigurationError("NFS_WEB_SESSION_SECONDS must be positive")

    return WebSettings(
        package_root=config_root,
        config_path=config_path,
        account_db=resolve_package_path(config_root, global_values["ACCOUNT_DB"]),
        account_files=resolve_package_path(config_root, global_values["ACCOUNT_FILES"]),
        runtime_dir=(config_root / "runtime").resolve(),
        downloads_dir=downloads_dir,
        static_dir=(REPO_ROOT / "web" / "static").resolve(),
        public_host=public_host,
        site_url=_env(env, "NFS_WEB_SITE_URL") or f"http://{public_host}:8096",
        games=games,
        admin_password_hash=_env(env, "NFS_WEB_ADMIN_PASSWORD_HASH"),
        session_seconds=session_seconds,
        invite_required=_env_bool(env, "NFS_WEB_INVITE_REQUIRED", True),
        allow_insecure=_env_bool(env, "NFS_WEB_ALLOW_INSECURE", False),
        trusted_proxy_ips=_csv(_env(env, "NFS_WEB_TRUSTED_PROXY_IPS")),
    )
