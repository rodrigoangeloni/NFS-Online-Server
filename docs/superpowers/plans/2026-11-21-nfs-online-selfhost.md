# NFS Online self-host + community site Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Poner en marcha el servidor NFS Online en un Debian con IP pública y un sitio web propio con registro, estado en vivo, descargas, leaderboards, noticias, TOS y administración.

**Architecture:** El servidor de juego corre nativo bajo `systemd` usando el launcher existente. Una app FastAPI separada (`web/`) comparte la SQLite de cuentas mediante `SQLiteAccountDatabase`, lee los JSON de estado de `runtime/` y sirve el frontend estático. Nginx Proxy Manager termina TLS. No hay fork, socket de Docker ni escritura de la web en el estado del juego.

**Tech Stack:** Python 3.10+, FastAPI, Uvicorn, SQLite (WAL), HTML/CSS/JS vanilla, pytest, Docker, systemd, Nginx Proxy Manager, Zig 0.16.0 para los clientes.

**Spec:** `docs/superpowers/specs/2026-11-21-nfs-online-selfhost-design.md`

## Global Constraints

- Python mínimo 3.10; el servidor de juego no añade dependencias de terceros.
- La web solo usa `fastapi`, `uvicorn[standard]` y, para tests, `pytest` + `httpx`.
- No se versionan binarios ni archivos comprimidos: `.asi`, `.dll`, `.exe`, `.zip` van a `artifacts/downloads/`, fuera del árbol del repo. `tools/check_public_tree.py` rechaza binarios incluso dentro de `runtime/`.
- Las ISOs y archivos de juego (`*.iso`) no se versionan y deben estar fuera del árbol del repo. `.gitignore` no basta para `tools/check_public_tree.py`, que recorre el filesystem.
- Todas las escrituras de cuentas usan `SQLiteAccountDatabase`; nunca `INSERT` directo en `accounts` o `personas`.
- `config/server.toml` es la fuente de verdad; las variables de entorno solo sobrescriben valores de despliegue.
- Registro, login y preferencias exigen HTTPS; `NFS_WEB_ALLOW_INSECURE=1` solo se usa en tests locales.
- Cookies `HttpOnly`, `Secure`, `SameSite=Lax`, `Path=/`; CSRF obligatorio en todo POST.
- Todo texto de usuario se escapa antes de insertarse en HTML.
- La web no escribe en `runtime/`, no toca procesos del juego y no usa el socket de Docker.
- Comando de tests: `python -m pytest web/tests -q` (el `conftest.py` añade `server/` y la raíz al `sys.path`).
- Un commit por tarea, con mensaje `feat(web): ...` o `chore(deploy): ...`.

## Review Focus

- **Invitaciones:** código expirado, revocado, agotado o consumido por dos registros a la vez; el segundo debe fallar y no crear cuenta.
- **Registro parcial:** si la cuenta se crea pero falla la sesión o las preferencias, el usuario no debe quedar en un estado ambiguo; la cuenta debe poder iniciar sesión igualmente y el error debe quedar auditado.
- **Login:** cuenta deshabilitada, baneada o email bloqueado; sesión expirada; CSRF ausente o inválido; no filtrar si el usuario existe.
- **Estado en vivo:** archivos `runtime/*.json` ausentes, corruptos o viejos; no romper la landing; respetar `appear_online=0`.
- **Descargas:** IDs inventados, manifest desactualizado y path traversal (`../`); solo servir archivos dentro de `artifacts/downloads/`.

---

### Task 1: Esqueleto de la app web y configuración

**Files:**
- Create: `web/__init__.py`
- Create: `web/config.py`
- Create: `web/app.py`
- Create: `web/requirements.txt`
- Create: `web/tests/conftest.py`
- Create: `web/tests/test_config.py`
- Create: `web/tests/test_health.py`

**Interfaces:**
- Consumes: `common.config.load_service_values` (repo `server/`).
- Produces:
  - `@dataclass(frozen=True) class WebSettings` con `package_root: Path`, `config_path: Path`, `account_db: Path`, `account_files: Path`, `runtime_dir: Path`, `downloads_dir: Path`, `static_dir: Path`, `public_host: str`, `site_url: str`, `games: tuple[str, ...]`, `admin_password_hash: str`, `session_seconds: int`, `invite_required: bool`, `allow_insecure: bool`, `trusted_proxy_ips: tuple[str, ...]`.
  - `load_settings(environ: Mapping[str, str] | None = None) -> WebSettings`
  - `create_app(settings: WebSettings | None = None) -> FastAPI`
  - `GET /healthz -> {"ok": true}`

- [ ] **Step 1: Write the failing tests**

```python
def test_load_settings_reads_public_host_and_paths(tmp_path, monkeypatch):
    monkeypatch.setenv("NFS_WEB_PUBLIC_HOST", "nfs.example.com")
    monkeypatch.setenv("NFS_GAMES", "u2,mw")
    settings = load_settings()
    assert settings.public_host == "nfs.example.com"
    assert settings.games == ("u2", "mw")
    assert settings.account_db.name == "accounts.sqlite3"
    assert settings.downloads_dir.name == "downloads"

def test_healthz_returns_ok():
    client = TestClient(create_app())
    response = client.get("/healthz")
    assert response.status_code == 200
    assert response.json() == {"ok": True}
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest web/tests/test_config.py web/tests/test_health.py -q`
Expected: FAIL with `ModuleNotFoundError` or `ImportError`.

- [ ] **Step 3: Implement `WebSettings`, `load_settings` and `create_app`**

