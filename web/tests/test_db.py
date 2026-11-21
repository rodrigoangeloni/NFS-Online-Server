from __future__ import annotations

import sqlite3
from pathlib import Path

from web.db import WebDatabase


def test_session_token_is_hashed_and_expires(tmp_path: Path) -> None:
    db = WebDatabase(tmp_path / "accounts.sqlite3")
    db.ensure_schema()
    token, csrf = db.create_session(7, now=1000.0)
    session = db.session(token, now=1001.0)
    assert session is not None
    assert session.account_id == 7
    assert session.csrf_token == csrf
    with sqlite3.connect(db.path) as conn:
        stored = conn.execute("SELECT session_hash FROM web_sessions").fetchone()[0]
    assert stored != token
    assert db.session(token, now=1000.0 + 8 * 24 * 3600) is None


def test_invite_is_single_use(tmp_path: Path) -> None:
    db = WebDatabase(tmp_path / "accounts.sqlite3")
    db.ensure_schema()
    code = db.create_invite("friends", 1, None, "admin")
    assert db.consume_invite(code) is True
    assert db.consume_invite(code) is False


def test_invite_expiry_and_refund(tmp_path: Path) -> None:
    db = WebDatabase(tmp_path / "accounts.sqlite3")
    db.ensure_schema()
    code = db.create_invite("short", 1, 2000.0, "admin")
    assert db.consume_invite(code, now=2001.0) is False
    assert db.consume_invite(code, now=1999.0) is True
    db.refund_invite(code)
    assert db.consume_invite(code, now=1999.0) is True


def test_preferences_default_and_roundtrip(tmp_path: Path) -> None:
    db = WebDatabase(tmp_path / "accounts.sqlite3")
    db.ensure_schema()
    assert db.get_preferences(9).appear_online is True
    db.set_preferences(9, appear_online=False, challenge_series_assist=False)
    saved = db.get_preferences(9)
    assert saved.appear_online is False
    assert saved.challenge_series_assist is False


def test_visibility_events_keep_chronological_order(tmp_path: Path) -> None:
    db = WebDatabase(tmp_path / "accounts.sqlite3")
    db.ensure_schema()
    db.queue_visibility("First")
    db.queue_visibility("Second")
    events = db.visibility_events()
    assert [event["source_persona"] for event in events] == ["First", "Second"]
