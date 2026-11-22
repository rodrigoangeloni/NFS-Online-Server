from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import zipfile

import pytest

from tools.package_clients import PackageError, package_clients, write_ini


def fake_inputs(tmp_path: Path) -> dict[str, Path]:
    asi = tmp_path / "asi"
    asi.mkdir()
    (asi / "net_u2.asi").write_bytes(b"u2-asi")
    (asi / "net_mw.asi").write_bytes(b"mw-asi")

    clients = tmp_path / "clients"
    for folder, name, port in (
        ("underground2", "net_u2.ini", "20921"),
        ("most-wanted", "net_mw.ini", "30921"),
    ):
        directory = clients / folder
        directory.mkdir(parents=True)
        (directory / name).write_text(
            "[network]\n"
            "host = 127.0.0.1\n"
            f"bootstrap_port = {port}\n"
            "\n[lan]\n"
            "host = 127.0.0.1\n",
            encoding="utf-8",
        )

    fixes = tmp_path / "fixes"
    for folder, prefix in (
        ("NFSUnderground2", "NFSUnderground2.WidescreenFix"),
        ("NFSMostWanted", "NFSMostWanted.WidescreenFix"),
    ):
        scripts = fixes / folder / "scripts"
        scripts.mkdir(parents=True)
        (scripts / f"{prefix}.asi").write_bytes(b"fix-asi")
        (scripts / f"{prefix}.ini").write_text(
            "[MISC]\n"
            "SkipIntro = 0\n"
            "WindowedMode = 3\n"
            "NoOpticalDriveFix = 0\n",
            encoding="utf-8",
        )
        (scripts / f"{prefix}.dat").write_bytes(b"fix-data")

    loader = tmp_path / "dinput8.dll"
    loader.write_bytes(b"loader")
    return {
        "asi": asi,
        "clients": clients,
        "fixes": fixes,
        "loader": loader,
    }


def test_write_ini_replaces_all_hosts(tmp_path: Path) -> None:
    source = tmp_path / "net_u2.ini"
    source.write_text(
        "[network]\nhost = 127.0.0.1\n\n[lan]\nhost = 127.0.0.1\n",
        encoding="utf-8",
    )
    destination = tmp_path / "out.ini"
    write_ini(source, "192.0.2.37", destination)
    text = destination.read_text(encoding="utf-8")
    assert "host = 192.0.2.37" in text
    assert "127.0.0.1" not in text


def test_package_contains_both_games_fix_and_manifest(tmp_path: Path) -> None:
    inputs = fake_inputs(tmp_path)
    out = tmp_path / "out"
    result = package_clients(
        "192.0.2.37",
        inputs["asi"],
        out,
        "0.2.22",
        asi_loader=inputs["loader"],
        clients_dir=inputs["clients"],
        widescreen_dir=inputs["fixes"],
    )

    pack = out / "NFS-Online-Client-Pack-v0.2.22.zip"
    assert pack.is_file()
    with zipfile.ZipFile(pack) as archive:
        names = set(archive.namelist())
        assert "INSTALAR.bat" in names
        assert "LEEME.txt" in names
        assert "host.txt" in names
        assert "loader/dinput8.dll" in names
        assert "U2/net_u2.asi" in names
        assert "U2/scripts/NFSUnderground2.WidescreenFix.ini" in names
        assert "MW/net_mw.asi" in names
        assert "MW/scripts/NFSMostWanted.WidescreenFix.ini" in names
        assert archive.read("host.txt").decode().strip() == "192.0.2.37"
        u2_ini = archive.read("U2/scripts/NFSUnderground2.WidescreenFix.ini").decode()
        mw_ini = archive.read("MW/scripts/NFSMostWanted.WidescreenFix.ini").decode()
        assert "WindowedMode = 1" in u2_ini
        assert "SkipIntro = 1" in u2_ini
        assert "NoOpticalDriveFix = 1" in u2_ini
        assert "WindowedMode = 1" in mw_ini
        assert "SkipIntro = 1" in mw_ini
        client_ini = archive.read("U2/net_u2.ini").decode()
        assert "host = 192.0.2.37" in client_ini
        assert "127.0.0.1" not in client_ini
        readme = archive.read("LEEME.txt").decode()
        assert "192.0.2.37" in readme
        assert "NFS-Online" in readme
        installer = archive.read("install.ps1").decode()
        assert "host.txt" in installer
        assert "Set-IniHost" in installer

    manifest = json.loads((out / "manifest.json").read_text(encoding="utf-8"))
    ids = [entry["id"] for entry in manifest["downloads"]]
    assert ids == ["all", "u2", "mw"]
    for entry in manifest["downloads"]:
        assert len(entry["sha256"]) == 64
        assert entry["size"] > 0
        assert entry["available"] is True
        assert (out / entry["filename"]).is_file()
    assert result["downloads"][0]["id"] == "all"


