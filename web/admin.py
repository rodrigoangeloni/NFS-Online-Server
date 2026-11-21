"""Password-protected administration service for website invitations."""

from __future__ import annotations

import secrets
import time

from common.accounts import SQLiteAccountDatabase
from web.config import WebSettings
from web.db import Session, WebDatabase


TEMP_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"


def _temporary_password() -> str:
    raw = "".join(secrets.choice(TEMP_ALPHABET) for _ in range(8))
    return f"NFS-TMP-{raw[:4]}-{raw[4:]}"


class AdminAuthError(ValueError):
    """The admin password or session is invalid."""


class AdminService:
    def __init__(
        self,
        web_db: WebDatabase,
        settings: WebSettings,
        database: SQLiteAccountDatabase | None = None,
    ) -> None:
        self.web_db = web_db
        self.settings = settings
        self.database = database

    @staticmethod
    def hash_password(password: str) -> str:
        return SQLiteAccountDatabase.encode_password(password)

    @staticmethod
    def verify_password(password: str, encoded: str) -> bool:
        return SQLiteAccountDatabase.verify_password(password, encoded)

    def _current_password_hash(self) -> str:
        stored = self.web_db.get_admin_password_hash()
        if stored:
            return stored
        configured = str(self.settings.admin_password_hash or "").strip()
        if configured:
            self.web_db.set_admin_password_hash(configured)
            return configured
        return ""

    def login(self, password: str) -> tuple[str, str]:
        encoded = self._current_password_hash()
        if not encoded:
            raise AdminAuthError("admin_disabled")
        if not self.verify_password(str(password or ""), encoded):
            self.web_db.audit("admin", "admin.login_failed", {})
            raise AdminAuthError("bad_password")
        token, csrf = self.web_db.create_session(None, role="admin")
        self.web_db.audit("admin", "admin.login", {})
        return token, csrf

    def change_password(
        self,
        current_password: str,
        new_password: str,
    ) -> tuple[str, str]:
        encoded = self._current_password_hash()
        if not encoded or not self.verify_password(str(current_password or ""), encoded):
            self.web_db.audit("admin", "admin.password_failed", {})
            raise AdminAuthError("bad_password")
        if len(str(new_password or "")) < 10:
            raise ValueError("La clave nueva debe tener al menos 10 caracteres.")
        self.web_db.set_admin_password_hash(self.hash_password(str(new_password)))
        self.web_db.delete_admin_sessions()
        token, csrf = self.web_db.create_session(None, role="admin")
        self.web_db.audit("admin", "admin.password_changed", {})
        return token, csrf

    def me(self, token: str) -> Session | None:
        session = self.web_db.session(token)
        if session is None or session.role != "admin":
            return None
        return session

    def logout(self, token: str) -> None:
        self.web_db.audit("admin", "admin.logout", {})
        self.web_db.delete_session(token)

    def list_accounts(self) -> list[dict[str, object]]:
        if self.database is None:
            return []
        result: list[dict[str, object]] = []
        for record in self.database.accounts():
            security = self.web_db.get_security(record.account_id)
            result.append(
                {
                    "accountId": record.account_id,
                    "accountName": record.account_name,
                    "personas": list(record.personas),
                    "email": record.email,
                    "enabled": record.enabled,
                    "banned": record.banned,
                    "mustChangePassword": bool(security.get("must_change")),
                }
            )
        return result

    def reset_account_password(self, account_name: str) -> str:
        if self.database is None:
            raise ValueError("account database not configured")
        record = self.database.resolve_account(account_name)
        if record is None:
            raise ValueError("La cuenta no existe.")
        temporary = _temporary_password()
        self.database.set_password(record.account_name, temporary)
        self.web_db.set_must_change(
            record.account_id,
            time.time() + 24 * 3600,
        )
        self.web_db.delete_sessions_for_account(record.account_id)
        self.web_db.audit(
            "admin",
            "admin.account_reset",
            {"accountId": record.account_id, "accountName": record.account_name},
        )
        return temporary

    def list_invites(self) -> list[dict[str, object]]:
        now = time.time()
        result: list[dict[str, object]] = []
        for row in self.web_db.list_invites():
            expires_at = row.get("expires_at")
            revoked_at = row.get("revoked_at")
            uses = int(row.get("uses") or 0)
            max_uses = int(row.get("max_uses") or 0)
            if revoked_at is not None:
                status = "revoked"
            elif expires_at is not None and float(expires_at) <= now:
                status = "expired"
            elif uses >= max_uses:
                status = "used"
            else:
                status = "active"
            result.append(
                {
                    "codeHash": str(row.get("code_hash") or ""),
                    "code": str(row.get("code") or ""),
                    "label": str(row.get("label") or ""),
                    "maxUses": max_uses,
                    "uses": uses,
                    "expiresAt": float(expires_at) if expires_at is not None else None,
                    "createdBy": str(row.get("created_by") or ""),
                    "createdAt": float(row.get("created_at") or 0),
                    "revokedAt": float(revoked_at) if revoked_at is not None else None,
                    "status": status,
                }
            )
        return result

    def create_invite(
        self,
        label: str,
        max_uses: int,
        days: float,
    ) -> dict[str, object]:
        uses = int(max_uses)
        if not 1 <= uses <= 1000:
            raise ValueError("maxUses must be between 1 and 1000")
        duration = float(days)
        if not 0 <= duration <= 3650:
            raise ValueError("days must be between 0 and 3650")
        expires_at = time.time() + duration * 86400 if duration > 0 else None
        code = self.web_db.create_invite(
            str(label or "").strip(),
            uses,
            expires_at,
            "admin",
        )
        self.web_db.audit(
            "admin",
            "admin.invite_create",
            {"label": str(label or ""), "maxUses": uses, "days": duration},
        )
        for invite in self.list_invites():
            if invite["code"] == code:
                return invite
        return {"code": code}

    def revoke_invite(self, code_hash: str) -> None:
        self.web_db.revoke_invite(code_hash)
        self.web_db.audit("admin", "admin.invite_revoke", {"codeHash": code_hash})
