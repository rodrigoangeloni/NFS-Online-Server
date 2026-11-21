from __future__ import annotations

import pytest

from common.accounts import SharedAccountExistsError
from web.accounts import (
    AccountService,
    AuthError,
    InviteError,
    RegisterPayload,
    RegistrationError,
)


def make_payload(code: str, name: str) -> RegisterPayload:
    return RegisterPayload(
        account_name=name,
        email="driver@example.com",
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


def test_register_rejects_names_longer_than_the_game_accepts(service: AccountService) -> None:
    code = service.web_db.create_invite("test", 1, None, "test")
    with pytest.raises(RegistrationError):
        service.register(make_payload(code, "driverdriver1234"))


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


def test_recovery_code_and_forgot_password(service: AccountService) -> None:
    code = service.web_db.create_invite("test", 1, None, "test")
    token, csrf, account, recovery = service.register_with_recovery(
        make_payload(code, "Driver")
    )
    assert recovery.startswith("NFS-REC-")
    temp = service.forgot_password("Driver", "driver@example.com", recovery)
    assert temp.startswith("NFS-TMP-")
    temp_token, _, temp_account = service.login("Driver", temp)
    assert temp_account.must_change_password is True
    service.change_password(temp_token, temp, "newsecret123")
    new_token, _, new_account = service.login("Driver", "newsecret123")
    assert new_account.must_change_password is False
    assert new_token


def test_change_password_rejects_old_password(service: AccountService) -> None:
    code = service.web_db.create_invite("test", 1, None, "test")
    token, _, _ = service.register(make_payload(code, "Driver"))
    service.change_password(token, "secret123", "newsecret123")
    with pytest.raises(AuthError):
        service.login("Driver", "secret123")
    assert service.login("Driver", "newsecret123")[2].account_name == "Driver"


def test_set_email_and_regenerate_recovery_code(service: AccountService) -> None:
    code = service.web_db.create_invite("test", 1, None, "test")
    token, _, _ = service.register(make_payload(code, "Driver"))
    account = service.set_email(token, "new@example.com", "secret123")
    assert account.email == "new@example.com"
    recovery = service.regenerate_recovery_code(token)
    assert recovery.startswith("NFS-REC-")