`load_settings` debe leer `config/server.toml` con `load_service_values(path, "classic")` y `load_service_values(path, "carbon")`, resolver `ACCOUNT_DB`/`ACCOUNT_FILES` y aplicar overrides de entorno. `games` sale de `NFS_GAMES` (coma-separado) o de `DEFAULT_GAMES` del config. `runtime_dir` es `runtime/` bajo la raíz del repo; `downloads_dir` sale de `NFS_WEB_DOWNLOADS_DIR` y su default es `package_root.parent / "artifacts" / "downloads"` (hermano del repo). `create_app` monta `StaticFiles` en `/static` y registra `/healthz`.

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest web/tests/test_config.py web/tests/test_health.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add web/__init__.py web/config.py web/app.py web/requirements.txt web/tests
git commit -m "feat(web): add FastAPI skeleton and settings"
```

---

### Task 2: Esquema web, sesiones e invitaciones

**Files:**
- Create: `web/db.py`
- Create: `web/tests/test_db.py`

**Interfaces:**
- Consumes: `sqlite3`, `hashlib`, `secrets`, `time`.
- Produces:
  - `@dataclass(frozen=True) class Session` con `token_hash: str`, `account_id: int | None`, `role: str`, `csrf_token: str`, `expires_at: float`.
  - `@dataclass(frozen=True) class Preferences` con `appear_online: bool`, `challenge_series_assist: bool`.
  - `WebDatabase(path: Path)`
  - `ensure_schema() -> None`
  - `create_session(account_id: int | None, *, role: str = "player", now: float | None = None) -> tuple[str, str]`
  - `session(token: str, *, now: float | None = None) -> Session | None`
  - `delete_session(token: str) -> None`
  - `get_preferences(account_id: int) -> Preferences`
  - `set_preferences(account_id: int, *, appear_online: bool, challenge_series_assist: bool) -> None`
  - `create_invite(label: str, max_uses: int, expires_at: float | None, created_by: str) -> str`
  - `consume_invite(code: str, *, now: float | None = None) -> bool`
  - `refund_invite(code: str) -> None`
  - `list_invites() -> list[dict[str, object]]`
  - `revoke_invite(code_hash: str) -> None`
  - `visibility_events(limit: int = 20) -> list[dict[str, object]]`
  - `audit(actor: str, action: str, detail: Mapping[str, object]) -> None`
  - Tablas: `web_sessions`, `web_account_preferences`, `web_invites`, `web_audit_log`, `web_social_events`.

- [ ] **Step 1: Write the failing tests**

```python
def test_session_token_is_hashed_and_expires(tmp_path):
    db = WebDatabase(tmp_path / "accounts.sqlite3")
    db.ensure_schema()
    token, csrf = db.create_session(7, now=1000.0)
    assert db.session(token, now=1001.0).account_id == 7
    assert db.session(token, now=1000.0 + 8 * 24 * 3600) is None
    with sqlite3.connect(db.path) as conn:
        assert conn.execute("SELECT session_hash FROM web_sessions").fetchone()[0] != token

def test_invite_is_single_use(tmp_path):
    db = WebDatabase(tmp_path / "accounts.sqlite3")
    db.ensure_schema()
    code = db.create_invite("friends", 1, None, "admin")
    assert db.consume_invite(code) is True
    assert db.consume_invite(code) is False
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest web/tests/test_db.py -q`
Expected: FAIL with `ImportError`.

- [ ] **Step 3: Implement `WebDatabase`**

Configurar cada conexión con `PRAGMA journal_mode=WAL`, `PRAGMA busy_timeout=5000` y `PRAGMA foreign_keys=ON`. Usar `session_hash = sha256(token).hexdigest()`. `create_session` devuelve `token` y `csrf_token` en claro solo al llamador. `consume_invite` debe abrir una transacción `BEGIN IMMEDIATE` y comprobar `revoked_at IS NULL`, `expires_at > now` y `uses < max_uses` antes de incrementar `uses`; `refund_invite` decrementa `uses` sin bajar de cero. Crear `web_social_events` con el esquema de `server/common/web_social.py` para que la inserción de visibilidad funcione aunque el servidor no haya arrancado aún.

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest web/tests/test_db.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add web/db.py web/tests/test_db.py
git commit -m "feat(web): add sessions, preferences and invite storage"
```

---

### Task 3: Servicio de cuentas (registro, login, preferencias)

**Files:**
- Create: `web/accounts.py`
- Create: `web/tests/test_accounts.py`

**Interfaces:**
- Consumes: `SQLiteAccountDatabase`, `WebDatabase`, `WebSettings`.
- Produces:
  - `@dataclass(frozen=True) class RegisterPayload` con `account_name`, `email`, `password`, `persona`, `country_code`, `appear_online`, `challenge_series_assist`, `invite_code`.
  - `@dataclass(frozen=True) class AccountView` con `account_id: int`, `account_name`, `email`, `personas: tuple[str, ...]`, `primary_persona`, `appear_online`, `challenge_series_assist`.
  - `AccountService(database: SQLiteAccountDatabase, web_db: WebDatabase, settings: WebSettings)`
  - `register(payload: RegisterPayload) -> tuple[str, str, AccountView]` (token, csrf, account)
  - `login(identifier: str, password: str) -> tuple[str, str, AccountView]`
  - `me(token: str) -> tuple[Session, AccountView] | None`
  - `logout(token: str) -> None`
  - `update_preferences(token: str, *, appear_online: bool) -> dict[str, object]`

- [ ] **Step 1: Write the failing tests**

```python
def make_payload(code: str, name: str) -> RegisterPayload:
    return RegisterPayload(
        account_name=name, email="", password="secret123", persona=name,
        country_code="PY", appear_online=True, challenge_series_assist=True,
        invite_code=code,
    )

def test_register_creates_account_session_and_preferences(service):
    code = service.web_db.create_invite("test", 1, None, "test")
    token, csrf, account = service.register(make_payload(code, "Driver"))
    assert account.account_name == "Driver"
    assert account.account_id > 0
    assert service.database.resolve_account("Driver").enabled is True
    assert service.web_db.session(token).account_id == account.account_id

def test_register_rejects_used_invite(service):
    code = service.web_db.create_invite("test", 1, None, "test")
    service.register(make_payload(code, "First"))
    with pytest.raises(InviteError):
        service.register(make_payload(code, "Second"))

def test_failed_registration_refunds_invite(service):
    service.database.create_account("Driver", "secret123")
    code = service.web_db.create_invite("test", 1, None, "test")
    with pytest.raises(SharedAccountExistsError):
        service.register(make_payload(code, "Driver"))
    assert service.web_db.consume_invite(code) is True

def test_login_rejects_banned_account(service):
    service.database.create_account("Bad", "secret123")
    service.database.set_banned("Bad", True)
    with pytest.raises(AuthError):
        service.login("Bad", "secret123")

def test_preferences_queue_visibility_event(service):
    code = service.web_db.create_invite("test", 1, None, "test")
    token, _, _ = service.register(make_payload(code, "Driver"))
    result = service.update_preferences(token, appear_online=False)
    assert result["syncQueued"] is True
    assert service.web_db.visibility_events()[-1]["source_persona"] == "Driver"
```

