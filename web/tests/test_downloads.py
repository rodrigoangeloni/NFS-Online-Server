from __future__ import annotations

import json
from pathlib import Path

import pytest

from web.downloads import DownloadNotFound, DownloadService


def test_connect_payload_exposes_public_host_and_downloads(
    downloads: DownloadService,
) -> None:
    payload = downloads.connect_payload("nfs.example.com")
    assert payload["serverAddress"] == "nfs.example.com"
    assert payload["downloads"][0]["id"] == "all"
    assert payload["downloads"][0]["available"] is True
    assert payload["downloads"][0]["downloadUrl"] == "/downloads/all"


def test_resolve_rejects_path_traversal(downloads: DownloadService) -> None:
    with pytest.raises(DownloadNotFound):
        downloads.resolve("../../etc/passwd")


def test_missing_file_marks_download_unavailable(
    downloads: DownloadService,
) -> None:
    (downloads.downloads_dir / "NFS-Online-Client-Pack-v0.2.22.zip").unlink()
    payload = downloads.connect_payload("nfs.example.com")
    assert payload["downloads"][0]["available"] is False
    with pytest.raises(DownloadNotFound):
        downloads.resolve("all")


def test_manifest_filename_cannot_escape_directory(
    downloads: DownloadService,
) -> None:
    manifest = json.loads((downloads.downloads_dir / "manifest.json").read_text())
    manifest["downloads"][0]["filename"] = "../../outside.zip"
    (downloads.downloads_dir / "manifest.json").write_text(json.dumps(manifest))
    payload = downloads.connect_payload("nfs.example.com")
    assert payload["downloads"][0]["available"] is False


def test_invalid_manifest_returns_empty_list(tmp_path: Path) -> None:
    service = DownloadService(tmp_path)
    (tmp_path / "manifest.json").write_text("{not json", encoding="utf-8")
    assert service.manifest()["downloads"] == []
    assert service.connect_payload("host")["downloads"] == []
