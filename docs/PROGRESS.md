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
| Debian/NPM/DuckDNS | Desplegado; `duckdns-nfs` actualiza `nfs-fps` |

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

- El puerto **8080** lo usa NFS World (y `sbrw-core` en Windows); Assetto ocupa
  `8081-8088`; la web NFS quedó en **8096** (`0.0.0.0:8096->8080/tcp`).
- Reglas de firewall agregadas, limitadas a `192.0.2.0/24`:
  - `NFS Online web 8080 (LAN)` y `NFS Online web 8081 (LAN)` (pruebas anteriores).
  - `NFS Online web 8096 (LAN)` (puerto definitivo).
- `nfs-server-dev` publica los puertos de juego en `0.0.0.0` y se reinició con
  `NFS_PUBLIC_HOST=192.0.2.37` / `NFS_LOCAL_IPV4=192.0.2.37`.
- Pendiente: instalar el paquete en la otra PC y verificar registro, descarga y
  entrada a la sala desde allí.

## Hito: prueba LAN completa con 2 jugadores y carrera (2026-11-21)

La segunda PC de la LAN completó el flujo entero:

1. Abrió `http://192.0.2.37:8096`.
2. Creó la cuenta `driver4` con persona `DriverD`.
3. Descargó el pack U2 + MW y lo instaló con `INSTALAR.bat`.
4. Abrió U2, inició sesión y entró a la sala de `TestDriver`.
5. Inició una carrera y vio el auto de la otra PC.

Evidencia:

- `logs/classic.log`:
  - Segundo cliente: `underground2 lobby command=auth result=ok`.
  - `underground2 lobby command=pers result=ok`.
  - `underground2 lobby command=gjoi result=game_joined`.
  - `underground2 lobby command=gset result=game_settings`.
  - `underground2 stock directory reply ... lobby=192.0.2.37:20922`.
  - Relay de carrera para dos usuarios:
    - `user=463561769 ... target=100.64.0.1:3658 ... relayed=1`
    - `user=573763722 ... target=100.64.0.2:3658 ... relayed=1`
- `runtime/classic-status.json`:
  - Sala `016.TestDriver`, `players=2`, `capacity=6`, `state=ACTIVE`.
  - Personas `DriverD` y `TestDriver`.
  - `last_race_activity_at` actualizado.
- Web `/api/live`: `totalPlayers=2`, misma sala.
- Cuenta en SQLite: `account=driver4 persona=DriverD enabled=1`.

Resultado: registro, descarga, instalación, login, sala y carrera de dos jugadores
funcionando por LAN. No hubo errores nuevos en el servidor; los `disk I/O error`
del log son de la prueba anterior con la web en Windows.

## Hito: despliegue público en Debian (2026-11-21)

Se desplegó el servidor en `debian-server` (`192.0.2.200`, público
`<IP publica>`).

- Código en `/opt/nfs-online/repo`; datos, runtime, logs, backups,
  env y descargas bajo `/opt/nfs-online/`.
- Juego en contenedor `nfs-server` (systemd deshabilitado):
  - DNS `1.1.1.1` para evitar el DNS split-horizon del router.
  - Log: `Public host: nfs-fps.duckdns.org`, IPv4 `<IP publica>`,
    local `192.0.2.200`.
  - Puertos: TCP `13505`, `20921-20923`, `30920-30921`; UDP
    `20000-20005`.
- Repo Debian: clon git de `main`; actualización con `deploy/update.sh`.
- Stack Docker `nfs-online`: `nfs-server` + `nfs-web`; systemd
  deshabilitado. Portainer los muestra en **Containers**.
- El DNS del router es split-horizon: devuelve `192.0.2.200` para
  `nfs-fps`; `1.1.1.1`/`8.8.8.8` devuelven `<IP publica>`. Por eso
  `nfs-server` usa `dns: 1.1.1.1` y anuncia la IP pública.
- DuckDNS: `duckdns` actualiza `nextcloud-<usuario>`; `duckdns-nfs` actualiza
  `nfs-fps` con el token de esa cuenta. Token en
  `/opt/nfs-online/env/duckdns-nfs.env` (chmod 600, no versionado).
- Log de `duckdns-nfs`: `DuckDNS request ... successful. IP(s) unchanged.`
- UFW: reglas para los puertos de juego; `8096` no se abre.
- Web:
  - Contenedor `nfs-web`, `127.0.0.1:8096->8080/tcp`, usuario UID 1000.
  - Conectado a `nginx-proxy-manager-new_default`.
  - NPM: `nfs-fps.duckdns.org` → `http://nfs-web:8080`, Force SSL,
    HTTP/2; certificado Let's Encrypt.