Los fixtures `service` y `service.web_db` se definen en `web/tests/conftest.py` con una SQLite temporal.

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest web/tests/test_accounts.py -q`
Expected: FAIL with `ImportError`.

- [ ] **Step 3: Implement `AccountService`**

Validar `account_name` y `persona` con `^[A-Za-z0-9_-]{3,24}$`; password mínimo 8; email opcional. Consumir la invitación **antes** de crear la cuenta; si `create_account` falla, llamar a `refund_invite` y auditar `account.register_failed`, sin devolver sesión. Usar `database.authenticate` para login y comprobar `enabled`/`banned`. Al registrar, crear preferencias; si falla, auditar pero no impedir el login. `update_preferences` actualiza `web_account_preferences` e inserta en `web_social_events` (`action='visibility'`, `status='pending'`). Auditar `account.register`, `account.login`, `account.login_failed`, `account.logout`, `account.preferences`.

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest web/tests/test_accounts.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add web/accounts.py web/tests/test_accounts.py
git commit -m "feat(web): add account registration and login service"
```

---

### Task 4: Estado en vivo, salas y jugadores

**Files:**
- Create: `web/status.py`
- Create: `web/tests/test_status.py`
- Create: `web/tests/fixtures/classic-status.json`
- Create: `web/tests/fixtures/carbon-status.json`

**Interfaces:**
- Consumes: `WebSettings`, `SQLiteAccountDatabase`.
- Produces:
  - `StatusService(settings: WebSettings, database: SQLiteAccountDatabase, *, now: Callable[[], float] = time.time)`
  - `live() -> dict[str, object]` con `status`, `rooms`, `players`.

- [ ] **Step 1: Write the failing tests**

```python
def test_live_maps_rooms_and_players(status_service, fixture_files):
    payload = status_service.live()
    assert payload["status"]["connected"] is True
    assert {game["shortName"] for game in payload["status"]["games"]} == {"U2", "MW", "NFSC"}
    assert payload["rooms"]["available"] is True
    assert payload["rooms"]["rooms"][0]["shortName"] == "U2"
    assert payload["rooms"]["rooms"][0]["players"] == 2

def test_stale_status_is_offline(status_service, fixture_files):
    status_service.now = lambda: 10_000_000.0
    payload = status_service.live()
    assert payload["status"]["connected"] is False
    assert payload["rooms"]["available"] is False

def test_appear_offline_persona_is_hidden(status_service, seed_online_player):
    seed_online_player("Driver", appear_online=False)
    payload = status_service.live()
    assert all(player["persona"] != "Driver" for player in payload["players"])

def test_games_outside_nfs_games_are_omitted(status_service):
    status_service.settings = replace(status_service.settings, games=("u2", "mw"))
    payload = status_service.live()
    assert {game["shortName"] for game in payload["status"]["games"]} == {"U2", "MW"}
```

Los fixtures `status_service`, `fixture_files` y `seed_online_player` se definen en `web/tests/conftest.py`; `fixture_files` copia los JSON de `web/tests/fixtures/` a un `runtime/` temporal. El test de filtrado importa `dataclasses.replace`.

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest web/tests/test_status.py -q`
Expected: FAIL with `ImportError`.

- [ ] **Step 3: Implement `StatusService`**

Leer `runtime/classic-status.json` y `runtime/carbon-status.json`; considerar stale si `updated_at` tiene más de 15 s. Incluir en `games[]` solo los juegos de `settings.games` (`NFS_GAMES`) y añadir `enabled`. Mapear salas de Classic y Carbon a `{id, game, shortName, name, host, players, capacity, personas, gameMode, track, visibility, stateLabel, raceActive}`. Consultar `active_sessions` y `web_account_preferences`; ocultar personas con `appear_online=0` y las que `carbon_public_presence.show == 'OFFLINE'`. Si `active_sessions`, `web_account_preferences` o `carbon_public_presence` no existen todavía, degradar sin romper (lista vacía o sin filtro). Calcular `uptime` desde `runtime/services.json.started_at` si existe; si no, `--`. Devolver `rooms.available=false` si no hay ningún archivo de estado legible.

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest web/tests/test_status.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add web/status.py web/tests/test_status.py web/tests/fixtures
git commit -m "feat(web): aggregate live server status"
```

---

### Task 5: Descargas y manifest

**Files:**
- Create: `web/downloads.py`
- Create: `web/tests/test_downloads.py`
- Create: `web/tests/fixtures/manifest.json`

**Interfaces:**
- Consumes: `artifacts/downloads/manifest.json`.
- Produces:
  - `DownloadService(downloads_dir: Path)`
  - `connect_payload(public_host: str) -> dict[str, object]`
  - `resolve(download_id: str) -> Path`
  - `manifest() -> dict[str, object]`

- [ ] **Step 1: Write the failing tests**

```python
def test_connect_payload_exposes_public_host_and_downloads(service):
    payload = service.connect_payload("nfs.example.com")
    assert payload["serverAddress"] == "nfs.example.com"
    assert payload["downloads"][0]["id"] == "all"
    assert payload["downloads"][0]["available"] is True

def test_resolve_rejects_path_traversal(service):
    with pytest.raises(DownloadNotFound):
        service.resolve("../../etc/passwd")

def test_missing_file_marks_download_unavailable(service):
    (service.downloads_dir / "NFS-Online-Client-Pack-v0.2.22.zip").unlink()
    payload = service.connect_payload("nfs.example.com")
    assert payload["downloads"][0]["available"] is False
```

El fixture `service` copia `web/tests/fixtures/manifest.json` a un `artifacts/downloads/` temporal.

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest web/tests/test_downloads.py -q`
Expected: FAIL with `ImportError`.

- [ ] **Step 3: Implement `DownloadService`**

Leer el manifest de forma segura; si falta o es inválido, devolver `downloads: []`. Para cada entrada, comprobar que `filename` resuelve dentro de `downloads_dir` y que el archivo existe; recalcular `available` sin confiar en el manifest. `resolve` solo acepta IDs del manifest. Servir con `FileResponse` y `Content-Disposition: attachment` en la ruta de API.

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest web/tests/test_downloads.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add web/downloads.py web/tests/test_downloads.py web/tests/fixtures/manifest.json
git commit -m "feat(web): serve client downloads from manifest"
```

---

### Task 6: Leaderboards U2, MW y Carbon

**Files:**
- Create: `web/leaderboards.py`
- Create: `web/tests/test_leaderboards.py`

**Interfaces:**
- Consumes: `SQLiteAccountDatabase`, `classic.ea.sqlite_ranking.SQLiteClassicRankingStore`, `data/carbon/progression.sqlite3`.
- Produces:
  - `LeaderboardService(database: SQLiteAccountDatabase, carbon_progression: Path | None)`
  - `games() -> list[dict[str, object]]`
  - `board(game: str, category: int, limit: int = 100) -> dict[str, object]`

