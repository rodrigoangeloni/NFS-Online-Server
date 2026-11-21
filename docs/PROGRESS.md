# Progreso — NFS Online autoalojado

**Fecha:** 2026-11-21
**Rama:** `feat/web-mvp` (desde `main`, commits sin pushear)
**Objetivo:** servidor U2/MW en Debian + web comunitaria propia (FastAPI) + clientes preconfigurados.

## Resumen de estado

| Área | Estado |
|---|---|
| Diseño y plan | Completos en `docs/superpowers/` |
| Dominio | `nfs-fps.duckdns.org` decidido |
| Juegos Fase 1 | U2 + MW (instalados en esta PC) |
| Carbon | Fase 1b, pendiente |
| Servidor local | Corriendo en Docker Desktop (`nfs-server-dev`) |
| Clientes | Compilados y copiados a las carpetas de U2/MW |
| Login real | MW y U2 verificados (auth, persona, Messenger y sala) |
| Web `web/` | MVP implementado en `feat/web-mvp`: registro, login, sesiones, descargas y landing |
| Debian/NPM/DuckDNS | Pendiente de desplegar |

## Protocolo de trabajo

Cada paso sigue el ciclo definido en `AGENTS.md`:

1. Prueba (unitaria, integración, Docker, navegador o juego).
2. Registro del comando y resultado en este archivo.
3. Commit detallado con el alcance y las pruebas ejecutadas.

## Cronología

### 2026-11-21

1. Se analizó `https://brake.go.ro/`:
   - FastAPI/Uvicorn detrás de Caddy.
   - Frontend HTML/CSS/JS vanilla.
   - APIs `/api/live`, `/api/connect`, `/api/account/*`, `/api/leaderboards`, `/api/news`, `/api/tos`, `/api/photos`.
   - Las cuentas web usan la misma SQLite que el juego.
2. Se revisó el repo:
   - `SQLiteAccountDatabase` es process-safe (WAL, PBKDF2).
   - `runtime/classic-status.json` y `runtime/carbon-status.json` ya existen para una web externa.
   - Los leaderboards y el blob store de Carbon ya están en SQLite.
3. Se eligió la arquitectura:
   - Web FastAPI separada que importa la API oficial de cuentas.
   - Servidor de juego nativo en Debian; Docker Desktop para pruebas locales.
   - NPM para HTTPS; sin fork ni socket de Docker.
