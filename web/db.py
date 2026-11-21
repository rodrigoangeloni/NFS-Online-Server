"""Durable website state stored beside the shared game accounts database."""

from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import secrets
import sqlite3
import time
from typing import Iterator, Mapping


DEFAULT_SESSION_SECONDS = 7 * 24 * 3600
INVITE_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"

SCHEMA = """
CREATE TABLE IF NOT EXISTS web_sessions (
    session_hash TEXT PRIMARY KEY,
    account_id INTEGER,
    role TEXT NOT NULL DEFAULT 'player',
    csrf_token TEXT NOT NULL,
    created_at REAL NOT NULL,
    expires_at REAL NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_web_sessions_account
    ON web_sessions(account_id);

CREATE TABLE IF NOT EXISTS web_account_preferences (
    account_id INTEGER PRIMARY KEY,
    appear_online INTEGER NOT NULL DEFAULT 1 CHECK(appear_online IN (0, 1)),
    challenge_series_assist INTEGER NOT NULL DEFAULT 1
        CHECK(challenge_series_assist IN (0, 1)),
    updated_at REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS web_account_security (
    account_id INTEGER PRIMARY KEY,
    recovery_code_hash TEXT NOT NULL DEFAULT '',
    must_change INTEGER NOT NULL DEFAULT 0 CHECK(must_change IN (0, 1)),
    temp_expires_at REAL,
    updated_at REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS web_admin_credentials (
    id INTEGER PRIMARY KEY CHECK(id = 1),
    password_hash TEXT NOT NULL,
    updated_at REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS web_invites (
    code_hash TEXT PRIMARY KEY,
    code TEXT NOT NULL DEFAULT '',
    label TEXT NOT NULL DEFAULT '',
    max_uses INTEGER NOT NULL CHECK(max_uses > 0),
    uses INTEGER NOT NULL DEFAULT 0 CHECK(uses >= 0),
    expires_at REAL,
    created_by TEXT NOT NULL DEFAULT '',
    created_at REAL NOT NULL,
    revoked_at REAL
);
CREATE INDEX IF NOT EXISTS idx_web_invites_created
    ON web_invites(created_at DESC);

CREATE TABLE IF NOT EXISTS web_audit_log (
    event_id INTEGER PRIMARY KEY AUTOINCREMENT,
    actor TEXT NOT NULL,
    action TEXT NOT NULL,
    detail_json TEXT NOT NULL DEFAULT '{}',
    created_at REAL NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_web_audit_created
    ON web_audit_log(event_id DESC);

CREATE TABLE IF NOT EXISTS web_social_events (
    event_id INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at REAL NOT NULL,
    source_persona TEXT NOT NULL,
    target_persona TEXT NOT NULL DEFAULT '',
    action TEXT NOT NULL,
    payload_json TEXT NOT NULL DEFAULT '{}',
    status TEXT NOT NULL DEFAULT 'pending',
    result_json TEXT NOT NULL DEFAULT '',
    processed_at REAL
);
CREATE INDEX IF NOT EXISTS idx_web_social_events_pending
    ON web_social_events(status, event_id);

CREATE TABLE IF NOT EXISTS web_social_presence (
    session_hash TEXT PRIMARY KEY,
    persona TEXT NOT NULL,
    expires_at REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS web_social_messages (
    message_id INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at REAL NOT NULL,
    source_persona TEXT NOT NULL,
    target_persona TEXT NOT NULL,
    body TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_web_social_messages_target
    ON web_social_messages(target_persona COLLATE NOCASE, message_id);
"""


@dataclass(frozen=True)
class Session:
    token_hash: str
    account_id: int | None
    role: str
    csrf_token: str
    expires_at: float


@dataclass(frozen=True)
class Preferences:
    appear_online: bool
    challenge_series_assist: bool


def _hash_token(token: str) -> str:
    return hashlib.sha256(str(token or "").encode("utf-8")).hexdigest()


def _invite_code() -> str:
    raw = "".join(secrets.choice(INVITE_ALPHABET) for _ in range(8))
    return f"NFS-{raw[:4]}-{raw[4:]}"


def _normalize_invite(code: str) -> str:
    return str(code or "").strip().upper()