- [ ] **Step 1: Write the failing tests**

```python
def test_games_exposes_categories(service):
    games = service.games()
    assert [game["id"] for game in games] == ["underground2", "most_wanted", "carbon"]
    assert games[0]["categories"][0] == {"id": 0, "name": "Circuit"}

def test_u2_board_returns_ranked_rows(service_with_stats):
    board = service_with_stats.board("underground2", 0, limit=10)
    assert board["available"] is True
    assert board["rows"][0]["rank"] == 1
    assert board["rows"][0]["player"] == "DZeR"
    assert board["rows"][0]["wins"] == 5

def test_hidden_persona_is_excluded(service_with_stats):
    hide_persona(service_with_stats.database, "underground2", "DZeR")
    board = service_with_stats.board("underground2", 0, limit=10)
    assert all(row["player"] != "DZeR" for row in board["rows"])

def test_carbon_board_uses_skill_and_rep(service_with_stats):
    board = service_with_stats.board("carbon", 0, limit=10)
    assert board["rows"][0]["skill"] == 1012.0
    assert "rep" in board["rows"][0]
```

El fixture `service_with_stats` siembra cuentas y filas de `game_player_stats` en una SQLite temporal. `hide_persona` es un helper del test que inserta en `game_leaderboard_visibility`.

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest web/tests/test_leaderboards.py -q`
Expected: FAIL with `ImportError`.

- [ ] **Step 3: Implement `LeaderboardService`**

U2/MW: construir `SQLiteClassicRankingStore(self.database)` y llamar `leaderboard(game, category, limit=limit)`; mapear `ClassicPlayerStats` a `{rank, player, skill, wins, losses, disconnects}`. Carbon: consultar `carbon_progression_accounts` y `carbon_progression_stats` para `Skill_Level` y `Online_Rep`, unir con `personas`/`accounts` para excluir cuentas deshabilitadas/baneadas y con `game_leaderboard_visibility` para excluir ocultas. Ordenar por `skill DESC, persona ASC`. Devolver `available: false` si el archivo de progreso no existe.

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest web/tests/test_leaderboards.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add web/leaderboards.py web/tests/test_leaderboards.py
git commit -m "feat(web): add leaderboards for all games"
```

---

### Task 7: News y TOS

**Files:**
- Create: `web/content.py`
- Create: `web/tests/test_content.py`

**Interfaces:**
- Consumes: `common.legal.TERMS_OF_SERVICE_TEXT` y los textos públicos de noticias del servidor.
- Produces:
  - `news_payload() -> dict[str, object]`
  - `tos_payload() -> dict[str, object]`

- [ ] **Step 1: Write the failing tests**

```python
def test_news_contains_network_u2_and_mw():
    payload = news_payload()
    assert payload["available"] is True
    assert {feed["id"] for feed in payload["feeds"]} >= {"network", "u2", "mw"}

def test_tos_returns_shared_text():
    payload = tos_payload()
    assert payload["available"] is True
    assert "NFS Online" in payload["text"]
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest web/tests/test_content.py -q`
Expected: FAIL with `ImportError`.

- [ ] **Step 3: Implement `content.py`**

Definir en `web/content.py` los textos públicos de noticias para red, U2 y MW (`Underground 2 and Most Wanted online services are available.`, etc.) y usar `TERMS_OF_SERVICE_TEXT` para TOS. Devolver `available: true`, `source: "NFS Online game server"` y `carbonNewsAvailable: false`.

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest web/tests/test_content.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add web/content.py web/tests/test_content.py
git commit -m "feat(web): add news and terms endpoints"
```

---

### Task 8: Administración e invitaciones por CLI

**Files:**
- Create: `web/admin.py`
- Create: `web/manage.py`
- Create: `web/tests/test_admin.py`

**Interfaces:**
- Consumes: `WebSettings`, `SQLiteAccountDatabase`, `WebDatabase`.
- Produces:
  - `AdminService(settings, database, web_db)`
  - `login(password: str) -> tuple[str, str]`
  - `me(token: str) -> bool`
  - `create_invite(label: str, max_uses: int, days: int) -> tuple[str, dict]`
  - `list_accounts(query: str = "") -> list[dict]`
  - `set_account_state(account: str, action: str) -> dict`
  - `audit_log(limit: int = 100) -> list[dict]`
  - CLI: `python -m web.manage hash-password`, `create-invite`, `list-invites`, `list-accounts`.

- [ ] **Step 1: Write the failing tests**

```python
def test_admin_login_rejects_wrong_password(admin_service):
    with pytest.raises(AdminAuthError):
        admin_service.login("wrong")

def test_admin_creates_and_lists_invite(admin_service):
    code, _ = admin_service.create_invite("friends", 5, 30)
    assert any(invite["label"] == "friends" for invite in admin_service.web_db.list_invites())
    assert len(code) >= 12

def test_admin_bans_account(admin_service, seeded_account):
    result = admin_service.set_account_state("Driver", "ban")
    assert result["banned"] is True
    assert admin_service.database.resolve_account("Driver").banned is True
```

Los fixtures `admin_service` y `seeded_account` viven en `web/tests/conftest.py`; `admin_service` usa un hash PBKDF2 de `test-password`.

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest web/tests/test_admin.py -q`
Expected: FAIL with `ImportError`.

- [ ] **Step 3: Implement `AdminService` and `manage.py`**