4. Se decidió el dominio `nfs-fps.duckdns.org` y arrancar por U2/MW.
5. Se movieron los ISOs fuera del repo:
   - `E:\vscode-workspace\NFS-Online-ISOs\`.
6. Se descargó y verificó el Ultimate ASI Loader 32-bit:
   - `dinput8.dll` SHA-256 `73D6DB0481AF99B8481E8E6A685DD385E5A3E0E10518BFE97A993F7F368667EB`.
7. Se compilaron los `.asi` actuales desde fuente en WSL con Zig 0.16.0:
   - `net_u2.asi` `8DB6557E...`
   - `net_mw.asi` `35B6C620...`
   - `net_carbon.asi` `FBACD6C5...`
   - El audit PE pasó para los tres.
8. Se creó el stack local de Docker Desktop:
   - `docker/Dockerfile.server`
   - `docker/entrypoint-server.sh`
   - `docker/compose.dev.yml`
   - Contenedor `nfs-server-dev`, U2/MW, puertos TCP `13505/20921/20922/20923/30920/30921` y UDP `20000-20005`.
9. Se creó la cuenta local `TestDriver` (contraseña de prueba definida localmente, no versionada).
10. Se instalaron los clientes en las carpetas de los juegos con UAC:
    - U2: `dinput8.dll`, `net_u2.asi`, `net_u2.ini`.
    - MW: `dinput8.dll`, `net_mw.asi`, `net_mw.ini`.
    - Hashes verificados contra staging.
11. `python tools/check_public_tree.py` pasa; el repo no tiene binarios.

## Hito: login de MW + sala (2026-11-21)

- Se lanzó **Most Wanted** y se saltó el intro/attract renombrando temporalmente los videos de `MOVIES` a `.bak` (backup reversible, fuera del repo).
- Navegación: `Online` → `Usar cuenta de EA existente` → cuenta `testdriver` + contraseña local → persona `TestDriver` → `Carrera rápida` → `Circuito` → `Crear partida`.
- Evidencia en `logs/classic.log`:
  - `most_wanted lobby command=auth result=ok close=False`
  - `most_wanted lobby command=pers result=ok close=False`
  - `most_wanted lobby command=sele result=selection close=False`
  - `EA Messenger client connected ...`
  - `authenticated=1 persona=TestDriver`
  - `most_wanted lobby command=gcre result=game_created close=False`
- `runtime/classic-status.json` ahora publica la sala:

```json
"most_wanted": {
  "enabled": true,
  "rooms": [
    {
      "id": 1,
      "name": "TestDriver",
      "host": "TestDriver",
      "players": 1,
      "capacity": 4,
      "state": "OPEN",
      "visibility": "PUBLIC",
      "personas": ["TestDriver"]
    }
  ]
}
```

- La sala queda abierta esperando el mínimo de 2 jugadores.
- La cuenta `testdriver` existe en `data/accounts.sqlite3`; su contraseña es local y no se versiona.

### Automatización del juego

La entrada sintética solo funciona si la ventana del juego está en primer plano:

1. `SetForegroundWindow` + `BringWindowToTop` sobre `speed.exe`.
2. Seleccionar el campo (teclado o clic).
3. **Enter** para entrar en modo edición.
4. Escribir con `keybd_event` usando **VK + scancode** (no solo scancode).
5. **Enter** para confirmar.

Sin el paso de foco, el juego ignora el teclado. Los clics sintéticos no son fiables para los campos de texto; el teclado sí.

## Hito: login de U2 + sala (2026-11-21)

- U2 ya arranca; el chequeo de **Disc 2** quedó resuelto externamente por el usuario.
- Se saltó el intro renombrando `FMVOpening.vp6`, `ealogo.vp6`, `PSA.vp6` y `THX_logo.vp6` a `.bak` (reversible, fuera del repo).
- Navegación: `Online` → `Usar cuenta de EA existente` → `testdriver` + contraseña local → persona `TestDriver` → `Punto de encuentro` → `Crear partida` → `Circuito` → `Resort Loop` → `Continuar` → `Aceptar` aviso.
- Evidencia en `logs/classic.log`:
  - `underground2 lobby command=auth result=ok close=False`
  - `underground2 lobby command=pers result=ok close=False`
  - `EA Messenger ... adapter=underground2-classic-messenger`
  - `underground2 assigned roomless U2 game to default ranked room: user=573763722 room=A.LAN`
  - `underground2 U2 game size negotiated: ... applied_min=2 applied_max=6`
  - `underground2 lobby command=gcre result=game_created close=False`
- `runtime/classic-status.json` publica la sala de U2:

```json
"underground2": {
  "enabled": true,
  "rooms": [{
    "id": 1,
    "name": "017.TestDriver",
    "host": "TestDriver",
    "players": 1,
    "capacity": 6,
    "state": "OPEN",
    "visibility": "PUBLIC",
    "personas": ["TestDriver"]
  }]
}
```

- La sala queda abierta esperando el mínimo de 2 jugadores.

### Restaurar el intro de U2

```powershell
Get-ChildItem 'C:\Program Files (x86)\Need for Speed Underground 2\MOVIES' -Filter '*.vp6.bak' |
  Rename-Item -NewName { $_.Name -replace '\.bak$','' }
