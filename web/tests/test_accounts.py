from __future__ import annotations

import pytest

from common.accounts import SharedAccountExistsError
from web.accounts import AccountService, AuthError, InviteError, RegisterPayload


def make_payload(code: str, name: str) -> RegisterPayload:
    return RegisterPayload(
        account_name=name,
        email="",
        password="secret123",
        persona=name,
        country_code="PY",
        appear_online=True,
        challenge_series_assist=True,
        invite_code=code,
    )


def test_register_creates_account_session_and_preferences(service: AccountService) -> None:
    code = service.web_db.create_invite("test", 1, None, "test")
    token, csrf, account = service.register(make_payload(code, "Driver"))
    assert csrf
    assert account.account_name == "Driver"
    assert account.account_id > 0
    assert service.database.resolve_account("Driver").enabled is True
    session = service.web_db.session(token)
    assert session is not None
    assert session.account_id == account.account_id
    assert service.web_db.get_preferences(account.account_id).appear_online is True


def test_register_rejects_used_invite(service: AccountService) -> None:
    code = service.web_db.create_invite("test", 1, None, "test")
    service.register(make_payload(code, "First"))
    with pytest.raises(InviteError):
        service.register(make_payload(code, "Second"))


def test_failed_registration_refunds_invite(service: AccountService) -> None:
    service.database.create_account("Driver", "secret123")
    code = service.web_db.create_invite("test", 1, None, "test")
    with pytest.raises(SharedAccountExistsError):
        service.register(make_payload(code, "Driver"))
    assert service.web_db.consume_invite(code) is True


def test_login_rejects_banned_account(service: AccountService) -> None:
    service.database.create_account("Bad", "secret123")
    service.database.set_banned("Bad", True)
    with pytest.raises(AuthError):
        service.login("Bad", "secret123")


def test_login_accepts_valid_credentials(service: AccountService) -> None:
    service.database.create_account("Driver", "secret123")
    token, csrf, account = service.login("Driver", "secret123")
    assert account.account_name == "Driver"
    assert service.web_db.session(token) is not None
    assert csrf


def test_preferences_queue_visibility_event(service: AccountService) -> None:
    code = service.web_db.create_invite("test", 1, None, "test")
    token, _, _ = service.register(make_payload(code, "Driver"))
    result = service.update_preferences(token, appear_online=False)
    assert result["syncQueued"] is True
    events = service.web_db.visibility_events()
    assert events[-1]["source_persona"] == "Driver"