Comparar la contraseña con `NFS_WEB_ADMIN_PASSWORD_HASH` usando PBKDF2 y `hmac.compare_digest`. Crear sesión con `role='admin'` y `account_id=None`. `set_account_state` acepta `enable`, `disable`, `ban`, `unban`, `kick` y llama a los métodos oficiales de `SQLiteAccountDatabase`. Auditar cada acción. `manage.py` usa `argparse` y `getpass`; `hash-password` imprime el hash PBKDF2 en el formato del repo.

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest web/tests/test_admin.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add web/admin.py web/manage.py web/tests/test_admin.py
git commit -m "feat(web): add admin service and invite CLI"
```

---

### Task 9: Rutas API, CSRF, HTTPS y rate limit

**Files:**
- Modify: `web/app.py`
- Create: `web/security.py`
- Create: `web/api.py`
- Create: `web/tests/test_api.py`

**Interfaces:**
- Consumes: all previous services.
- Produces:
  - `GET /api/live`, `GET /api/connect`, `GET /api/photos`, `GET /api/account/me`, `POST /api/account/register`, `POST /api/account/login`, `POST /api/account/logout`, `POST /api/account/preferences`, `GET /api/leaderboard-games`, `GET /api/leaderboards`, `GET /api/news`, `GET /api/tos`, `GET /downloads/{id}`, `POST /api/admin/login`, `GET /api/admin/accounts`, `POST /api/admin/invites`, `GET /api/admin/invites`, `POST /api/admin/accounts/{name}/{action}`, `GET /api/admin/audit`, `GET /healthz`.
  - `require_https(request: Request, settings: WebSettings) -> None`
  - `require_csrf(request: Request, session: Session) -> None`
  - `RateLimiter(limit: int, window: float)` con `check(key: str) -> None` (lanza 429).

- [ ] **Step 1: Write the failing tests**

```python
def test_register_flow_returns_authenticated_account(client):
    response = client.post("/api/account/register", json=register_payload(client))
    assert response.status_code == 200
    body = response.json()
    assert body["authenticated"] is True
    assert body["account"]["accountName"] == "Driver"
    assert body["csrfToken"]

def test_post_without_csrf_is_rejected(client, logged_in):
    response = client.post("/api/account/preferences", json={"appearOnline": False})
    assert response.status_code == 403

def test_insecure_register_is_rejected(settings):
    settings = replace(settings, allow_insecure=False)
    client = TestClient(create_app(settings), base_url="http://testserver")
    response = client.post("/api/account/register", json={})
    assert response.status_code == 403

def test_login_rate_limit(client):
    for _ in range(5):
        client.post("/api/account/login", json={"identifier": "x", "password": "y"})
    response = client.post("/api/account/login", json={"identifier": "x", "password": "y"})
    assert response.status_code == 429
```

Los fixtures `client`, `logged_in`, `settings` y el helper `register_payload` viven en `web/tests/conftest.py`; `client` usa `base_url="https://testserver"` y una SQLite temporal.

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest web/tests/test_api.py -q`
Expected: FAIL with `404`/`ImportError`.

- [ ] **Step 3: Implement the API and middleware**

Inyectar servicios en `app.state`. Para determinar HTTPS, aceptar `request.url.scheme == "https"` o `X-Forwarded-Proto: https` solo si el cliente está en `trusted_proxy_ips`. Cookies de sesión: `nfs_web_session`; admin: `nfs_web_admin`. CSRF se lee de `X-CSRF-Token`. Rate limit en memoria con `RLock` y `deque`. Middleware de cabeceras de seguridad y `TrustedHostMiddleware` si `allowed_hosts` no está vacío. `/api/photos` devuelve `{"photos": [], "available": False}` en Fase 1.

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest web/tests/test_api.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add web/app.py web/security.py web/api.py web/tests/test_api.py
git commit -m "feat(web): expose API with CSRF and HTTPS enforcement"
```

---

### Task 10: Shell visual y sistema de diseño

**Files:**
- Create: `web/static/styles.css`
- Create: `web/static/index.html`
- Create: `web/static/app.js`

**Interfaces:**
- Consumes: `/api/live`, `/api/connect`.
- Produces: landing completa con IDs `totalPlayers`, `uptime`, `updatedAt`, `serverGrid`, `connectionWarning`, `serverAddress`, `copyServerAddress`, `downloadSummary`, `downloadGrid`, `roomCount`, `roomGrid`, `playerCount`, `playerList`.

- [ ] **Step 1: Write the static shell**

Crear `index.html` con la estructura de la landing: topbar, hero, status, connect, rooms, players, support/contact. Enlazar `/static/styles.css` y `/static/app.js`. No usar imágenes externas.

- [ ] **Step 2: Implement the design tokens**

`styles.css` define `--bg: #080808`, `--panel: #101010`, `--line: rgba(255,255,255,.09)`, `--text: #f4f4f4`, `--muted: #8d8d8d`, `--accent: #ff2a2a`, `--accent-soft: rgba(255,42,42,.15)`, `--green: #56ef91`. Incluir ruido SVG, grid, topbar sticky, tarjetas, tablas y responsive.

- [ ] **Step 3: Verify static serving**

Run: `python -m pytest web/tests/test_api.py -q -k health`
Expected: PASS.

- [ ] **Step 4: Visual check**

Arrancar `uvicorn web.app:app --reload` y abrir `/` en el navegador. Verificar que no hay 404 de CSS/JS y que el layout colapsa a una columna a 390 px.

- [ ] **Step 5: Commit**

```bash
git add web/static/styles.css web/static/index.html web/static/app.js
git commit -m "feat(web): add landing page shell and design system"
```

---

### Task 11: Integración de la landing con la API

**Files:**
- Modify: `web/static/app.js`

**Interfaces:**
- Consumes: `/api/live`, `/api/connect`.
- Produces: render de estado, salas, jugadores, descargas, botones de copiar y polling cada 10 s.

- [ ] **Step 1: Implement `renderStatus`, `renderRooms`, `renderPlayers`**

Copiar la forma de los datos de la spec, escapar todo con `escapeHtml`, mostrar `empty-state` cuando no haya datos y `connectionWarning` cuando `connected` sea falso.

- [ ] **Step 2: Implement `loadConnect` y `renderDownloads`**

Mostrar `serverAddress`, chips online/offline, tarjetas con versión, tamaño, SHA corto, enlace de descarga y botón de copiar. Si `downloads` está vacío, mostrar el mensaje de “No downloads configured”.

- [ ] **Step 3: Implement polling y copiar**

`refreshAll()` al cargar y cada 10 s; `copyText` con `navigator.clipboard` y fallback `document.execCommand("copy")`.

- [ ] **Step 4: Verify with the running app**

Run: `uvicorn web.app:app --port 8080` y abrir `/`. Comprobar que el polling no genera errores en consola y que los estados offline se muestran correctamente.

- [ ] **Step 5: Commit**

```bash
git add web/static/app.js
git commit -m "feat(web): wire landing page to live status API"
```

---

### Task 12: Página de cuenta

**Files:**
- Create: `web/static/account.html`
- Create: `web/static/account.js`

**Interfaces:**
- Consumes: `/api/account/me`, `/api/account/register`, `/api/account/login`, `/api/account/logout`, `/api/account/preferences`.
- Produces: formularios de registro/login, panel de cuenta, toggle de `appearOnline`, lista de personas, stats.

- [ ] **Step 1: Implement the HTML**