```

## Commits de esta etapa

| Commit | Mensaje |
|---|---|
| `d130c9e` | `chore(repo): keep game media and local artifacts out of git` |
| `b7ea59e` | `docs(plan): document self-host architecture and U2/MW rollout` |
| `84bcced` | `feat(dev): run U2/MW server in Docker Desktop` |
| `c8e40c9` | `docs(progress): record local U2/MW setup and next steps` |
| `954078c` | `docs(progress): verify public tree from committed archive` |

Este documento y `AGENTS.md` forman parte de este mismo commit.

## Hito: web MVP, descargas y prueba LAN (2026-11-21)

Se implementó el corte vertical mínimo para que un amigo pueda crear cuenta y
descargar el cliente desde otra PC de la LAN.

### Backend

- `web/config.py`: settings desde `config/server.toml` + overrides de entorno.
- `web/db.py`: sesiones hasheadas, CSRF, preferencias, invitaciones, auditoría y
  cola `web_social_events` compatible con el servidor.
- `web/accounts.py`: registro con invitación opcional, login, logout y
  preferencias; usa `SQLiteAccountDatabase`.
- `web/downloads.py`: manifest seguro, `available` recalculado y `/downloads/{id}`.
- `web/api.py` + `web/security.py`: API JSON, CSRF, HTTPS configurable y rate
  limit de login.
- `web/app.py`: landing y página de cuenta.

### Frontend

- `web/static/index.html`, `account.html`, `styles.css`, `app.js`, `account.js`.
- Diseño dark street-racing, responsive, sin imágenes externas.
- Polling de estado cada 10 s y descargas desde `/api/connect`.

### Paquetes de cliente

- `tools/package_clients.py` construye:
  - `NFS-Online-Client-Pack-v0.2.22.zip` (U2 + MW, 10.7 MB).
  - `NFS-Online-U2-Client-v0.2.22.zip` (5.8 MB).
  - `NFS-Online-MW-Client-v0.2.22.zip` (5.9 MB).
  - `manifest.json` con SHA-256.
- Incluye `dinput8.dll` verificado, `net_*.asi`, `net_*.ini` con
  `host = 192.0.2.37` y el Widescreen Fix en `WindowedMode = 1`,
  `SkipIntro = 1` (U2 además `NoOpticalDriveFix = 1`).
- `INSTALAR.bat` / `install.ps1`: detección por registro, rutas típicas o
  selector de carpeta; UAC; backup en `Documentos\NFS-Online\Backup`.
- `DESINSTALAR.bat` / `uninstall.ps1`: quita solo los archivos del paquete.
- Probado en una carpeta falsa de U2: instaló y desinstaló los archivos
  correctos, conservó `dinput8.dll` y `SPEED2.EXE`.
- Los ZIP y `manifest.json` viven en
  `E:\vscode-workspace\NFS-Online-Artifacts\downloads\`; no se versionan.

### Pruebas ejecutadas

```text
python -m pytest web/tests/test_config.py web/tests/test_health.py -q   -> 3 passed
python -m pytest web/tests/test_db.py -q                                -> 5 passed
python -m pytest web/tests/test_accounts.py -q                          -> 6 passed
python -m pytest web/tests/test_downloads.py -q                         -> 5 passed
python -m pytest web/tests/test_api.py -q                               -> 7 passed
python -m pytest web/tests/test_pages.py web/tests/test_api.py -q       -> 10 passed
python -m pytest tests/test_package_clients.py -q                       -> 5 passed
python -m pytest web/tests tests/test_package_clients.py -q             -> 34 passed
```

Prueba HTTP real:

- `GET /healthz` → `200 {"ok":true}`.
- `GET /api/connect` → 3 descargas `available=true`.
- Registro `SmokeTest` por API → `200`, `/me` autenticado, preferencias OK.
- Registro `BrowserTest` desde la página → panel de cuenta visible, logout y
  login posteriores OK.
- Descarga `GET /downloads/u2` → 6.103.984 bytes, SHA-256
  `8b9b6115eb0863d00e7a5caf04c325f448ac9689b2c443a474cad98881317687`,
  igual al manifest.
- Los usuarios de prueba se borraron de `data/accounts.sqlite3`; queda
  `TestDriver`.

### Incidencia SQLite al correr la web en Windows

Al ejecutar `uvicorn` en el host Windows contra el mismo `data/accounts.sqlite3`
que el contenedor, el servidor registró:

```text
sqlite3.OperationalError: disk I/O error
sqlite3.OperationalError: unable to open database file
```

La web se movió a un contenedor (`nfs-web-dev`) con el mismo bind mount
`../data` que `nfs-server-dev`. Después de eso, registrar una cuenta desde la
web y verla con `python nfs_online.py account list` funcionó sin errores nuevos.

### Red LAN

- El puerto **8080** ya lo usa otro proyecto (`sbrw-core`); la web NFS quedó en
  **8081** (`0.0.0.0:8081->8080/tcp`).
- Reglas de firewall agregadas, limitadas a `192.0.2.0/24`:
  - `NFS Online web 8080 (LAN)` (queda por compatibilidad).
  - `NFS Online web 8081 (LAN)`.
- `nfs-server-dev` publica los puertos de juego en `0.0.0.0` y se reinició con
  `NFS_PUBLIC_HOST=192.0.2.37` / `NFS_LOCAL_IPV4=192.0.2.37`.
- Pendiente: instalar el paquete en la otra PC y verificar registro, descarga y
  entrada a la sala desde allí.

## Verificación actual

- Servidor:
  - `docker exec nfs-server-dev python nfs_online.py status` → `Classic: running`, `Messenger: running in Classic`.
  - `Test-NetConnection 127.0.0.1` OK en `13505`, `20921`, `20922`, `20923`, `30920`, `30921`.
  - `runtime/classic-status.json` reporta U2 y MW habilitados y sin salas (el jugador salió).
  - `nfs-server-dev` anuncia `192.0.2.37`; `nfs-web-dev` corre en `http://192.0.2.37:8081`.
