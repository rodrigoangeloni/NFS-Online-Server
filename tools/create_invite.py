"""Create a single website invitation code."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "server"))

from web.config import load_settings  # noqa: E402
from web.db import WebDatabase  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--label", default="", help="internal label")
    parser.add_argument("--uses", type=int, default=1, help="maximum uses")
    parser.add_argument("--days", type=float, default=0.0, help="expiry in days (0 = never)")
    parser.add_argument("--created-by", default="cli")
    args = parser.parse_args()

    settings = load_settings()
    database = WebDatabase(settings.account_db, session_seconds=settings.session_seconds)
    expires_at = None
    if args.days > 0:
        expires_at = time.time() + args.days * 86400
    code = database.create_invite(
        args.label,
        args.uses,
        expires_at,
        args.created_by,
    )
    print(code)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