Replicar la estructura de la referencia: `loginPanel`, `createPanel`, `accountPanel`, `loginForm`, `createForm`, `appearOnlineToggle`, `logoutButton`, `personaList`, `statsGrid`, `socialInbox` (oculto en Fase 1). Incluir `inviteCode` en el formulario de registro.

- [ ] **Step 2: Implement `account.js`**

Usar `fetch` con `credentials: "same-origin"`; guardar `csrfToken`; enviar `X-CSRF-Token` en POST; manejar errores con mensajes en `role="status"`. Al registrar, redirigir a `/account` o mostrar el panel.

- [ ] **Step 3: Verify flows**

Run: `python -m pytest web/tests/test_api.py -q -k account`
Expected: PASS. Luego probar manualmente registro, logout y login en el navegador.

- [ ] **Step 4: Commit**

```bash
git add web/static/account.html web/static/account.js
git commit -m "feat(web): add account registration and login page"
```

---

### Task 13: Página de leaderboards

**Files:**
- Create: `web/static/leaderboards.html`
- Create: `web/static/leaderboards.js`

**Interfaces:**
- Consumes: `/api/leaderboard-games`, `/api/leaderboards`.
- Produces: tabs de juego, selector de modo, tabla con rank/player/skill/wins/losses/D-C y variante Carbon skill/rep.

- [ ] **Step 1: Implement the HTML shell**

Incluir `gameTabs`, `leaderboardTitle`, `leaderboardCount`, `modePicker`, `leaderboardRows`, `leaderboardColumns`.

- [ ] **Step 2: Implement `leaderboards.js`**

Cargar juegos, seleccionar el primero, cargar tabla, cambiar de modo con `select`, escapar celdas, mostrar `Leaderboard unavailable` si falla.

- [ ] **Step 3: Verify**

Run: `python -m pytest web/tests/test_leaderboards.py -q`
Expected: PASS. Probar `/leaderboards` en el navegador con datos sembrados.

- [ ] **Step 4: Commit**

```bash
git add web/static/leaderboards.html web/static/leaderboards.js
git commit -m "feat(web): add leaderboards page"
```

---

### Task 14: Páginas de News y TOS

**Files:**
- Create: `web/static/news.html`
- Create: `web/static/news.js`
- Create: `web/static/tos.html`
- Create: `web/static/tos.js`

**Interfaces:**
- Consumes: `/api/news`, `/api/tos`.

- [ ] **Step 1: Implement `news.html` and `news.js`**

Tarjetas por feed; mostrar `available=false` como “endpoint unavailable”; escapar texto.

- [ ] **Step 2: Implement `tos.html` and `tos.js`**

Cargar `/api/tos` y poner el texto en `<pre>` con `textContent` (nunca `innerHTML`).

- [ ] **Step 3: Verify**

Run: `python -m pytest web/tests/test_content.py -q`
Expected: PASS. Abrir `/news` y `/tos`.

- [ ] **Step 4: Commit**

```bash
git add web/static/news.html web/static/news.js web/static/tos.html web/static/tos.js
git commit -m "feat(web): add news and terms pages"
```

---

### Task 15: Panel de administración

**Files:**
- Create: `web/static/admin.html`
- Create: `web/static/admin.js`

**Interfaces:**
- Consumes: `/api/admin/login`, `/api/admin/accounts`, `/api/admin/invites`, `/api/admin/audit`, `/api/admin/accounts/{name}/{action}`.

- [ ] **Step 1: Implement the HTML**

Secciones: login, lista de invitaciones con formulario (label, usos, días), tabla de cuentas con búsqueda y acciones enable/disable/ban/unban, log de auditoría.

- [ ] **Step 2: Implement `admin.js`**

Cookie de admin, CSRF, `fetch` con `credentials: "same-origin"`, render de tablas, confirmación antes de banear, manejo de errores.

- [ ] **Step 3: Verify**

Run: `python -m pytest web/tests/test_admin.py web/tests/test_api.py -q`
Expected: PASS. Probar `/admin` en el navegador.

- [ ] **Step 4: Commit**

```bash
git add web/static/admin.html web/static/admin.js
git commit -m "feat(web): add admin panel"
```

---

### Task 16: Empaquetado de clientes

**Files:**
- Create: `tools/package_clients.py`
- Create: `tests/test_package_clients.py`

**Interfaces:**
- Consumes: `source/client-zig/zig-out/bin/net_*.asi`, `clients/*/net_*.ini`, `artifacts/downloads/`.
- Produces:
  - `package_clients(host: str, asi_dir: Path, out_dir: Path, version: str, asi_loader: Path | None = None, games: Sequence[str] = ("u2", "mw")) -> dict[str, object]`
  - `write_ini(source: Path, host: str, destination: Path) -> None`
  - `manifest.json` con la forma de `/api/connect.downloads[]`.

- [ ] **Step 1: Write the failing tests**

```python
def test_write_ini_sets_host_and_lan_host(tmp_path):
    source = tmp_path / "net_u2.ini"
    source.write_text("[network]\nhost = 127.0.0.1\n\n[lan]\nhost = 127.0.0.1\n")
    destination = tmp_path / "out.ini"
    write_ini(source, "nfs.example.com", destination)
    text = destination.read_text()
    assert "host = nfs.example.com" in text
    assert text.count("host = 127.0.0.1") == 0

def test_package_contains_asi_ini_bat_and_manifest(tmp_path):
    result = package_clients("nfs.example.com", fake_asi_dir(tmp_path), tmp_path / "out", "0.2.22")
    assert (tmp_path / "out" / "NFS-Online-Client-Pack-v0.2.22.zip").is_file()
    assert result["downloads"][0]["sha256"]
```