- Clientes locales:
  - Archivos presentes en ambas carpetas.
  - `dinput8.dll` idéntico en U2/MW.
  - `net_u2.ini` y `net_mw.ini` locales con `host = 127.0.0.1`.
  - Los ZIP de descarga usan `host = 192.0.2.37`.
- Repo:
  - Working tree: el checker ve `data/accounts.sqlite3`, `data/server-state.json`, `runtime/*.json`, `logs/*.log` y `__pycache__` del test local (ignorados por git).
  - Árbol commiteado: `git archive HEAD` + checker → OK.
  - Sin `.iso`, `.asi`, `.dll` ni `.zip` versionados.

## Pendiente inmediato

1. [x] Abrir MW y probar login online:
   - Cuenta: `testdriver`
   - Persona: `TestDriver`
   - Contraseña: definida localmente (no versionada).
   - Resultado: `auth result=ok`, `pers result=ok`, Messenger autenticado y sala creada.
2. [x] Abrir U2 y probar login online:
   - Resultado: `auth result=ok`, `pers result=ok`, Messenger `underground2-classic-messenger` y sala `017.TestDriver` creada.
3. [ ] Probar la sala con un segundo jugador/cuenta (mínimo 2).
4. [x] Implementar el MVP de `web/` (registro, login, descargas y landing).
5. [ ] Desde la otra PC de la LAN: abrir `http://192.0.2.37:8081`, crear cuenta, descargar e instalar el pack U2 + MW.
6. [ ] Probar la sala con la segunda PC y confirmar que el servidor anuncia `192.0.2.37`.
7. [ ] Probar Most Wanted con el Widescreen Fix y DSR en fullscreen.

### Restaurar los videos de MW

Si se quiere devolver el intro original de MW:

```powershell
Get-ChildItem 'C:\Program Files (x86)\Need for Speed Most Wanted 2005\MOVIES' -Filter '*.vp6.bak' |
  Rename-Item -NewName { $_.Name -replace '\.bak$','' }
```

## Comandos útiles

```powershell
docker compose -f docker/compose.dev.yml up -d --build
docker exec nfs-server-dev python nfs_online.py status
Get-Content logs\classic.log -Tail 80
docker compose -f docker/compose.dev.yml down

# Verificar solo el árbol commiteado (sin runtime/data/logs locales)
git archive HEAD --format=zip -o "$env:TEMP\nfs-clean.zip"
Expand-Archive "$env:TEMP\nfs-clean.zip" "$env:TEMP\nfs-clean" -Force
python tools/check_public_tree.py "$env:TEMP\nfs-clean"
```

## Riesgos conocidos

- Los juegos son repacks de ElAmigos; si el `.exe` fue modificado por el No-CD, los offsets del plugin pueden no coincidir.
- El chequeo de **Disc 2** de U2 quedó resuelto externamente por el usuario; el ISO disponible es el instalador, no el disco de juego.
- Los videos de intro/attract de MW y U2 están renombrados a `.bak` para poder entrar al menú; es reversible.
- La automatización de teclado solo funciona con la ventana del juego en primer plano; usar `SetForegroundWindow` + `BringWindowToTop`.
- `python nfs_online.py status` falla en Windows (`WinError 87`); usar la versión dentro del contenedor.
- Docker Desktop no reproduce el networking exacto de Linux; la prueba final es en el Debian.
- No ejecutar `nfs_online.py stop` en Windows mientras el stack Docker está activo.
