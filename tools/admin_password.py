"""Generate the PBKDF2 hash for NFS_WEB_ADMIN_PASSWORD_HASH."""

from __future__ import annotations

import getpass
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "server"))

from common.accounts import SQLiteAccountDatabase  # noqa: E402


def main() -> int:
    password = getpass.getpass("Nueva clave de administrador: ")
    confirmation = getpass.getpass("Repetir clave: ")
    if password != confirmation:
        print("Las claves no coinciden.", file=sys.stderr)
        return 1
    if len(password) < 10:
        print("La clave debe tener al menos 10 caracteres.", file=sys.stderr)
        return 1
    print(SQLiteAccountDatabase.encode_password(password))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