`fake_asi_dir` es un helper del test que crea `net_u2.asi` vacío y copia la plantilla `clients/underground2/net_u2.ini` a un directorio temporal.

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_package_clients.py -q`
Expected: FAIL with `ImportError`.

- [ ] **Step 3: Implement the packager**

Copiar `.asi`, generar `.ini` con el host, escribir `INSTALAR.bat`, `LEEME.txt`, incluir `dinput8.dll` (32-bit) si se pasa `--asi-loader`, comprimir con `zipfile`, calcular `sha256` y `size`, escribir `manifest.json` de forma atómica. El loader 32-bit se obtiene de `https://github.com/ThirteenAG/Ultimate-ASI-Loader/releases/download/v10.0.4/Ultimate-ASI-Loader-NoPDB.zip` (contiene `dinput8.dll`; no usar `_x64`). SHA-256 verificado: `73D6DB0481AF99B8481E8E6A685DD385E5A3E0E10518BFE97A993F7F368667EB`. Los `.asi` se compilan con `source/client-zig/build_linux.sh` y Zig 0.16.0. `INSTALAR.bat` debe detectar `%ProgramFiles(x86)%\Need for Speed Underground 2` y `%ProgramFiles(x86)%\Need for Speed Most Wanted 2005`, pedir elevación UAC si hace falta, respaldar un loader existente antes de copiar y verificar `SPEED2.EXE`/`speed.exe` + `.asi` + `.ini` + `dinput8.dll` al final. No usar rutas absolutas dentro del ZIP. Si falta un `.asi`, fallar con un mensaje claro. En Fase 1 el default es `games=("u2","mw")`; para Fase 1b se ejecuta con `games=("u2","mw","carbon")`.

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_package_clients.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add tools/package_clients.py tests/test_package_clients.py
git commit -m "feat(tools): package preconfigured NFS clients"
```

---

### Task 17: Artefactos de despliegue

**Files:**
- Create: `deploy/systemd/nfs-online.service`
- Create: `deploy/systemd/nfs-watchdog.service`
- Create: `deploy/systemd/nfs-watchdog.timer`
- Create: `deploy/healthcheck.sh`
- Create: `deploy/duckdns-update.sh`
- Create: `deploy/systemd/duckdns-update.service`
- Create: `deploy/systemd/duckdns-update.timer`
- Create: `deploy/env.example`
- Create: `web/Dockerfile`
- Create: `docker/compose.web.yml`
- Create: `docker/compose.dev.yml`
- Create: `docker/Dockerfile.server`
- Create: `docker/entrypoint-server.sh`
- Create: `docs/local-testing.md`
- Create: `docs/deployment.md`

**Interfaces:**
- Consumes: repo, `data/`, `runtime/`, `config/`, `artifacts/downloads/`.
- Produces: unidad systemd del juego, watchdog, contenedor web, compose y runbook.

- [ ] **Step 1: Write the systemd units**

`nfs-online.service`: `Type=oneshot`, `RemainAfterExit=yes`, `WorkingDirectory=/opt/nfs-online/repo`, `ExecStart=/opt/nfs-online/venv/bin/python nfs_online.py start --games u2,mw --daemon`, `ExecStop=/opt/nfs-online/venv/bin/python nfs_online.py stop`, `User=nfs`, `EnvironmentFile=/opt/nfs-online/env/nfs.env` con `NFS_GAMES=u2,mw`. En Fase 1b se cambia a `--games u2,mw,carbon` y `NFS_GAMES=u2,mw,carbon`. `nfs-watchdog.timer` cada 5 min ejecuta `deploy/healthcheck.sh` y reinicia si devuelve 1.

`deploy/healthcheck.sh`: lee `NFS_GAMES` (default `u2,mw`) y comprueba:
- Siempre: TCP 13505 (Messenger) y 20923 (web/PREL).
- `u2`: TCP 20921, 20922.
- `mw`: TCP 30920, 30921.
- `carbon`: TCP 18210, 18215, 9000.
- UDP 20000 si `u2` o `mw`; UDP 19119 si `carbon`.

Usa `ss -ltn`/`ss -lun` y sale 1 si falta un puerto. Así el watchdog detecta caídas parciales sin exigir Carbon en Fase 1.

`deploy/duckdns-update.sh`: leer `DUCKDNS_DOMAIN=nfs-fps` y `DUCKDNS_TOKEN` desde `env/nfs.env`, llamar a `https://www.duckdns.org/update?domains=${DUCKDNS_DOMAIN}&token=${DUCKDNS_TOKEN}&ip=` y fallar si la respuesta no es `OK`. `duckdns-update.timer` cada 5 minutos. Si la IP es fija, este timer es opcional; si es dinámica, es obligatorio.

- [ ] **Step 2: Write the Dockerfile and compose**

`web/Dockerfile`: `python:3.12-slim`, `ENV PYTHONPATH=/app/server:/app`, crear `appuser`, copiar `web/` y `server/`, instalar `web/requirements.txt`, `USER appuser`, `CMD ["uvicorn","web.app:app","--host","0.0.0.0","--port","8080","--proxy-headers"]`. `docker/compose.web.yml`: puerto `127.0.0.1:8080:8080`, volúmenes `../data:/app/data`, `../runtime:/app/runtime:ro`, `../config:/app/config:ro`, `../server:/app/server:ro`, `${NFS_DOWNLOADS_DIR:-../NFS-Online-Artifacts/downloads}:/app/downloads:ro`, `NFS_WEB_DOWNLOADS_DIR=/app/downloads`, `env_file`, `restart: unless-stopped`, `user: "${NFS_UID:-1000}:${NFS_GID:-1000}"` para que `appuser` pueda escribir en `data/`.

Para Docker Desktop, `docker/Dockerfile.server`: `python:3.12-slim`, copiar el repo, `CMD ["./docker/entrypoint-server.sh"]`. `docker/entrypoint-server.sh` arranca `python nfs_online.py start --games "${NFS_GAMES:-u2,mw}" --daemon`, atrapa `TERM/INT` y ejecuta `python nfs_online.py stop` antes de salir. `docker/compose.dev.yml`: `nfs-server` + `nfs-web`, bind mounts `../data`, `../runtime` (runtime read-only en la web) y `../NFS-Online-Artifacts/downloads` (read-only), `NFS_GAMES=u2,mw`, `NFS_WEB_ALLOW_INSECURE=1`, `NFS_WEB_PUBLIC_HOST=localhost`, `NFS_WEB_DOWNLOADS_DIR=/app/downloads`, y puertos publicados TCP `13505/20921/20922/20923/30920/30921` + UDP `20000`. Para probar desde el mismo PC, `NFS_PUBLIC_HOST=127.0.0.1` y `NFS_LOCAL_IPV4=127.0.0.1`; para LAN, usar la IP LAN del host Windows. En dev, ejecutar ambos contenedores con el mismo UID (o root) para que `data/` sea escribible; en producción se usa el UID del host `nfs`. Si SQLite WAL da problemas de locking en el bind mount de Windows, cambiar a volúmenes nombrados.

- [ ] **Step 3: Write `docs/deployment.md`**

