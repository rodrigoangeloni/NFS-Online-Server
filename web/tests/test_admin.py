from __future__ import annotations

from dataclasses import replace

import pytest

from web.admin import AdminAuthError, AdminService


def test_admin_login_create_and_revoke(admin_service: AdminService) -> None:
    token, csrf = admin_service.login("admin-test-password")
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
        admin_service.login("wrong-password")


def test_admin_disabled_without_hash(admin_service: AdminService) -> None:
    disabled = AdminService(
        admin_service.web_db,
        replace(admin_service.settings, admin_password_hash=""),
    )
    with pytest.raises(AdminAuthError):
        disabled.login("anything")


def test_admin_rejects_bad_invite_limits(admin_service: AdminService) -> None:
    with pytest.raises(ValueError):
        admin_service.create_invite("bad", 0, 30)
