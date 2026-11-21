"""Password-protected administration service for website invitations."""

from __future__ import annotations

import time

from common.accounts import SQLiteAccountDatabase
from web.config import WebSettings
from web.db import Session, WebDatabase


class AdminAuthError(ValueError):
    """The admin password or session is invalid."""


class AdminService:
    def __init__(self, web_db: WebDatabase, settings: WebSettings) -> None:
        self.web_db = web_db
        self.settings = settings

    @staticmethod
    def hash_password(password: str) -> str:
        return SQLiteAccountDatabase.encode_password(password)

    @staticmethod
    def verify_password(password: str, encoded: str) -> bool:
        return SQLiteAccountDatabase.verify_password(password, encoded)

    def login(self, password: str) -> tuple[str, str]:
        encoded = str(self.settings.admin_password_hash or "").strip()
        if not encoded:
            raise AdminAuthError("admin_disabled")
        if not self.verify_password(str(password or ""), encoded):
            self.web_db.audit("admin", "admin.login_failed", {})
            raise AdminAuthError("bad_password")
        token, csrf = self.web_db.create_session(None, role="admin")
        self.web_db.audit("admin", "admin.login", {})
        return token, csrf

    def me(self, token: str) -> Session | None:
        session = self.web_db.session(token)
        if session is None or session.role != "admin":
            return None
        return session

    def logout(self, token: str) -> None:
        self.web_db.audit("admin", "admin.logout", {})
        self.web_db.delete_session(token)

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