def test_per_game_zip_contains_only_its_game(tmp_path: Path) -> None:
    inputs = fake_inputs(tmp_path)
    out = tmp_path / "out"
    package_clients(
        "nfs.example.com",
        inputs["asi"],
        out,
        "0.2.22",
        asi_loader=inputs["loader"],
        clients_dir=inputs["clients"],
        widescreen_dir=inputs["fixes"],
    )
    with zipfile.ZipFile(out / "NFS-Online-U2-Client-v0.2.22.zip") as archive:
        names = archive.namelist()
        assert any(name.startswith("U2/") for name in names)
        assert not any(name.startswith("MW/") for name in names)
        assert "INSTALAR.bat" in names
        assert "host.txt" in names


def test_missing_asi_fails_with_clear_message(tmp_path: Path) -> None:
    inputs = fake_inputs(tmp_path)
    (inputs["asi"] / "net_mw.asi").unlink()
    with pytest.raises(PackageError, match="net_mw.asi"):
        package_clients(
            "nfs.example.com",
            inputs["asi"],
            tmp_path / "out",
            "0.2.22",
            clients_dir=inputs["clients"],
            widescreen_dir=inputs["fixes"],
        )


def test_invalid_host_is_rejected(tmp_path: Path) -> None:
    inputs = fake_inputs(tmp_path)
    with pytest.raises(PackageError):
        package_clients(
            "http://bad host/",
            inputs["asi"],
            tmp_path / "out",
            "0.2.22",
            clients_dir=inputs["clients"],
            widescreen_dir=inputs["fixes"],
        )


@pytest.mark.skipif(sys.platform != "win32", reason="install.ps1 is PowerShell")
def test_installer_forces_pack_host_on_fake_games(tmp_path: Path) -> None:
    inputs = fake_inputs(tmp_path)
    out = tmp_path / "out"
    package_clients(
        "nfs.example.com",
        inputs["asi"],
        out,
        "0.2.24",
        asi_loader=inputs["loader"],
        clients_dir=inputs["clients"],
        widescreen_dir=inputs["fixes"],
    )

    pack_dir = tmp_path / "pack"
    with zipfile.ZipFile(out / "NFS-Online-Client-Pack-v0.2.24.zip") as archive:
        archive.extractall(pack_dir)

    u2 = tmp_path / "u2"
    mw = tmp_path / "mw"
    u2.mkdir()
    mw.mkdir()
    (u2 / "SPEED2.EXE").write_bytes(b"")
    (mw / "speed.exe").write_bytes(b"")
    old_ini = "[network]\nhost = 192.0.2.37\n\n[lan]\nhost = 192.0.2.37\n"
    (u2 / "net_u2.ini").write_text(old_ini, encoding="utf-8")
    (mw / "net_mw.ini").write_text(old_ini, encoding="utf-8")

    result = subprocess.run(
        [
            "powershell.exe",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(pack_dir / "install.ps1"),
            "-NoElevate",
            "-NoPause",
            "-U2Path",
            str(u2),
            "-MWPath",
            str(mw),
        ],
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    for ini in (u2 / "net_u2.ini", mw / "net_mw.ini"):
        text = ini.read_text(encoding="utf-8")
        assert "host = nfs.example.com" in text
        assert "192.0.2.37" not in text
