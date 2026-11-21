from __future__ import annotations

from dataclasses import replace

import pytest

from web.admin import AdminAuthError, AdminService


def test_admin_login_create_and_revoke(admin_service: AdminService) -> None:
    token, csrf = admin_service.login("admin", "admin-test-password")
    assert csrf
    session = admin_service.me(token)
    assert session is not None
    assert session.role == "admin"

    invite = admin_service.create_invite("friends", 2, 30)
    assert str(invite["code"]).startswith("NFS-")
    listing = admin_service.list_invites()
    assert listing[0]["code"] == invite["code"]
    assert listing[0]["status"] == "active"

    admin_service.revoke_invite(str(invite["codeHash"]))
    assert admin_service.list_invites()[0]["status"] == "revoked"

    admin_service.logout(token)
    assert admin_service.me(token) is None


def test_admin_wrong_password(admin_service: AdminService) -> None:
    with pytest.raises(AdminAuthError):
        admin_service.login("admin", "wrong-password")


def test_admin_wrong_username(admin_service: AdminService) -> None:
    with pytest.raises(AdminAuthError):
        admin_service.login("root", "admin-test-password")


def test_admin_disabled_without_hash(admin_service: AdminService) -> None:
    disabled = AdminService(
        admin_service.web_db,
        replace(admin_service.settings, admin_password_hash=""),
    )
    with pytest.raises(AdminAuthError):
        disabled.login("admin", "anything")


def test_admin_rejects_bad_invite_limits(admin_service: AdminService) -> None:
    with pytest.raises(ValueError):
        admin_service.create_invite("bad", 0, 30)


def test_admin_can_change_password(admin_service: AdminService) -> None:
    admin_service.login("admin", "admin-test-password")
    token, csrf = admin_service.change_password(
        "admin-test-password",
        "new-admin-password",
    )
    assert csrf
    assert admin_service.me(token) is not None
    with pytest.raises(AdminAuthError):
        admin_service.login("admin", "admin-test-password")
    assert admin_service.login("admin", "new-admin-password")[0]


def test_admin_lists_and_resets_accounts(admin_service: AdminService) -> None:
    assert admin_service.database is not None
    admin_service.database.create_account(
        "Driver",
        "secret123",
        email="driver@example.com",
    )
    accounts = admin_service.list_accounts()
    assert accounts[0]["accountName"] == "Driver"
    assert accounts[0]["email"] == "driver@example.com"

    temporary = admin_service.reset_account_password("Driver")
    assert temporary.startswith("NFS-TMP-")
    assert admin_service.database.authenticate("Driver", temporary).accepted
    security = admin_service.web_db.get_security(accounts[0]["accountId"])
    assert security["must_change"] is True
