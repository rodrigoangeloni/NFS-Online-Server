"""JSON and download routes for the community site."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel

from common.accounts import SharedAccountExistsError, SharedPersonaExistsError
from web.accounts import AccountService, AccountView, AuthError, InviteError, RegisterPayload
from web.config import WebSettings
from web.downloads import DownloadNotFound, DownloadService
from web.security import RateLimiter, require_csrf, require_https


SESSION_COOKIE = "nfs_web_session"


class RegisterBody(BaseModel):
    accountName: str = ""
    email: str = ""
    password: str = ""
    persona: str = ""
    countryCode: str = ""
    appearOnline: bool = True
    challengeSeriesAssist: bool = True
    inviteCode: str = ""


class LoginBody(BaseModel):
    identifier: str = ""
    password: str = ""


class PreferencesBody(BaseModel):
    appearOnline: bool = True


def account_json(account: AccountView) -> dict[str, Any]:
    return {
        "accountId": account.account_id,
        "accountName": account.account_name,
        "email": account.email,
        "personas": list(account.personas),
        "primaryPersona": account.primary_persona,
        "appearOnline": account.appear_online,
        "challengeSeriesAssist": account.challenge_series_assist,
    }


def _set_session_cookie(
    response: JSONResponse, token: str, settings: WebSettings
) -> None:
    response.set_cookie(
        SESSION_COOKIE,
        token,
        max_age=settings.session_seconds,
        httponly=True,
        samesite="lax",
        secure=not settings.allow_insecure,
        path="/",
    )


def _session_token(request: Request) -> str:
    return str(request.cookies.get(SESSION_COOKIE) or "")


def _client_key(request: Request, prefix: str) -> str:
    host = request.client.host if request.client else "unknown"
    return f"{prefix}:{host}"


def live_payload(runtime_dir: Path) -> dict[str, Any]:
    path = runtime_dir / "classic-status.json"
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        value = {}
    if not isinstance(value, dict):
        value = {}
    rooms: list[dict[str, Any]] = []
    personas: set[str] = set()
    games = value.get("games") if isinstance(value.get("games"), dict) else {}
    for game, info in games.items():
        if not isinstance(info, dict):
            continue
        for room in info.get("rooms", []):
            if not isinstance(room, dict):
                continue
            room_personas = [
                str(persona)
                for persona in room.get("personas", [])
                if str(persona).strip()
            ]
            personas.update(room_personas)
            rooms.append(
                {
                    "game": str(game),
                    "name": str(room.get("name") or ""),
                    "host": str(room.get("host") or ""),
                    "players": int(room.get("players") or len(room_personas)),
                    "capacity": int(room.get("capacity") or 0),
                    "state": str(room.get("state") or ""),
                    "personas": room_personas,
                }
            )
    updated = value.get("updated_at")
    return {
        "connected": bool(rooms),
        "updatedAt": float(updated) if isinstance(updated, (int, float)) else 0.0,
        "rooms": rooms,
        "players": sorted(personas),
        "totalPlayers": len(personas),
    }


def build_router(
    settings: WebSettings,
    accounts: AccountService,
    downloads: DownloadService,
    limiter: RateLimiter,
) -> APIRouter:
    router = APIRouter()

    @router.get("/api/live")
    def live() -> dict[str, Any]:
        return live_payload(settings.runtime_dir)

    @router.get("/api/connect")
    def connect() -> dict[str, Any]:
        payload = downloads.connect_payload(settings.public_host)
        payload["siteUrl"] = settings.site_url
        return payload

    @router.get("/api/photos")
    def photos() -> dict[str, Any]:
        return {"photos": [], "available": False}

    @router.get("/api/account/me")
    def me(request: Request) -> dict[str, Any]:
        current = accounts.me(_session_token(request))
        if current is None:
            return {"authenticated": False, "account": None, "csrfToken": None}
        session, account = current
        return {
            "authenticated": True,
            "account": account_json(account),
            "csrfToken": session.csrf_token,
        }

    @router.post("/api/account/register")
    def register(request: Request, body: RegisterBody) -> JSONResponse:
        require_https(request, settings)
        limiter.check(_client_key(request, "register"))
        payload = RegisterPayload(
            account_name=body.accountName,
            email=body.email,
            password=body.password,
            persona=body.persona,
            country_code=body.countryCode,
            appear_online=body.appearOnline,
            challenge_series_assist=body.challengeSeriesAssist,
            invite_code=body.inviteCode,
        )
        try:
            token, csrf, account = accounts.register(payload)
        except InviteError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except (SharedAccountExistsError, SharedPersonaExistsError) as exc:
            raise HTTPException(
                status_code=409,
                detail="Ese nombre de cuenta o jugador ya está en uso.",
            ) from exc
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        response = JSONResponse(
            {
                "authenticated": True,
                "account": account_json(account),
                "csrfToken": csrf,
            }
        )
        _set_session_cookie(response, token, settings)
        return response

    @router.post("/api/account/login")
    def login(request: Request, body: LoginBody) -> JSONResponse:
        require_https(request, settings)
        limiter.check(_client_key(request, "login"))
        try:
            token, csrf, account = accounts.login(body.identifier, body.password)
        except AuthError as exc:
            raise HTTPException(
                status_code=401,
                detail="Usuario o contraseña incorrectos.",
            ) from exc
        response = JSONResponse(
            {
                "authenticated": True,
                "account": account_json(account),
                "csrfToken": csrf,
            }
        )
        _set_session_cookie(response, token, settings)
        return response

    @router.post("/api/account/logout")
    def logout(request: Request) -> JSONResponse:
        session = accounts.web_db.session(_session_token(request))
        if session is not None:
            require_csrf(request, session)
        accounts.logout(_session_token(request))
        response = JSONResponse({"ok": True})
        response.delete_cookie(SESSION_COOKIE, path="/")
        return response

    @router.post("/api/account/preferences")
    def preferences(request: Request, body: PreferencesBody) -> dict[str, Any]:
        require_https(request, settings)
        token = _session_token(request)
        current = accounts.me(token)
        if current is None:
            raise HTTPException(status_code=401, detail="not authenticated")
        session, _ = current
        require_csrf(request, session)
        result = accounts.update_preferences(token, appear_online=body.appearOnline)
        result["ok"] = True
        return result

    @router.get("/downloads/{download_id}")
    def download(download_id: str) -> FileResponse:
        try:
            path = downloads.resolve(download_id)
        except DownloadNotFound as exc:
            raise HTTPException(status_code=404, detail="download not found") from exc
        return FileResponse(
            path,
            media_type="application/zip",
            filename=path.name,
        )

    return router