- Verificación pública:
  - `https://nfs-fps.duckdns.org/healthz` → `{"ok":true}`.
  - `GET /`, `/account`, `/api/connect` → 200.
  - Descarga U2 por HTTPS: 6.104.050 bytes, SHA-256 igual al manifest.
  - Registro con invitación por HTTPS → cuenta y `/me` autenticados.
  - HTTP `80` → `301` a HTTPS.
  - `http://nfs-fps.duckdns.org:8096` → timeout desde Internet (loopback).
- TCP de juego verificados desde Internet con `webfetch`:
  - `20921`, `20922`, `30920`, `30921` responden con el protocolo del
    juego (transport error esperado al pedir HTTP).
  - `20923` responde `404` (endpoint HTTP de noticias/PREL).
  - `13505` responde `404` (Messenger/PREL).
- Router: se agregaron `NFS-Online-Msg` (TCP 13505),
  `NFS-Online-U2` (TCP 20921-20923), `NFS-Online-MW` (TCP 30920-30921)
  y `NFS-Online-Race` (UDP 20000-20005), todas a `192.0.2.200`.
  Las reglas existentes (443, Assetto, SNES, etc.) no se tocaron.
- `8096` sigue cerrado desde Internet.
- Pendiente: carrera completa desde una conexión externa para confirmar
  el relay UDP `20000-20005`.
- Invitación de prueba creada en la SQLite del Debian (no versionada).

## Hito: panel de administración de invitaciones (2026-11-21)

Se agregó un panel privado para no depender de la terminal para ver o crear
códigos.

- URL: `https://nfs-fps.duckdns.org/admin`.
- Login con clave PBKDF2 (`NFS_WEB_ADMIN_PASSWORD_HASH`), cookie
  `nfs_web_admin`, CSRF y rate limit.
- Lista invitaciones con código visible, etiqueta, usos, vencimiento y
  estado (`activa`, `agotada`, `vencida`, `revocada`).
- Permite crear invitaciones (etiqueta, usos, días) y revocarlas.
- El código se guarda en la SQLite además del hash para poder mostrarlo
  meses después; la base sigue protegida por permisos del servidor.
- Los códigos existentes `<invitacion>` y `<invitacion de prueba>` se
  completaron en la columna `code` para que aparezcan en el panel.
- Probado por HTTPS: login, listado, creación y revocación.
- Tests: `python -m pytest web/tests tests/test_package_clients.py -q`
  → **43 passed**.

## Hito: cambio de contraseña y recuperación gratuita (2026-11-21)

Se agregó seguridad de cuentas sin depender de un servidor de correo.

- **Email obligatorio** para cuentas nuevas (`NFS_WEB_EMAIL_REQUIRED=1`);
  las cuentas viejas pueden cargarlo desde `/account` con su contraseña.
- **Cambio de contraseña de usuario** en `/account` (actual + nueva).
- **Cambio de clave de administrador** en `/admin`; el hash queda en
  SQLite y el de `web.env` solo se usa como semilla inicial. El login
  pide usuario (`admin` por defecto) y clave.
- **Código de recuperación** `NFS-REC-XXXX-XXXX` generado al registrarse
  y visible una vez; se puede regenerar desde la cuenta.
- **Olvidé mi contraseña**: cuenta + email + código de recuperación
  genera una temporal `NFS-TMP-XXXX-XXXX` válida 24 h, que se muestra
  en la web y obliga a cambiarla al entrar.
- **Reset desde admin**: `/admin` lista cuentas y genera una temporal
  para cualquier jugador.
- Al resetear/recuperar se invalidan las sesiones web de esa cuenta.
- La temporal vencida se invalida al intentar entrar por la web.
- **Anti-spam:** límite de 5 intentos por minuto por IP real para login,
  registro, recuperación y login admin. Detrás de NPM se usa
  `X-Real-IP`/`X-Forwarded-For` solo si la conexión viene de
  `172.28.0.0/16`; si no, se ignora para evitar spoofing.
- Prueba pública: 5 intentos fallidos → `401`, sexto → `429` con
  `Retry-After: 60`; el login de admin usa un contador separado y
  siguió funcionando.
- Tests actuales: `python -m pytest web/tests tests/test_package_clients.py -q`
  → **52 passed**.

Verificación en el Debian por HTTPS:

- Registro `RecoveryE2E` → código `NFS-REC-...`.
- `forgot` → temporal `NFS-TMP-...`.
- Login con temporal → `mustChangePassword=true`.
- Cambio de contraseña → login con la nueva OK.
- Reset desde admin → otra temporal y `mustChangePassword=true`.
- Cuenta de prueba borrada al terminar.

