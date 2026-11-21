# NFS Online autoalojado + sitio comunitario — Diseño

**Fecha:** 2026-11-21
**Estado:** propuesta para revisión
**Repositorio:** `rodrigoangeloni/NFS-Online-Server` (fork de `moio9/NFS-Online-Server`)

## 1. Resumen

Montar el servidor **NFS Online** (Underground 2, Most Wanted 2005 y Carbon) en un Debian con IP pública, y construir un sitio web propio inspirado en [brake.go.ro](https://brake.go.ro/) que permita a amigos no técnicos:

1. Registrarse con un código de invitación.
2. Iniciar sesión con la misma cuenta que usan en el juego.
3. Descargar un paquete de cliente ya configurado para el servidor.
4. Ver el estado en vivo, salas, jugadores, leaderboards, noticias y TOS.

El servidor de juego se ejecuta de forma nativa bajo `systemd`. La web se ejecuta como un servicio **FastAPI** separado, en Docker, compartiendo la base SQLite de cuentas mediante la API oficial del repositorio. No se modifica el servidor de juego, no se usa el socket de Docker y no se mantiene un fork.

## 2. Objetivo y motivación

El objetivo real es **volver a jugar online con amigos** sin que ellos tengan que entender puertos, `.ini`, ASI loaders ni SQLite. El sitio web reduce la fricción a:

- Entrar a una URL.
- Crear una cuenta con una invitación.
- Descargar un ZIP.
- Ejecutar un `.bat`.
- Abrir el juego.

La web tipo brake.go.ro es la capa de comunidad y soporte; el servidor de juego sigue siendo la fuente de verdad.

## 3. Alcance

### Fase 1 — MVP jugable y sitio base (U2 + MW)

- Servidor clásico (U2 + MW) funcionando en Debian y validado con amigos.
- Cuentas creadas desde la web con invitación.
- Login web con la cuenta del juego.
- Landing con estado, conexión, descargas, salas y jugadores.
- Leaderboards de U2/MW (Carbon cuando se habilite).
- Páginas de News y TOS.
- Panel de administración: invitaciones, listado de cuentas, enable/disable/ban, auditoría.
- Paquetes de cliente de U2 y MW con host ya configurado; el pack completo con Carbon se genera después.
- HTTPS con Nginx Proxy Manager.
- Backups automáticos de SQLite y datos de usuario.

### Fase 1b — Carbon

- Arrancar Carbon (`--games u2,mw,carbon`), abrir sus puertos y generar su paquete.
- Añadir sus leaderboards y estado al sitio.

### Fase 2 — Paridad visual/funcional adicional

- Fotos de Carbon desde el blob store.
- Gestión de DLC de Carbon (enlazando o integrando la tienda existente).
- Social/EA Messenger (mensajes, amigos, bloqueos) usando `web_social_events`.
- Perfil ampliado y entitlements.

### No objetivos

- No se incluyen juegos, ejecutables ni assets propietarios.
- No se construye un launcher genérico ni un panel para otros juegos.
- No se copia literalmente el CSS/JS/HTML de brake.go.ro; se replica su estructura y su lenguaje visual con código propio.
- No se promete compatibilidad con servidores oficiales de EA.
- No se usa `AUTH_AUTO_ENROLL` como sustituto del registro web.

## 4. Contexto técnico

### 4.1 Lo que ya trae el repositorio

- `server/common/accounts.py`: `SQLiteAccountDatabase`, almacenamiento **process-safe** con WAL, PBKDF2-SHA256, bloqueo por intentos fallidos y sesiones activas.
- `server/common/runtime_status.py`: publica `runtime/classic-status.json` y `runtime/carbon-status.json` cada 2 s con salas y jugadores.
- `server/classic/ea/sqlite_ranking.py`: leaderboards U2/MW sobre la misma SQLite.
- `server/carbon/progression.py` + `progression_sqlite.py`: progreso y leaderboards de Carbon.
- `server/common/legal.py`: texto de TOS compartido.
- `server/carbon/web/dlc_store.py`: tienda DLC autoservicio en `127.0.0.1:8081`.
- `server/common/web_social.py`: procesa eventos sociales de la web (`game_invite`, `visibility`, `friend_request`, `message`, `report`).
- `server/common/public_presence.py`: lee la preferencia `appear_online` de la web.

### 4.2 Lo que se analizó de brake.go.ro

- Backend: **FastAPI/Uvicorn** detrás de **Caddy** (HTTP/3, TLS, cabeceras de seguridad).
- Frontend: HTML + CSS + JavaScript vanilla, sin framework ni build.
- Endpoints públicos observados:
  - `GET /api/live`
  - `GET /api/connect`
  - `GET /api/photos`
  - `GET /api/account/me`
  - `POST /api/account/register`
  - `POST /api/account/login`
  - `POST /api/account/logout`
  - `POST /api/account/preferences`
  - `GET /api/leaderboard-games`
  - `GET /api/leaderboards?game=...&category=...&limit=...`
  - `GET /api/news`
  - `GET /api/tos`
  - `GET /downloads/{id}`
- Páginas: `/`, `/leaderboards`, `/news`, `/tos`, `/account` y `/account/dlc`.
- Cuentas: la web no crea una cuenta separada; usa la misma cuenta del juego.
- Descargas: metadata con versión, tamaño, SHA-256 y URL.
- Estética: fondo `#080808`, acento rojo `#ff2a2a`, verde `#56ef91`, tipografía Inter/system, ruido, grid, tarjetas y polling cada 10 s.

### 4.3 Restricciones del repositorio

- `tools/check_public_tree.py` prohíbe binarios (`.asi`, `.dll`, `.exe`), archivos comprimidos (`.zip`) y secretos dentro del árbol versionado.
- Los ZIP de cliente y el ASI loader deben generarse en `artifacts/downloads/`, **fuera del árbol del repo**. `tools/check_public_tree.py` rechaza cualquier binario dentro del repo, incluso en `runtime/`.
- Las ISOs y archivos de juego no se versionan ni se copian al servidor. Deben quedar **fuera del árbol del repo**; `.gitignore` es solo una red de seguridad, porque `tools/check_public_tree.py` recorre el filesystem y también las vería.
- El proyecto es AGPL-3.0-or-later; el código web nuevo se publica bajo la misma licencia.
- El servidor de juego no debe modificarse para esta fase.

## 5. Decisiones de arquitectura

### 5.1 Opciones consideradas

| Opción | Descripción | Veredicto |
|---|---|---|
| **A. Web separada con la API oficial de cuentas** | FastAPI importa `SQLiteAccountDatabase` y comparte el volumen `data/`. | **Elegida.** Sin fork, sin socket Docker, usa el hashing y el WAL oficiales. |
| B. Web que envuelve el CLI | La web ejecuta `python nfs_online.py account create ...`. | Viable como respaldo, pero más lenta y frágil. |
| C. Fork con endpoint HTTP dentro del servidor | Añadir `/register` al proceso del juego. | Rechazada: mantenimiento de fork, mezcla responsabilidades y reinicios del juego para cambios web. |

### 5.2 Forma de despliegue elegida

- **Servidor de juego:** nativo, bajo `systemd`, con el launcher existente (`nfs_online.py start --daemon`). Es la opción más directa para UDP y para los procesos Classic/Carbon/Messenger.
- **Web:** contenedor Docker con FastAPI/Uvicorn, escuchando en `127.0.0.1:8096` o en una red Docker interna.
- **Proxy TLS:** Nginx Proxy Manager, que ya está instalado. Un Proxy Host para `nfs-fps.duckdns.org` hacia la web.
- **Datos compartidos:** bind mount del repositorio y de `data/`, `runtime/`, `artifacts/downloads/` y `config/`.
- **Sin** Docker socket, **sin** exponer SQLite y **sin** publicar el puerto de la web a Internet.

## 6. Arquitectura propuesta

```text
Amigos
  │  HTTPS 443
  ▼
Nginx Proxy Manager
  │  HTTP 8096 (red interna / loopback)
  ▼
nfs-web (FastAPI)
  ├─ SQLite compartida: data/accounts.sqlite3
  ├─ Estado en vivo: runtime/classic-status.json, runtime/carbon-status.json
  ├─ Leaderboards: game_player_stats / Carbon progression
  ├─ Descargas: artifacts/downloads/manifest.json + ZIPs
  └─ Contenido: TOS/News del servidor

Amigos (juego)
  │  TCP/UDP directos (puertos de abajo)
  ▼
nfs-server (nativo, systemd)
  ├─ Classic (U2 + MW) + Messenger compartido
  └─ Carbon
        │
        └─ misma SQLite y mismos runtime/*.json
```

### 6.1 Puertos

| Servicio | Protocolo | Puerto |
|---|---|---:|
| Web (detrás de NPM) | TCP | 8096 interno |
| Messenger compartido | TCP | 13505 |
| U2 bootstrap | TCP | 20921 |
| U2 lobby | TCP | 20922 |
| U2/MW web y PREL | TCP | 20923 |
| Most Wanted lobby | TCP | 30920 |
| Most Wanted bootstrap | TCP | 30921 |
| U2/MW race relay | UDP | 20000 |
| Carbon FESL | TCP | 18210 (Fase 1b) |
| Carbon Theater | TCP | 18215 (Fase 1b) |
| Carbon race transport | UDP | 19119 (Fase 1b) |
| Carbon Massive Ads | TCP | 9000 (Fase 1b) |
| DLC store (opcional) | TCP loopback | 8081 |

Solo se abren los puertos de los juegos habilitados. El 8096 de la web no se publica.

### 6.2 Componentes

- `nfs-server`: procesos existentes del repo. No se toca su código.
- `nfs-web`: aplicación nueva en `web/`.
- `nfs-web` no escribe en `runtime/`; solo lee.
- `nfs-web` escribe únicamente en `data/accounts.sqlite3` y `data/users/` mediante `SQLiteAccountDatabase`.
- `nfs-web` puede crear tablas `web_*` en la misma SQLite; el servidor las ignora o las consume cuando corresponde.

## 7. Modelo de datos web

Se crean en `data/accounts.sqlite3` con `CREATE TABLE IF NOT EXISTS`:

```sql
web_sessions(
  session_hash TEXT PRIMARY KEY,
  account_id INTEGER,                 -- NULL para sesiones de admin
  role TEXT NOT NULL DEFAULT 'player',
  csrf_token TEXT NOT NULL,
  created_at REAL NOT NULL,
  expires_at REAL NOT NULL
);

web_account_preferences(
  account_id INTEGER PRIMARY KEY,
  appear_online INTEGER NOT NULL DEFAULT 1,
  challenge_series_assist INTEGER NOT NULL DEFAULT 1,
  updated_at REAL NOT NULL
);

web_invites(
  code_hash TEXT PRIMARY KEY,
  label TEXT NOT NULL DEFAULT '',
  max_uses INTEGER NOT NULL DEFAULT 1,
  uses INTEGER NOT NULL DEFAULT 0,
  created_at REAL NOT NULL,
  expires_at REAL,
  created_by TEXT NOT NULL DEFAULT '',
  revoked_at REAL
);

web_audit_log(
  event_id INTEGER PRIMARY KEY AUTOINCREMENT,
  created_at REAL NOT NULL,
  actor TEXT NOT NULL DEFAULT '',
  action TEXT NOT NULL,
  detail_json TEXT NOT NULL DEFAULT '{}'
);
```

Notas:

- `web_sessions` mantiene las columnas que `server/common/web_social.py` espera (`session_hash`, `account_id`, `expires_at`).
- El token de cookie nunca se guarda en claro; se guarda `sha256(token)`.
- `web_account_preferences` mantiene `appear_online`, que `server/common/public_presence.py` ya lee.
- Los códigos de invitación se guardan hasheados; el código en claro se muestra una sola vez al crearlo.
- No se guardan contraseñas ni secretos en claro.

## 8. API de la web

Se replica la forma de los endpoints de brake.go.ro para que el frontend sea equivalente.

| Método | Ruta | Respuesta |
|---|---|---|
| GET | `/api/live` | `{status, rooms, players}` |
| GET | `/api/connect` | `{serverAddress, downloads[]}` |
| GET | `/api/photos` | `{photos[]}` (Fase 1: `photos: []`, `available: false`) |
| GET | `/api/account/me` | `{authenticated, secureLoginAvailable, csrfToken?, account?}` |
| POST | `/api/account/register` | misma forma que `me` |
| POST | `/api/account/login` | misma forma que `me` |
| POST | `/api/account/logout` | `{ok: true}` |
| POST | `/api/account/preferences` | `{appearOnline, syncQueued}` |
| GET | `/api/leaderboard-games` | `{games[]}` |
| GET | `/api/leaderboards` | `{game, gameName, category, categories, rows, available}` |
| GET | `/api/news` | `{available, source, feeds[]}` |
| GET | `/api/tos` | `{available, source, text}` |
| GET | `/downloads/{id}` | ZIP o 404 |
| GET | `/api/admin/...` | endpoints de administración |
| GET | `/healthz` | `{ok: true}` |

### 8.1 Registro

Payload:

```json
{
  "accountName": "Driver",
  "email": "driver@example.com",
  "password": "secreto",
  "confirmPassword": "secreto",
  "persona": "Driver",
  "countryCode": "PY",
  "appearOnline": true,
  "challengeSeriesAssist": true,
  "inviteCode": "XXXX-XXXX"
}
```

Reglas:

- `accountName`: 3–15 caracteres, letras/números/`_`/`-`. El cliente
  clásico rechaza nombres de 16 o más antes de enviarlos al servidor.
- `persona`: 3–15 caracteres, mismo conjunto; si se omite, se usa `accountName`.
- `password`: mínimo 8 caracteres.
- `email`: opcional; si se envía, validar formato y unicidad (la propia DB lo hace).
- `inviteCode`: obligatorio salvo que `NFS_WEB_INVITE_REQUIRED=0`.
- Crear la cuenta con `SQLiteAccountDatabase.create_account(...)`.
- Si la creación falla después de reservar la invitación, devolver el uso con `refund_invite` y auditar `account.register_failed`.
- Crear preferencias y sesión; devolver el mismo payload que `me`.
- Auditar `account.register`.

### 8.2 Login

- `SQLiteAccountDatabase.authenticate(identifier, password)`.
- Si `accepted` es falso, devolver 401 con mensaje genérico.
- Si la cuenta está deshabilitada o baneada, devolver 403.
- Crear sesión, devolver `csrfToken` y datos de cuenta.
- Auditar `account.login` y `account.login_failed`.

### 8.3 Preferencias

- Actualizar `web_account_preferences`.
- Insertar un evento `web_social_events` con `action='visibility'` y `source_persona` = persona primaria, para que el servidor notifique a Carbon.
- Devolver `syncQueued: true` si se insertó el evento.

### 8.4 Estado en vivo

`StatusService.live()`:

1. Leer `runtime/classic-status.json` y `runtime/carbon-status.json`.
2. Si el archivo falta o `updated_at` tiene más de 15 s, marcar el componente como offline.
3. Construir `games[]` con `id`, `game`, `name`, `shortName`, `enabled`, `online`, `players`, `rooms`, `races`, `roomStatusAvailable`. Incluir solo los juegos listados en `NFS_GAMES` (en Fase 1, `u2,mw`).
4. Agregar salas de Classic y Carbon, mapeando campos a un formato común.
5. Consultar `active_sessions` para jugadores online; aplicar `web_account_preferences.appear_online` y `carbon_public_presence`.
6. Calcular `uptime` desde `runtime/services.json.started_at` o desde el `updated_at` más antiguo disponible.
7. Devolver `status.connected = true` solo si al menos un componente está online.

### 8.5 Leaderboards

- U2/MW: `SQLiteClassicRankingStore(database).leaderboard(game, category, limit=...)`.
- Carbon: `CarbonProgressionStore(path).leaderboard_snapshot()` y ordenar por `skill`/`rep`.
- Filtrar cuentas deshabilitadas/baneadas y `game_leaderboard_visibility.hidden=1`.
- Devolver el mismo formato que brake.go.ro:
  - U2/MW: `rank`, `player`, `skill`, `wins`, `losses`, `disconnects`.
  - Carbon: `rank`, `player`, `skill`, `rep`.

### 8.6 News y TOS

- `news()`: devolver los textos de `server/classic/ea/web.py` para U2, MW y red; `carbonNewsAvailable: false` si Carbon no expone noticias.
- `tos()`: usar `common.legal.TERMS_OF_SERVICE_TEXT`.
- No se hace scraping de la web del autor.

### 8.7 Descargas

- `tools/package_clients.py` genera:
  - `artifacts/downloads/manifest.json`
  - `artifacts/downloads/NFS-Online-Client-Pack-vX.zip`
  - `artifacts/downloads/NFS-Online-U2-Client-vX.zip`
  - `artifacts/downloads/NFS-Online-MW-Client-vX.zip`
  - `artifacts/downloads/NFS-Online-CARBON-Client-vX.zip`
- El manifest tiene la forma de `/api/connect.downloads[]` con `id`, `title`, `description`, `game`, `version`, `recommended`, `available`, `filename`, `size`, `sizeLabel`, `sha256`, `downloadUrl`.
- La web sirve solo IDs del manifest y valida que la ruta resuelta esté dentro de `artifacts/downloads/`.

## 9. Frontend

### 9.1 Páginas

- `/` — landing:
  - Topbar con marca, navegación y badge LIVE.
  - Hero con título, subtítulo y stats de jugadores/uptime.
  - Server status cards.
  - Connect & downloads: dirección, botón copiar, pasos, tarjetas de descarga.
  - Active rooms & races.
  - Players online.
  - Support/contacto configurable (sin copiar los datos del autor).
- `/leaderboards` — tabs por juego, selector de modo, tabla.
- `/news` — tarjetas de noticias.
- `/tos` — texto legal.
- `/account` — registro/login/panel.
- `/admin` — panel de administración (no enlazado desde la landing).

### 9.2 Lenguaje visual

- Fondo `#080808`, paneles `#101010`/`#151515`.
- Acento rojo `#ff2a2a`, verde `#56ef91`.
- Tipografía del sistema (Inter si está instalada; fallback a `system-ui`).
- Ruido SVG sutil, grid de fondo, bordes `rgba(255,255,255,.09)`.
- Tarjetas con radios de 18–24 px, hover con borde rojo.
- Responsive: 1 columna en móvil, 2–3 en tablet, 4 en escritorio.
- Sin imágenes de juegos ni logos propietarios.

### 9.3 Comportamiento

- `app.js` hace polling cada 10 s a `/api/live`, y una vez a `/api/connect`.
- Los botones de copiar usan `navigator.clipboard` con fallback.
- `account.js` maneja registro/login/logout/preferencias.
- `leaderboards.js` consulta juegos y tablas.
- `news.js` y `tos.js` consultan sus endpoints.
- `admin.js` maneja login de admin, invitaciones y cuentas.
- Todo el HTML se escapa antes de insertarse con `innerHTML`; se usan `textContent` cuando aplica.

## 10. Paquetes de cliente

`tools/package_clients.py`:

1. Requiere los `.asi` ya compilados en `source/client-zig/zig-out/bin/` (`./build_linux.sh`).
2. Copia el `.asi` y genera el `.ini` con `host = <PUBLIC_HOST>` y `[lan] host = <PUBLIC_HOST>`.
3. Incluye un `INSTALAR.bat` que:
   - Detecta la carpeta del juego entre las rutas por defecto:
     - `%ProgramFiles(x86)%\Need for Speed Underground 2`
     - `%ProgramFiles(x86)%\Need for Speed Most Wanted 2005`
   - Si no encuentra la ruta, pide al usuario que seleccione o arrastre la carpeta del juego.
   - Copia `.asi`, `.ini` y `dinput8.dll` a la carpeta del ejecutable (`SPEED2.EXE` / `speed.exe`).
   - Si la carpeta está en `Program Files (x86)`, se auto-eleva con UAC o pide “Ejecutar como administrador”.
   - Si ya existe un `dinput8.dll` u otro loader, lo respalda antes de copiar y avisa.
   - Verifica que los tres archivos quedaron en la carpeta.
4. Incluye `LEEME.txt` con tres pasos.
5. Incluye `dinput8.dll` (Ultimate ASI Loader 32-bit, MIT) con atribución y licencia. Se obtiene del release oficial de ThirteenAG:
   - `https://github.com/ThirteenAG/Ultimate-ASI-Loader/releases/download/v10.0.4/Ultimate-ASI-Loader-NoPDB.zip` (32-bit, contiene `dinput8.dll`).
   - No usar `_x64` ni `-NoPDB_x64`.
   - Verificar el SHA-512 publicado antes de empaquetar.
   - SHA-256 verificado de `dinput8.dll` (NoPDB v10.0.4): `73D6DB0481AF99B8481E8E6A685DD385E5A3E0E10518BFE97A993F7F368667EB`.
   - Los `.asi` se compilan desde `source/client-zig` con Zig 0.16.0; el release upstream `nfs-online-client.zip` es una alternativa, pero puede estar desactualizado. La compilación local en WSL produjo los mismos SHA-256 que el release 0.1: U2 `8DB6557E...`, MW `35B6C620...`, Carbon `FBACD6C5...`.
6. Comprime en `artifacts/downloads/` y calcula SHA-256.
7. Escribe `manifest.json` de forma atómica.

El script no se ejecuta en CI con binarios; los ZIP se generan en el servidor.

## 11. Despliegue

### 11.1 Directorios en Debian

```text
/opt/nfs-online/
  repo/                 # git clone del fork
  data/                 # bind mount / volumen (SQLite, usuarios)
  runtime/              # estado en vivo del juego (JSON, PID)
  artifacts/downloads/  # ZIPs y manifest generados, fuera del repo
  logs/                 # logs del launcher
  env/nfs.env           # variables de entorno (no versionado)
```

### 11.2 Servidor de juego

Unidad `nfs-online.service`:

- `Type=oneshot`
- `RemainAfterExit=yes`
- `WorkingDirectory=/opt/nfs-online/repo`
- `ExecStart=/opt/nfs-online/venv/bin/python nfs_online.py start --games u2,mw --daemon` (Fase 1; en Fase 1b se cambia a `u2,mw,carbon`)
- `ExecStop=/opt/nfs-online/venv/bin/python nfs_online.py stop`
- `User=nfs`
- `EnvironmentFile=/opt/nfs-online/env/nfs.env` con `NFS_GAMES=u2,mw`

Watchdog `nfs-watchdog.timer` cada 5 minutos:

- Ejecuta `deploy/healthcheck.sh`, que comprueba solo los puertos de `NFS_GAMES`.
- Si devuelve 1, ejecuta `systemctl restart nfs-online.service`.

### 11.3 Web

`web/Dockerfile`:

- Base `python:3.12-slim`.
- Instala `web/requirements.txt`.
- Copia `web/` y `server/` (solo para imports).
- Ejecuta `uvicorn web.app:app --host 0.0.0.0 --port 8080 --proxy-headers`.

`docker/compose.web.yml`:

- `nfs-web`
- `ports: ["127.0.0.1:8096:8080"]`
- Volúmenes:
  - `../data:/app/data`
  - `../runtime:/app/runtime:ro`
  - `../config:/app/config:ro`
  - `../server:/app/server:ro`
  - `../web/static:/app/web/static:ro`
- `env_file: ../env/nfs.env`
- `restart: unless-stopped`

### 11.4 DNS con DuckDNS

- Subdominio decidido: `nfs-fps.duckdns.org`.
- Crear/actualizar el registro A de DuckDNS para que apunte a la IP pública del Debian.
- Si la IP es fija, basta con configurarla una vez en el panel de DuckDNS.
- Si la IP puede cambiar, ejecutar un updater cada 5 minutos con el token de DuckDNS guardado en `env/nfs.env` (nunca en git).
- Verificar con `dig +short nfs-fps.duckdns.org` que devuelve la IP pública.
- Usar el mismo nombre en `PUBLIC_HOST` del servidor de juego y en `NFS_WEB_PUBLIC_HOST` de la web.

### 11.5 NPM

- Proxy Host `nfs-fps.duckdns.org` → `http://127.0.0.1:8096`.
- SSL Let's Encrypt, Force SSL, HTTP/2, HSTS opcional.
- Access List solo para `/admin` si se desea una capa extra.
- No se publica el 8096.

### 11.6 Firewall

- `ufw allow 80/tcp`, `443/tcp`.
- Puertos de juego según los juegos habilitados.
- `ufw` no debe exponer 8096, 8081, 13506 ni la SQLite.

### 11.7 Backups

- `sqlite3 data/accounts.sqlite3 ".backup '...'"` antes de cada actualización.
- Backup diario de `data/`, `config/` y `artifacts/downloads/manifest.json`.
- Verificación semanal con `PRAGMA integrity_check`.

### 11.8 Pruebas locales con Docker Desktop

Docker Desktop en Windows permite probar el stack antes de desplegar en Debian.

- `docker/compose.dev.yml` levanta dos servicios:
  - `nfs-server`: imagen Linux con el repo montado, `--games u2,mw`, puertos TCP `13505/20921/20922/20923/30920/30921` y UDP `20000`.
  - `nfs-web`: FastAPI en `http://localhost:8096`, con `NFS_WEB_ALLOW_INSECURE=1` para pruebas locales.
- Bind mounts `./data`, `./runtime` y `./artifacts/downloads` compartidos entre ambos contenedores (runtime y descargas montados read-only en la web), para poder inspeccionar la SQLite y generar los ZIP desde el host. Si SQLite WAL da problemas de locking en Windows, cambiar a volúmenes nombrados.
- En dev, ambos contenedores usan el mismo UID (o root) para que `data/` sea escribible; en producción la web usa el UID del usuario `nfs`.
- Para probar en el mismo PC: `NFS_PUBLIC_HOST=127.0.0.1` y `NFS_LOCAL_IPV4=127.0.0.1`.
- Para probar con amigos en la LAN: usar la IP LAN del Windows host en `NFS_PUBLIC_HOST`/`NFS_LOCAL_IPV4` y abrir los puertos publicados.
- La web local no usa NPM; se prueba por HTTP. La prueba con HTTPS/NPM y el reinicio real se hace en Debian.
- Docker Desktop no reproduce exactamente el host networking de Linux; la prueba final siempre es en el Debian con IP pública.

## 12. Seguridad

- HTTPS obligatorio para registro/login; el backend rechaza HTTP salvo `NFS_WEB_ALLOW_INSECURE=1` en desarrollo.
- Cookies `HttpOnly`, `Secure`, `SameSite=Lax`, `Path=/`.
- CSRF token por sesión, requerido en todos los POST.
- Rate limit por IP en registro/login (5 intentos/minuto).
- Códigos de invitación hasheados, con usos y expiración.
- Validación estricta de nombres/personas; sin HTML.
- Panel admin con contraseña propia (hash PBKDF2) y, opcionalmente, Access List de NPM.
- Cabeceras: `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `Referrer-Policy: same-origin`, `Permissions-Policy` restrictiva.
- Logs sin contraseñas ni tokens.
- No se exponen `data/` ni `runtime/` por NPM.
- La web corre como usuario sin privilegios en el contenedor.

## 13. Fases y criterios de aceptación

### Fase 1

- [ ] El servidor arranca al boot y sobrevive a un reinicio.
- [ ] El stack U2/MW + web funciona en Docker Desktop antes de desplegar.
- [ ] `nfs-fps.duckdns.org` resuelve a la IP pública y NPM sirve HTTPS.
- [ ] Los puertos de U2/MW responden desde fuera de la red.
- [ ] Un amigo crea una cuenta con invitación, inicia sesión y descarga el ZIP de U2 o MW.
- [ ] El ZIP instala `.asi` + `.ini` + `dinput8.dll` y el juego entra al lobby.
- [ ] La landing muestra estado, salas y jugadores en vivo.
- [ ] Leaderboards de U2/MW, News y TOS responden.
- [ ] El admin puede crear/revocar invitaciones y banear cuentas.
- [ ] NPM sirve HTTPS y no expone la web directamente.
- [ ] Los backups se generan y restauran en una prueba.

### Fase 1b — Carbon

- [ ] Carbon arranca con `--games u2,mw,carbon`.
- [ ] Los puertos 18210/18215/19119/9000 responden.
- [ ] El paquete de Carbon y sus leaderboards aparecen en el sitio.

### Fase 2

- [ ] Fotos de Carbon visibles y paginadas.
- [ ] DLC de Carbon gestionable desde la cuenta.
- [ ] Mensajes/amigos funcionando vía `web_social_events`.
- [ ] Perfil ampliado con entitlements.

## 14. Decisiones abiertas

1. **Dominio/subdominio:** decidido `nfs-fps.duckdns.org`.
2. **Juegos de la primera prueba:** decidido U2/MW (ya instalados); Carbon en Fase 1b.
3. **Alcance inicial:** Fase 1 o réplica completa desde el inicio.
4. **ASI loader:** incluir `dinput8.dll` MIT en el ZIP (recomendado) o enlazarlo aparte.
5. **Web en Docker o nativa:** recomendado Docker; nativa es alternativa si se quiere evitar el contenedor.

## 15. Referencias

- Repositorio: `https://github.com/moio9/NFS-Online-Server`
- Web de referencia: `https://brake.go.ro/`
- Ultimate ASI Loader: `https://github.com/ThirteenAG/Ultimate-ASI-Loader` (MIT)
