"""Serve pre-built client packages listed in ``manifest.json``."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class DownloadNotFound(KeyError):
    """The requested download is not present in the manifest or on disk."""


def _size_label(size: int) -> str:
    value = max(0, int(size))
    if value < 1024:
        return f"{value} B"
    if value < 1024 * 1024:
        return f"{value / 1024:.1f} KB"
    return f"{value / (1024 * 1024):.1f} MB"


class DownloadService:
    def __init__(self, downloads_dir: str | Path) -> None:
        self.downloads_dir = Path(downloads_dir)

    @property
    def manifest_path(self) -> Path:
        return self.downloads_dir / "manifest.json"

    def manifest(self) -> dict[str, Any]:
        try:
            value = json.loads(self.manifest_path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return {"downloads": []}
        if not isinstance(value, dict):
            return {"downloads": []}
        entries = value.get("downloads")
        if not isinstance(entries, list):
            return {"downloads": []}
        return value

    def _safe_path(self, filename: object) -> Path:
        text = str(filename or "").strip()
        if not text:
            raise DownloadNotFound("missing filename")
        root = self.downloads_dir.resolve()
        candidate = (self.downloads_dir / text).resolve()
        if candidate != root and root not in candidate.parents:
            raise DownloadNotFound("filename escapes downloads directory")
        return candidate

    def _entry(self, raw: object) -> dict[str, Any] | None:
        if not isinstance(raw, dict):
            return None
        download_id = str(raw.get("id") or "").strip()
        if not download_id:
            return None
        entry = dict(raw)
        entry["id"] = download_id
        entry["downloadUrl"] = f"/downloads/{download_id}"
        try:
            path = self._safe_path(raw.get("filename"))
            available = path.is_file()
        except DownloadNotFound:
            available = False
            path = None
        entry["available"] = bool(available)
        try:
            size = int(raw.get("size") or 0)
        except (TypeError, ValueError):
            size = 0
        if available and path is not None:
            try:
                size = path.stat().st_size
            except OSError:
                entry["available"] = False
        entry["size"] = size
        entry["sizeLabel"] = _size_label(size)
        return entry

    def connect_payload(self, public_host: str) -> dict[str, Any]:
        downloads: list[dict[str, Any]] = []
        for raw in self.manifest().get("downloads", []):
            entry = self._entry(raw)
            if entry is not None:
                downloads.append(entry)
        return {
            "serverAddress": str(public_host or ""),
            "downloads": downloads,
        }

    def resolve(self, download_id: str) -> Path:
        wanted = str(download_id or "").strip()
        for raw in self.manifest().get("downloads", []):
            if not isinstance(raw, dict):
                continue
            if str(raw.get("id") or "").strip() != wanted:
                continue
            path = self._safe_path(raw.get("filename"))
            if not path.is_file():
                raise DownloadNotFound(wanted)
            return path
        raise DownloadNotFound(wanted)
