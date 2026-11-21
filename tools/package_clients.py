"""Build preconfigured NFS Online client ZIPs and their download manifest."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
from typing import Iterable, Sequence
import zipfile


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CLIENTS_DIR = ROOT / "clients"
DEFAULT_TEMPLATES_DIR = ROOT / "packaging" / "client"
DEFAULT_LICENSES_DIR = ROOT / "LICENSES"

GAME_CONFIG = {
    "u2": {
        "label": "Underground 2",
        "folder": "U2",
        "asi": "net_u2.asi",
        "ini": "net_u2.ini",
        "clients": "underground2",
        "fix_folder": "NFSUnderground2",
        "fix_prefix": "NFSUnderground2.WidescreenFix",
    },
    "mw": {
        "label": "Most Wanted",
        "folder": "MW",
        "asi": "net_mw.asi",
        "ini": "net_mw.ini",
        "clients": "most-wanted",
        "fix_folder": "NFSMostWanted",
        "fix_prefix": "NFSMostWanted.WidescreenFix",
    },
}

HOST_PATTERN = re.compile(r"^[A-Za-z0-9](?:[A-Za-z0-9._-]{0,251}[A-Za-z0-9])?$")
HOST_LINE = re.compile(r"(?m)^(\s*host\s*=\s*).*$")
WINDOWED_LINE = re.compile(r"(?m)^(\s*WindowedMode\s*=\s*).*$")
SKIP_INTRO_LINE = re.compile(r"(?m)^(\s*SkipIntro\s*=\s*).*$")
NO_OPTICAL_LINE = re.compile(r"(?m)^(\s*NoOpticalDriveFix\s*=\s*).*$")


class PackageError(ValueError):
    """The package cannot be built with the supplied inputs."""


def size_label(size: int) -> str:
    value = max(0, int(size))
    if value < 1024:
        return f"{value} B"
    if value < 1024 * 1024:
        return f"{value / 1024:.1f} KB"
    return f"{value / (1024 * 1024):.1f} MB"


def validate_host(host: str) -> str:
    value = str(host or "").strip()
    if not value or not HOST_PATTERN.fullmatch(value):
        raise PackageError(
            f"invalid host {host!r}: use a hostname or IPv4 address without scheme, port or path"
        )
    return value


def write_ini(source: Path, host: str, destination: Path) -> None:
    text = source.read_text(encoding="utf-8-sig")
    updated, count = HOST_LINE.subn(lambda match: match.group(1) + host, text)
    if count == 0:
        raise PackageError(f"{source} has no host setting")
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(updated, encoding="utf-8")


def configure_widescreen_ini(text: str, game: str) -> str:
    updated, count = WINDOWED_LINE.subn(lambda match: match.group(1) + "1", text)
    if count == 0:
        raise PackageError(f"{game}: WidescreenFix.ini has no WindowedMode setting")
    updated, count = SKIP_INTRO_LINE.subn(lambda match: match.group(1) + "1", updated)
    if count == 0:
        raise PackageError(f"{game}: WidescreenFix.ini has no SkipIntro setting")
    if game == "u2":
        updated, count = NO_OPTICAL_LINE.subn(lambda match: match.group(1) + "1", updated)
        if count == 0:
            raise PackageError("u2: WidescreenFix.ini has no NoOpticalDriveFix setting")
    return updated


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _required_file(path: Path, description: str) -> Path:
    if not path.is_file():
        raise PackageError(f"missing {description}: {path}")
    return path


def _game_entries(
    game: str,
    *,
    host: str,
    asi_dir: Path,
    clients_dir: Path,
    widescreen_dir: Path,
    stage_dir: Path,
) -> dict[str, Path]:
    config = GAME_CONFIG[game]
    asi = _required_file(asi_dir / config["asi"], f"{game} ASI")
    ini_source = _required_file(
        clients_dir / config["clients"] / config["ini"], f"{game} INI template"
    )
    fix_scripts = widescreen_dir / config["fix_folder"] / "scripts"
    if not fix_scripts.is_dir():
        raise PackageError(f"missing widescreen scripts for {game}: {fix_scripts}")
    fix_ini = _required_file(
        fix_scripts / f"{config['fix_prefix']}.ini",
        f"{game} widescreen INI",
    )

    game_stage = stage_dir / config["folder"]
    game_stage.mkdir(parents=True, exist_ok=True)
    ini_target = game_stage / config["ini"]
    write_ini(ini_source, host, ini_target)

    entries: dict[str, Path] = {
        f"{config['folder']}/{config['asi']}": asi,
        f"{config['folder']}/{config['ini']}": ini_target,
    }

    scripts_stage = game_stage / "scripts"
    scripts_stage.mkdir(parents=True, exist_ok=True)
    for source in sorted(fix_scripts.iterdir()):
        if not source.is_file():
            continue
        target = scripts_stage / source.name
        if source.name == fix_ini.name:
            text = configure_widescreen_ini(
                source.read_text(encoding="utf-8-sig"), game
            )
            target.write_text(text, encoding="utf-8")
        else:
            target.write_bytes(source.read_bytes())
        entries[f"{config['folder']}/scripts/{source.name}"] = target
    return entries


def _shared_entries(
    *,
    templates_dir: Path,
    licenses_dir: Path,
    asi_loader: Path | None,
) -> dict[str, Path]:
    entries: dict[str, Path] = {}
    for name in (
        "INSTALAR.bat",
        "install.ps1",
        "DESINSTALAR.bat",
        "uninstall.ps1",
        "LICENCIAS.txt",
    ):
        entries[name] = _required_file(templates_dir / name, f"template {name}")

    gpl = licenses_dir / "GPL-3.0.txt"
    if gpl.is_file():
        entries["GPL-3.0.txt"] = gpl
    project_license = ROOT / "LICENSE"
    if project_license.is_file():
        entries["LICENSE-NFS-Online.txt"] = project_license

    if asi_loader is not None:
        entries["loader/dinput8.dll"] = _required_file(asi_loader, "ASI loader")
    return entries


def _readme_text(path: Path, host: str, version: str) -> str:
    return (
        path.read_text(encoding="utf-8")
        .replace("__HOST__", host)
        .replace("__VERSION__", version)
    )


def _write_archive(
    destination: Path,
    entries: dict[str, Path],
    *,
    readme: tuple[str, str] | None = None,
) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(
        destination,
        "w",
        compression=zipfile.ZIP_DEFLATED,
        compresslevel=6,
    ) as archive:
        for arcname, source in sorted(entries.items()):
            archive.write(source, arcname=arcname.replace("\\", "/"))
        if readme is not None:
            archive.writestr("LEEME.txt", readme[1].encode("utf-8"))


def _manifest_entry(
    download_id: str,
    title: str,
    description: str,
    game: str,
    version: str,
    archive: Path,
) -> dict[str, object]:
    size = archive.stat().st_size
    return {
        "id": download_id,
        "title": title,
        "description": description,
        "game": game,
        "version": version,
        "recommended": True,
        "available": True,
        "filename": archive.name,
        "size": size,
        "sizeLabel": size_label(size),
        "sha256": _sha256(archive),
    }


def package_clients(
    host: str,
    asi_dir: Path,
    out_dir: Path,
    version: str,
    *,
    asi_loader: Path | None = None,
    games: Sequence[str] = ("u2", "mw"),
    clients_dir: Path | None = None,
    widescreen_dir: Path | None = None,
    templates_dir: Path | None = None,
    licenses_dir: Path | None = None,
) -> dict[str, object]:
    host = validate_host(host)
    selected = tuple(dict.fromkeys(str(game).strip().casefold() for game in games))
    unknown = [game for game in selected if game not in GAME_CONFIG]
    if unknown:
        raise PackageError(f"unknown games: {', '.join(unknown)}")
    if not selected:
        raise PackageError("select at least one game")

    clients_root = Path(clients_dir) if clients_dir else DEFAULT_CLIENTS_DIR
    if widescreen_dir is not None:
        widescreen_root = Path(widescreen_dir)
    else:
        configured = os.environ.get("NFS_WIDESCREEN_DIR", "").strip()
        if not configured:
            raise PackageError("widescreen_dir is required")
        widescreen_root = Path(configured)
    templates_root = Path(templates_dir) if templates_dir else DEFAULT_TEMPLATES_DIR
    licenses_root = Path(licenses_dir) if licenses_dir else DEFAULT_LICENSES_DIR
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)

    readme_source = _required_file(templates_root / "LEEME.txt", "template LEEME.txt")
    readme_text = _readme_text(readme_source, host, version)
    shared = _shared_entries(
        templates_dir=templates_root,
        licenses_dir=licenses_root,
        asi_loader=Path(asi_loader) if asi_loader else None,
    )

    import tempfile

    downloads: list[dict[str, object]] = []
    with tempfile.TemporaryDirectory(prefix="nfs-client-package-") as temporary:
        stage = Path(temporary)
        per_game: dict[str, dict[str, Path]] = {}
        for game in selected:
            per_game[game] = _game_entries(
                game,
                host=host,
                asi_dir=Path(asi_dir),
                clients_dir=clients_root,
                widescreen_dir=widescreen_root,
                stage_dir=stage,
            )

        combined_entries = dict(shared)
        for entries in per_game.values():
            combined_entries.update(entries)
        combined_name = f"NFS-Online-Client-Pack-v{version}.zip"
        combined_path = out / combined_name
        _write_archive(combined_path, combined_entries, readme=("LEEME.txt", readme_text))
        downloads.append(
            _manifest_entry(
                "all",
                "NFS Online — Pack U2 + MW",
                "Cliente online y fix de pantalla borderless para Underground 2 y Most Wanted.",
                "all",
                version,
                combined_path,
            )
        )

        for game in selected:
            entries = dict(shared)
            entries.update(per_game[game])
            config = GAME_CONFIG[game]
            name = f"NFS-Online-{config['folder']}-Client-v{version}.zip"
            path = out / name
            _write_archive(path, entries, readme=("LEEME.txt", readme_text))
            downloads.append(
                _manifest_entry(
                    game,
                    f"NFS Online — {config['label']}",
                    f"Cliente online y fix de pantalla para {config['label']}.",
                    game,
                    version,
                    path,
                )
            )

    manifest_path = out / "manifest.json"
    temporary_manifest = out / f"manifest.json.{os.getpid()}.tmp"
    temporary_manifest.write_text(
        json.dumps({"downloads": downloads}, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    os.replace(temporary_manifest, manifest_path)
    return {"downloads": downloads}


def main(argv: Iterable[str] | None = None) -> int:
    artifacts = ROOT.parent / "NFS-Online-Artifacts"
    default_asi = artifacts / "vendor" / "nfs-online-client-current"
    default_loader = artifacts / "vendor" / "Ultimate-ASI-Loader" / "dinput8.dll"
    default_fixes = artifacts / "vendor" / "widescreen-fixes"
    default_out = artifacts / "downloads"
    default_version = "0.2.22"
    version_file = ROOT / "source" / "client-zig" / "VERSION"
    if version_file.is_file():
        default_version = version_file.read_text(encoding="utf-8").strip().splitlines()[-1]

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default=os.environ.get("NFS_WEB_PUBLIC_HOST", ""))
    parser.add_argument("--asi-dir", type=Path, default=default_asi)
    parser.add_argument("--out-dir", type=Path, default=default_out)
    parser.add_argument("--version", default=default_version)
    parser.add_argument("--asi-loader", type=Path, default=default_loader)
    parser.add_argument("--clients-dir", type=Path, default=DEFAULT_CLIENTS_DIR)
    parser.add_argument("--widescreen-dir", type=Path, default=default_fixes)
    parser.add_argument("--games", default="u2,mw")
    args = parser.parse_args(list(argv) if argv is not None else None)
    if not args.host:
        parser.error("--host is required (or set NFS_WEB_PUBLIC_HOST)")
    games = tuple(item.strip() for item in args.games.split(",") if item.strip())
    result = package_clients(
        args.host,
        args.asi_dir,
        args.out_dir,
        args.version,
        asi_loader=args.asi_loader if args.asi_loader.is_file() else None,
        games=games,
        clients_dir=args.clients_dir,
        widescreen_dir=args.widescreen_dir,
    )
    for entry in result["downloads"]:
        print(
            f"{entry['filename']}  {entry['sizeLabel']}  sha256={str(entry['sha256'])[:16]}…"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