Incluir: requisitos, clonado, usuario `nfs`, venv, `python nfs_online.py check`, `configure --public-host nfs-fps.duckdns.org`, `create-account`, systemd, firewall, DNS/DuckDNS, NPM (`nfs-fps.duckdns.org` → `127.0.0.1:8080`), Docker, backups, actualización y troubleshooting. Documentar `NFS_WEB_PUBLIC_HOST=nfs-fps.duckdns.org` y `NFS_WEB_SITE_URL=https://nfs-fps.duckdns.org`. En `docs/local-testing.md`, documentar `docker compose -f docker/compose.dev.yml up --build`, la URL `http://localhost:8080`, cómo crear la primera invitación y cómo probar U2/MW contra `127.0.0.1`.

- [ ] **Step 4: Verify**

En Debian: `systemd-analyze verify deploy/systemd/nfs-online.service` y `docker compose -f docker/compose.web.yml config`. En Windows: revisar YAML con un parser. Antes de ejecutar `tools/check_public_tree.py`, las ISOs y archivos de juego deben estar **fuera del árbol del repo**; `.gitignore` no es suficiente porque el checker recorre el filesystem.

- [ ] **Step 5: Commit**

```bash
git add deploy web/Dockerfile docker docs
git commit -m "chore(deploy): add systemd, Docker and deployment runbook"
```

---

### Task 18: CI para la web

**Files:**
- Modify: `.github/workflows/ci.yml`

**Interfaces:**
- Consumes: `web/requirements.txt`, `web/tests`.
- Produces: job `web` en Python 3.10–3.13.

- [ ] **Step 1: Add the job**

Añadir `web` con `actions/checkout`, `actions/setup-python`, `pip install -r web/requirements.txt`, `python -m pytest web/tests -q`, `python -m pytest tests/test_package_clients.py -q`.

- [ ] **Step 2: Run locally**

Run: `python -m pytest web/tests tests/test_package_clients.py -q`
Expected: PASS.

- [ ] **Step 3: Commit**

```bash
git add .github/workflows/ci.yml
git commit -m "ci: run web and client packaging tests"
```

---

### Task 19: Prueba end-to-end y runbook de juego

**Files:**
- Modify: `docs/deployment.md`
- Create: `docs/runbook.md`

**Interfaces:**
- Consumes: all previous tasks.
- Produces: checklist de aceptación y diagnóstico.

- [ ] **Step 1: Write the runbook**

Incluir: probar primero `docker compose -f docker/compose.dev.yml up --build` y el flujo de registro/descarga en `http://localhost:8080`; después, en Debian, arrancar el servidor con `--games u2,mw`, comprobar `status`, abrir puertos 13505/20921/20922/20923/30920/30921/20000, crear invitación, registrar cuenta, descargar ZIP, instalar en U2/MW, entrar al lobby, ver sala en la landing y revisar logs. Carbon queda como bloque separado de Fase 1b (puertos 18210/18215/19119/9000).

- [ ] **Step 2: Execute the checklist on Debian**

Verificar `systemctl status nfs-online`, `python nfs_online.py status`, `dig +short nfs-fps.duckdns.org`, `curl https://nfs-fps.duckdns.org/healthz`, `/api/live`, registro y descarga. Documentar resultados y problemas.

- [ ] **Step 3: Commit**

```bash
git add docs/deployment.md docs/runbook.md
git commit -m "docs: add end-to-end game and site runbook"
```

---

### Task 20: Backups y actualización

**Files:**
- Create: `deploy/backup.sh`
- Create: `deploy/update.sh`
- Create: `deploy/systemd/nfs-backup.service`
- Create: `deploy/systemd/nfs-backup.timer`

**Interfaces:**
- Consumes: `data/accounts.sqlite3`, `data/users/`, `config/`, `artifacts/downloads/manifest.json`.
- Produces: backup diario verificado y script de actualización.

- [ ] **Step 1: Write `backup.sh`**

`set -euo pipefail`; `BACKUP_ROOT="${1:-data/backups}"`; crear `${BACKUP_ROOT}/YYYY-MM-DD/`; `sqlite3 data/accounts.sqlite3 ".backup '...'"`; `sqlite3 ... "PRAGMA integrity_check"`; copiar `data/users`, `config`, `manifest.json`; retener 14 días.

- [ ] **Step 2: Write `update.sh`**

`git pull --ff-only`, `python nfs_online.py check`, backup, rebuild clients (`source/client-zig/build_linux.sh`), `systemctl restart nfs-online`, `docker compose pull/up -d`, health check.

- [ ] **Step 3: Write the systemd timer**

`nfs-backup.timer` diario a las 04:00; `nfs-backup.service` ejecuta `deploy/backup.sh`.

- [ ] **Step 4: Test backup in a temp directory**

Run: `bash deploy/backup.sh /tmp/nfs-test` y comprobar que `integrity_check` devuelve `ok`.

- [ ] **Step 5: Commit**

```bash
git add deploy/backup.sh deploy/update.sh deploy/systemd/nfs-backup.service deploy/systemd/nfs-backup.timer
git commit -m "chore(deploy): add backups and update scripts"
```

---

## Fase 2 (backlog, no ejecutar todavía)

- **Fotos de Carbon:** leer `assets` + `metadata_json`, servir `/api/photos` y `/api/photos/{id}/content`.
- **DLC:** enlazar `/account/dlc` con el `DLC_STORE_LISTEN` existente o proxear la tienda.
- **Social:** usar `web_social_events` para mensajes, amigos, bloqueos e invitaciones.
- **Perfil ampliado:** entitlements, stats por juego, cambio de contraseña.

## Verificación final

- `python -m pytest web/tests tests/test_package_clients.py -q` en verde.
- `python nfs_online.py check` en verde.
- `python tools/check_public_tree.py` en verde sobre un clon limpio o `git archive HEAD` (el working tree con `runtime/`, `data/`, `logs/` y `__pycache__` locales no cuenta).
- `docker compose -f docker/compose.dev.yml up --build` levanta U2/MW + web y el registro funciona en `http://localhost:8080`.
- `dig +short nfs-fps.duckdns.org` devuelve la IP pública.
- `https://nfs-fps.duckdns.org/healthz` responde `{"ok":true}`.
- Un amigo completa registro → descarga → instalación → partida en U2 o MW.
- La landing muestra salas/jugadores de U2/MW y no rompe con el servidor apagado.
- Carbon se valida en Fase 1b con sus puertos y su paquete.
- `systemctl restart nfs-online` y reinicio del host dejan el servidor operativo.
- Backup restaurado en una carpeta temporal e `integrity_check` correcto.