Tests: `python -m pytest web/tests -q` → **47 passed**.

## Fix: límite de 15 caracteres en cuentas (2026-11-21)

El cliente clásico valida el nombre de cuenta **antes** de enviar `auth`.
`driverdriver1234` (16 caracteres) mostraba “El nombre de cuenta EA
especificado no es válido” y el servidor no registraba ningún intento;
`driverdriver123` (15) entraba sin problema.

- `web/accounts.py`: `NAME_PATTERN` pasa de `{3,24}` a `{3,15}` para
  cuenta y persona, con el motivo documentado en el código.
- `web/static/account.html`: `maxlength=15` y texto de ayuda actualizado.
- Test nuevo: `test_register_rejects_names_longer_than_the_game_accepts`
  (rojo antes del cambio, verde después).
- Suite: `python -m pytest web/tests -q` → **53 passed**.
- En el Debian se borró la cuenta de prueba de 16 caracteres; backup en
  `data/backups/accounts-before-delete-*.sqlite3`.
- La clave de admin se había cambiado desde el panel a las 22:28 UTC y
  no se recordaba. Se restauró el hash semilla de `web.env`
  (`<clave-admin>`) y se verificó con `POST /api/admin/login` → 200.

## Panel admin: BAN y DESBANEAR (2026-11-21)

Se agregó el botón **BAN/DESBANEAR** en `/admin`, junto a RESET.

- `AdminService.set_account_banned` marca `accounts.banned`, escribe el
  evento `ban`/`unban` en `account_policy_events` e invalida las
  sesiones web de esa cuenta. El servidor de juego lee el evento y
  desconecta al piloto en ~1 s.
- Rutas: `POST /api/admin/accounts/{cuenta}/ban` y `/unban`, con CSRF.
- La tabla muestra `baneada` en rojo y el botón cambia a DESBANEAR.
- Tests: `python -m pytest web/tests tests/test_package_clients.py -q`
  → **62 passed**.

## Limpieza: solo Docker en el Debian (2026-11-21)

- Se eliminó el unit `/etc/systemd/system/nfs-online.service`, que
  había quedado instalado (disabled/inactive) del despliegue previo sin
  contenedor; luego `daemon-reload` y `reset-failed`.
- No quedan procesos `nfs_online` en el host. Los puertos de juego los
  publica `nfs-server` y la web corre en `nfs-web`.
- Verificación: `systemctl status nfs-online` → unit not found;
  `docker ps` → `nfs-server` + `nfs-web`; `/healthz` → `{"ok":true}`.

## Pack: el instalador fuerza el dominio (2026-11-21)

El pack 0.2.22 copiaba el INI tal como venía. Si el amigo reutilizaba un
pack viejo (por ejemplo el de la prueba LAN, con `host =
192.0.2.37`), el cliente nunca llegaba al Debian y el servidor no
veía ningún `auth`; el síntoma era “la cuenta existe en la web pero no
entra al juego”.

- `tools/package_clients.py` agrega `host.txt` con el host del build.
- `packaging/client/install.ps1` lee `host.txt` y reescribe las líneas
  `host =` de `net_u2.ini`/`net_mw.ini` después de copiarlas.
- Tests nuevos en `tests/test_package_clients.py`; uno de punta a punta
  extrae el pack, corre `install.ps1` contra carpetas de juego falsas con
  un INI viejo y verifica que ambas queden con el host del pack.
- Ese test encontró que `$Host` es una variable reservada de PowerShell;
  el parámetro se renombró a `$HostName`.
- Pack publicado: **0.2.24** (binarios de cliente 0.2.22 + instalador
  nuevo). SHA-256 del pack completo:
  `1d9829fe69339ad622413e2b40e6068522c6f5de183b33130bfa65ea2507daaa`.
- Verificado por HTTPS: `/api/connect` lista 0.2.24 y la descarga tiene
  el mismo SHA-256.
- Suite: `python -m pytest web/tests tests/test_package_clients.py -q`
  → **63 passed**.

## Verificación actual

- Servidor:
  - `docker exec nfs-server-dev python nfs_online.py status` → `Classic: running`, `Messenger: running in Classic`.
  - `Test-NetConnection 127.0.0.1` OK en `13505`, `20921`, `20922`, `20923`, `30920`, `30921`.
  - `runtime/classic-status.json` reporta U2 y MW habilitados y sin salas (el jugador salió).
  - `nfs-server-dev` anuncia `192.0.2.37`; `nfs-web-dev` corre en `http://192.0.2.37:8096`.
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
5. [ ] Desde la otra PC de la LAN: abrir `http://192.0.2.37:8096`, crear cuenta, descargar e instalar el pack U2 + MW.
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