class WebDatabase:
    def __init__(
        self,
        path: str | Path,
        *,
        session_seconds: int = DEFAULT_SESSION_SECONDS,
        busy_timeout_ms: int = 5_000,
    ) -> None:
        self.path = Path(path)
        self.session_seconds = int(session_seconds)
        self.busy_timeout_ms = int(busy_timeout_ms)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.ensure_schema()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(
            self.path,
            timeout=max(0.0, self.busy_timeout_ms / 1000.0),
            isolation_level=None,
        )
        connection.row_factory = sqlite3.Row
        connection.execute(f"PRAGMA busy_timeout={self.busy_timeout_ms}")
        connection.execute("PRAGMA foreign_keys=ON")
        return connection

    @contextmanager
    def connect(self) -> Iterator[sqlite3.Connection]:
        connection = self._connect()
        try:
            yield connection
        finally:
            connection.close()

    def ensure_schema(self) -> None:
        with self.connect() as connection:
            connection.execute("PRAGMA journal_mode=WAL")
            connection.executescript(SCHEMA)
            columns = {
                str(row["name"])
                for row in connection.execute("PRAGMA table_info(web_invites)").fetchall()
            }
            if "code" not in columns:
                connection.execute(
                    "ALTER TABLE web_invites ADD COLUMN code TEXT NOT NULL DEFAULT ''"
                )

    def create_session(
        self,
        account_id: int | None,
        *,
        role: str = "player",
        now: float | None = None,
    ) -> tuple[str, str]:
        timestamp = time.time() if now is None else float(now)
        token = secrets.token_urlsafe(32)
        csrf = secrets.token_urlsafe(32)
        with self.connect() as connection:
            connection.execute(
                """
                INSERT INTO web_sessions(
                    session_hash, account_id, role, csrf_token, created_at, expires_at
                ) VALUES(?, ?, ?, ?, ?, ?)
                """,
                (
                    _hash_token(token),
                    account_id,
                    role,
                    csrf,
                    timestamp,
                    timestamp + self.session_seconds,
                ),
            )
        return token, csrf

    def session(self, token: str, *, now: float | None = None) -> Session | None:
        if not token:
            return None
        timestamp = time.time() if now is None else float(now)
        token_hash = _hash_token(token)
        with self.connect() as connection:
            row = connection.execute(
                "SELECT * FROM web_sessions WHERE session_hash=?",
                (token_hash,),
            ).fetchone()
            if row is None:
                return None
            if float(row["expires_at"]) <= timestamp:
                connection.execute(
                    "DELETE FROM web_sessions WHERE session_hash=?",
                    (token_hash,),
                )
                return None
            return Session(
                token_hash=token_hash,
                account_id=(
                    int(row["account_id"]) if row["account_id"] is not None else None
                ),
                role=str(row["role"]),
                csrf_token=str(row["csrf_token"]),
                expires_at=float(row["expires_at"]),
            )

    def delete_session(self, token: str) -> None:
        with self.connect() as connection:
            connection.execute(
                "DELETE FROM web_sessions WHERE session_hash=?",
                (_hash_token(token),),
            )

    def get_preferences(self, account_id: int) -> Preferences:
        with self.connect() as connection:
            row = connection.execute(
                "SELECT * FROM web_account_preferences WHERE account_id=?",
                (int(account_id),),
            ).fetchone()
        if row is None:
            return Preferences(appear_online=True, challenge_series_assist=True)
        return Preferences(
            appear_online=bool(row["appear_online"]),
            challenge_series_assist=bool(row["challenge_series_assist"]),
        )

    def set_preferences(
        self,
        account_id: int,
        *,
        appear_online: bool,
        challenge_series_assist: bool,
        now: float | None = None,
    ) -> None:
        timestamp = time.time() if now is None else float(now)
        with self.connect() as connection:
            connection.execute(
                """
                INSERT INTO web_account_preferences(
                    account_id, appear_online, challenge_series_assist, updated_at
                ) VALUES(?, ?, ?, ?)
                ON CONFLICT(account_id) DO UPDATE SET
                    appear_online=excluded.appear_online,
                    challenge_series_assist=excluded.challenge_series_assist,
                    updated_at=excluded.updated_at
                """,
                (
                    int(account_id),
                    int(bool(appear_online)),
                    int(bool(challenge_series_assist)),
                    timestamp,
                ),
            )

    def get_security(self, account_id: int) -> dict[str, object]:
        with self.connect() as connection:
            row = connection.execute(
                "SELECT * FROM web_account_security WHERE account_id=?",
                (int(account_id),),
            ).fetchone()
        if row is None:
            return {
                "recovery_code_hash": "",
                "must_change": False,
                "temp_expires_at": None,
            }
        return {
            "recovery_code_hash": str(row["recovery_code_hash"] or ""),
            "must_change": bool(row["must_change"]),
            "temp_expires_at": (
                float(row["temp_expires_at"])
                if row["temp_expires_at"] is not None
                else None
            ),
        }

    def set_recovery_code_hash(
        self,
        account_id: int,
        code_hash: str,
        *,
        now: float | None = None,
    ) -> None:
        timestamp = time.time() if now is None else float(now)
        with self.connect() as connection:
            connection.execute(
                """
                INSERT INTO web_account_security(
                    account_id, recovery_code_hash, must_change, temp_expires_at, updated_at
                ) VALUES(?, ?, 0, NULL, ?)
                ON CONFLICT(account_id) DO UPDATE SET
                    recovery_code_hash=excluded.recovery_code_hash,
                    updated_at=excluded.updated_at
                """,
                (int(account_id), str(code_hash or ""), timestamp),
            )

    def set_must_change(
        self,
        account_id: int,
        expires_at: float,
        *,
        now: float | None = None,
    ) -> None:
        timestamp = time.time() if now is None else float(now)
        with self.connect() as connection:
            connection.execute(
                """
                INSERT INTO web_account_security(
                    account_id, recovery_code_hash, must_change, temp_expires_at, updated_at
                ) VALUES(?, '', 1, ?, ?)
                ON CONFLICT(account_id) DO UPDATE SET
                    must_change=1,
                    temp_expires_at=excluded.temp_expires_at,
                    updated_at=excluded.updated_at
                """,
                (int(account_id), float(expires_at), timestamp),
            )

    def clear_must_change(
        self,
        account_id: int,
        *,
        now: float | None = None,
    ) -> None:
        timestamp = time.time() if now is None else float(now)
        with self.connect() as connection:
            connection.execute(
                """
                UPDATE web_account_security
                   SET must_change=0, temp_expires_at=NULL, updated_at=?
                 WHERE account_id=?
                """,
                (timestamp, int(account_id)),
            )

    def get_admin_password_hash(self) -> str:
        with self.connect() as connection:
            row = connection.execute(
                "SELECT password_hash FROM web_admin_credentials WHERE id=1"
            ).fetchone()
        return str(row["password_hash"] or "") if row is not None else ""

    def set_admin_password_hash(
        self,
        password_hash: str,
        *,
        now: float | None = None,
    ) -> None:
        timestamp = time.time() if now is None else float(now)
        with self.connect() as connection:
            connection.execute(
                """
                INSERT INTO web_admin_credentials(id, password_hash, updated_at)
                VALUES(1, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    password_hash=excluded.password_hash,
                    updated_at=excluded.updated_at
                """,
                (str(password_hash), timestamp),
            )

    def delete_sessions_for_account(
        self,
        account_id: int,
        *,
        keep_token_hash: str | None = None,
    ) -> None:
        with self.connect() as connection:
            if keep_token_hash:
                connection.execute(
                    "DELETE FROM web_sessions WHERE account_id=? AND session_hash<>?",
                    (int(account_id), str(keep_token_hash)),
                )
            else:
                connection.execute(
                    "DELETE FROM web_sessions WHERE account_id=?",
                    (int(account_id),),
                )

    def delete_admin_sessions(self) -> None:
        with self.connect() as connection:
            connection.execute("DELETE FROM web_sessions WHERE role='admin'")

    def create_invite(
        self,
        label: str,
        max_uses: int,
        expires_at: float | None,
        created_by: str,
        *,
        now: float | None = None,
    ) -> str:
        uses = int(max_uses)
        if uses <= 0:
            raise ValueError("max_uses must be positive")
        timestamp = time.time() if now is None else float(now)
        code = _invite_code()
        with self.connect() as connection:
            connection.execute(
                """
                INSERT INTO web_invites(
                    code_hash, code, label, max_uses, uses, expires_at,
                    created_by, created_at, revoked_at
                ) VALUES(?, ?, ?, ?, 0, ?, ?, ?, NULL)
                """,
                (
                    _hash_token(_normalize_invite(code)),
                    code,
                    str(label or "").strip(),
                    uses,
                    None if expires_at is None else float(expires_at),
                    str(created_by or ""),
                    timestamp,
                ),
            )
        return code

    def consume_invite(self, code: str, *, now: float | None = None) -> bool:
        timestamp = time.time() if now is None else float(now)
        code_hash = _hash_token(_normalize_invite(code))
        with self.connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            try:
                row = connection.execute(
                    "SELECT * FROM web_invites WHERE code_hash=?",
                    (code_hash,),
                ).fetchone()
                if row is None:
                    connection.rollback()
                    return False
                uses = int(row["uses"])
                if (
                    row["revoked_at"] is not None
                    or uses >= int(row["max_uses"])
                    or (
                        row["expires_at"] is not None
                        and float(row["expires_at"]) <= timestamp
                    )
                ):
                    connection.rollback()
                    return False
                connection.execute(
                    "UPDATE web_invites SET uses=uses+1 WHERE code_hash=?",
                    (code_hash,),
                )
                connection.commit()
                return True
            except Exception:
                connection.rollback()
                raise

    def refund_invite(self, code: str) -> None:
        code_hash = _hash_token(_normalize_invite(code))
        with self.connect() as connection:
            connection.execute(
                "UPDATE web_invites SET uses=MAX(0, uses-1) WHERE code_hash=?",
                (code_hash,),
            )

    def list_invites(self) -> list[dict[str, object]]:
        with self.connect() as connection:
            rows = connection.execute(
                "SELECT * FROM web_invites ORDER BY created_at DESC"
            ).fetchall()
        return [dict(row) for row in rows]

    def revoke_invite(
        self,
        code_hash: str,
        *,
        now: float | None = None,
    ) -> None:
        timestamp = time.time() if now is None else float(now)
        with self.connect() as connection:
            connection.execute(
                "UPDATE web_invites SET revoked_at=? WHERE code_hash=? AND revoked_at IS NULL",
                (timestamp, str(code_hash)),
            )

    def visibility_events(self, limit: int = 20) -> list[dict[str, object]]:
        size = max(1, int(limit))
        with self.connect() as connection:
            rows = connection.execute(
                """
                SELECT * FROM web_social_events
                 WHERE action='visibility'
                 ORDER BY event_id DESC
                 LIMIT ?
                """,
                (size,),
            ).fetchall()
        return [dict(row) for row in reversed(rows)]

    def queue_visibility(
        self,
        source_persona: str,
        target_persona: str = "",
        *,
        payload: Mapping[str, object] | None = None,
        now: float | None = None,
    ) -> int:
        timestamp = time.time() if now is None else float(now)
        with self.connect() as connection:
            cursor = connection.execute(
                """
                INSERT INTO web_social_events(
                    created_at, source_persona, target_persona,
                    action, payload_json, status
                ) VALUES(?, ?, ?, 'visibility', ?, 'pending')
                """,
                (
                    timestamp,
                    str(source_persona or ""),
                    str(target_persona or ""),
                    json.dumps(dict(payload or {}), sort_keys=True),
                ),
            )
            return int(cursor.lastrowid)

    def audit(
        self,
        actor: str,
        action: str,
        detail: Mapping[str, object],
        *,
        now: float | None = None,
    ) -> None:
        timestamp = time.time() if now is None else float(now)
        with self.connect() as connection:
            connection.execute(
                """
                INSERT INTO web_audit_log(actor, action, detail_json, created_at)
                VALUES(?, ?, ?, ?)
                """,
                (
                    str(actor or ""),
                    str(action or ""),
                    json.dumps(dict(detail), sort_keys=True),
                    timestamp,
                ),
            )
