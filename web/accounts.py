"""Account registration, login and preferences for the community site."""

from __future__ import annotations

from dataclasses import dataclass
import re

from common.accounts import (
    SharedAccountExistsError,
    SharedAccountRecord,
    SharedPersonaExistsError,
    SQLiteAccountDatabase,
)
from web.config import WebSettings
from web.db import Preferences, Session, WebDatabase


NAME_PATTERN = re.compile(r"^[A-Za-z0-9_-]{3,24}$")


class AccountError(ValueError):
    """Base class for website account errors."""


class InviteError(AccountError):
    """The supplied invitation is missing, expired or already used."""


class RegistrationError(AccountError):
    """The registration payload is invalid or could not be stored."""


class AuthError(AccountError):
    """Authentication failed or the session is not valid."""

    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


@dataclass(frozen=True)
class RegisterPayload:
    account_name: str
    email: str
    password: str
    persona: str
    country_code: str
    appear_online: bool
    challenge_series_assist: bool
    invite_code: str


@dataclass(frozen=True)
class AccountView:
    account_id: int
    account_name: str
    email: str
    personas: tuple[str, ...]
    primary_persona: str
    appear_online: bool
    challenge_series_assist: bool


class AccountService:
    def __init__(
        self,
        database: SQLiteAccountDatabase,
        web_db: WebDatabase,
        settings: WebSettings,
    ) -> None:
        self.database = database
        self.web_db = web_db
        self.settings = settings

    @staticmethod
    def _clean_name(value: str) -> str:
        return str(value or "").strip()

    def _validate(self, payload: RegisterPayload) -> tuple[str, str, str, str]:
        account_name = self._clean_name(payload.account_name)
        persona = self._clean_name(payload.persona) or account_name
        email = self._clean_name(payload.email)
        password = str(payload.password or "")
        if not NAME_PATTERN.fullmatch(account_name):
            raise RegistrationError(
                "El nombre de cuenta debe tener entre 3 y 24 caracteres: letras, números, guion o guion bajo."
            )
        if not NAME_PATTERN.fullmatch(persona):
            raise RegistrationError(
                "El nombre de jugador debe tener entre 3 y 24 caracteres: letras, números, guion o guion bajo."
            )
        if len(password) < 8:
            raise RegistrationError("La contraseña debe tener al menos 8 caracteres.")
        if email and ("@" not in email or "." not in email.rsplit("@", 1)[-1]):
            raise RegistrationError("El email no parece válido.")
        if len(email) > 254:
            raise RegistrationError("El email es demasiado largo.")
        return account_name, persona, email, password

    def _view(
        self,
        record: SharedAccountRecord,
        preferences: Preferences | None = None,
    ) -> AccountView:
        prefs = preferences or self.web_db.get_preferences(record.account_id)
        return AccountView(
            account_id=record.account_id,
            account_name=record.account_name,
            email=record.email,
            personas=record.personas,
            primary_persona=record.primary_persona,
            appear_online=prefs.appear_online,
            challenge_series_assist=prefs.challenge_series_assist,
        )

    def _account_by_id(self, account_id: int) -> SharedAccountRecord | None:
        for record in self.database.accounts():
            if record.account_id == int(account_id):
                return record
        return None

    def register(self, payload: RegisterPayload) -> tuple[str, str, AccountView]:
        account_name, persona, email, password = self._validate(payload)
        invite_consumed = False
        if self.settings.invite_required:
            if not self.web_db.consume_invite(payload.invite_code):
                raise InviteError(
                    "La invitación no es válida, ya fue usada o está vencida."
                )
            invite_consumed = True

        try:
            record = self.database.create_account(
                account_name,
                password,
                persona=persona,
                email=email,
                country_code=str(payload.country_code or "").strip(),
            )
        except (SharedAccountExistsError, SharedPersonaExistsError):
            if invite_consumed:
                self.web_db.refund_invite(payload.invite_code)
            self.web_db.audit(
                account_name,
                "account.register_failed",
                {"reason": "duplicate"},
            )
            raise
        except Exception as exc:
            if invite_consumed:
                self.web_db.refund_invite(payload.invite_code)
            self.web_db.audit(
                account_name,
                "account.register_failed",
                {"reason": str(exc)[:200]},
            )
            raise RegistrationError("No se pudo crear la cuenta.") from exc

        try:
            self.web_db.set_preferences(
                record.account_id,
                appear_online=bool(payload.appear_online),
                challenge_series_assist=bool(payload.challenge_series_assist),
            )
        except Exception:
            self.web_db.audit(
                account_name,
                "account.preferences_failed",
                {"stage": "register"},
            )

        token, csrf = self.web_db.create_session(record.account_id)
        self.web_db.audit(
            account_name,
            "account.register",
            {"accountId": record.account_id, "persona": record.primary_persona},
        )
        return token, csrf, self._view(record)

    def login(self, identifier: str, password: str) -> tuple[str, str, AccountView]:
        name = self._clean_name(identifier)
        result = self.database.authenticate(name, str(password or ""))
        if not result.accepted:
            self.web_db.audit(
                name,
                "account.login_failed",
                {"reason": result.reason},
            )
            raise AuthError(result.reason)
        record = self.database.resolve_account(result.account_name) or self.database.resolve_account(name)
        if record is None or record.banned or not record.enabled:
            self.web_db.audit(name, "account.login_failed", {"reason": "unavailable"})
            raise AuthError("unavailable")
        token, csrf = self.web_db.create_session(record.account_id)
        self.web_db.audit(
            record.account_name,
            "account.login",
            {"accountId": record.account_id},
        )
        return token, csrf, self._view(record)

    def me(self, token: str) -> tuple[Session, AccountView] | None:
        session = self.web_db.session(token)
        if session is None or session.account_id is None:
            return None
        record = self._account_by_id(session.account_id)
        if record is None or record.banned or not record.enabled:
            self.web_db.delete_session(token)
            return None
        return session, self._view(record)

    def logout(self, token: str) -> None:
        session = self.web_db.session(token)
        if session is not None and session.account_id is not None:
            record = self._account_by_id(session.account_id)
            if record is not None:
                self.web_db.audit(
                    record.account_name,
                    "account.logout",
                    {"accountId": record.account_id},
                )
        self.web_db.delete_session(token)

    def update_preferences(
        self,
        token: str,
        *,
        appear_online: bool,
    ) -> dict[str, object]:
        current = self.me(token)
        if current is None:
            raise AuthError("not_authenticated")
        _, account = current
        preferences = self.web_db.get_preferences(account.account_id)
        self.web_db.set_preferences(
            account.account_id,
            appear_online=bool(appear_online),
            challenge_series_assist=preferences.challenge_series_assist,
        )
        self.web_db.queue_visibility(
            account.primary_persona,
            payload={"appearOnline": bool(appear_online)},
        )
        self.web_db.audit(
            account.account_name,
            "account.preferences",
            {"appearOnline": bool(appear_online)},
        )
        return {
            "appearOnline": bool(appear_online),
            "challengeSeriesAssist": preferences.challenge_series_assist,
            "syncQueued": True,
        }
