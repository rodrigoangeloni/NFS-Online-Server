# AGENTS.md — NFS Online Server (fork de el operador)

Este archivo es el contexto operativo para futuros agentes que trabajen en este fork.
La documentación completa del proyecto está en:

- Diseño: `docs/superpowers/specs/2026-11-21-nfs-online-selfhost-design.md`
- Plan de implementación: `docs/superpowers/plans/2026-11-21-nfs-online-selfhost.md`
- Progreso cronológico: `docs/PROGRESS.md`

## Objetivo actual

Volver a jugar online con amigos a **Need for Speed Underground 2** y **Most Wanted (2005)** en un servidor Debian con IP pública, y construir una web comunitaria propia inspirada en [brake.go.ro](https://brake.go.ro/).

- Fase 1: **U2 + MW**. Carbon queda para Fase 1b.
- Dominio decidido: **`nfs-fps.duckdns.org`**.
- Web: FastAPI + Uvicorn en Docker, compartiendo la SQLite oficial de cuentas.
- Servidor de juego: contenedor Docker `nfs-server` en Debian; systemd queda deshabilitado.
- Proxy TLS: Nginx Proxy Manager (ya instalado en el Debian).

## Decisiones de arquitectura

1. La web es un servicio separado y usa `SQLiteAccountDatabase` del repo; no hay fork del servidor, no se usa el socket de Docker y no se escribe en el estado del juego.
2. El registro usa invitaciones y la misma cuenta del juego.
3. La landing lee `runtime/classic-status.json` y `runtime/carbon-status.json`.
4. Los leaderboards U2/MW salen de `SQLiteClassicRankingStore`; Carbon de su SQLite de progreso.
5. Los `.asi` se compilan con Zig 0.16.0; el loader es Ultimate ASI Loader 32-bit.
6. Los binarios, ZIPs e ISOs **nunca** van dentro del repo. `tools/check_public_tree.py` recorre el filesystem y rechaza binarios incluso en `runtime/`.

## Estado actual (2026-11-21)

- [x] Diseño y plan escritos en `docs/superpowers/`.
- [x] Repo limpio de ISOs; movidos a `E:\vscode-workspace\NFS-Online-ISOs`.
- [x] Loader 32-bit descargado y verificado.
- [x] Clientes `.asi` actuales compilados desde fuente en WSL y verificados.
- [x] Stack local `nfs-server` en Docker Desktop con U2/MW.
- [x] Cuenta local de prueba `TestDriver` creada (contraseña definida localmente, no versionada).
- [x] Clientes instalados en las carpetas de U2/MW con UAC; hashes verificados.
- [x] El árbol commiteado pasa `tools/check_public_tree.py`.
- [x] Login real de **MW** verificado: `auth result=ok`, persona `TestDriver`, Messenger autenticado y sala creada.
- [x] Login real de **U2** verificado: `auth result=ok`, `pers result=ok`, Messenger `underground2-classic-messenger` y sala `017.TestDriver` creada.
- [x] `runtime/classic-status.json` publicó salas de U2 (`players=1`, `capacity=6`, `state=OPEN`).
- [x] Widescreen Fix instalado en U2/MW (solo `scripts/`; el `dinput8.dll` actual no se tocó).
- [x] U2 probado en ventana 1920x1080 (`WindowedMode=3`) y con resolución DSR 2560x1440.
- [x] Login online de U2 verificado después del fix, con `WindowedMode=1` borderless y sala `034.TestDriver`.
- [x] MVP de `web/`: registro, login, sesiones, descargas, landing y página de cuenta.
- [x] Paquetes de cliente U2/MW generados con el fix borderless e instalador para no técnicos.
- [x] Web levantada en LAN (`http://192.0.2.37:8096`) dentro de Docker.
- [x] Registro, descarga e instalación desde la otra PC de la LAN verificados.
- [x] Sala U2 `016.TestDriver` con 2 jugadores (`DriverD`, `TestDriver`) y carrera sincronizada.
- [x] Debian desplegado: juego Docker + web Docker + NPM y HTTPS público.
- [x] `https://nfs-fps.duckdns.org` sirve landing, cuenta, descargas y registro con invitación.
- [x] Panel admin `/admin`: login, listar, crear y revocar invitaciones.
- [x] Cambio de contraseña de usuario y de admin desde la web.
- [x] Recuperación con cuenta + email + código y reset desde `/admin`.
- [x] Email obligatorio para cuentas nuevas.
- [ ] Probar una partida completa desde fuera de la LAN (UDP `20000-20005`).
- [ ] Login online después del Widescreen Fix en MW y DSR en fullscreen.
- [ ] Completar web: estado en vivo completo, leaderboards y noticias/TOS.
- [ ] Fase 1b: Carbon.

## Artefactos locales (esta PC)

No están versionados:

```text
E:\vscode-workspace\NFS-Online-ISOs\
  Need for Speed Most Wanted 1.3.iso
  Need for Speed Underground 2.iso

E:\vscode-workspace\NFS-Online-Artifacts\
  vendor\Ultimate-ASI-Loader\dinput8.dll
  vendor\nfs-online-client-current\   # build actual desde source
  vendor\nfs-online-client-0.1\       # release upstream
  staging\U2\                         # dinput8.dll + net_u2.asi/.ini
  staging\MW\                         # dinput8.dll + net_mw.asi/.ini
  install-clients.ps1
  install-log.txt
  downloads\                          # ZIPs finales + manifest.json
  vendor\widescreen-fixes\            # releases U2/MW
```

Hashes verificados:

- `dinput8.dll` (NoPDB v10.0.4, 32-bit): `73D6DB0481AF99B8481E8E6A685DD385E5A3E0E10518BFE97A993F7F368667EB`
- `net_u2.asi`: `8DB6557E685CF2DD47F825E62CC202CBACE85F6CC4A43AF271B8238E0367A04F`
- `net_mw.asi`: `35B6C620D635224596BEA1D484F6D9AF983426D6A8F621EAE35AACA53FF4A7DE`
- `net_carbon.asi`: `FBACD6C5C30B64399F1FF96AC19BF325136D30A532072160A1D1FA36BAEABBE9`

## Juegos instalados en esta PC

```text
C:\Program Files (x86)\Need for Speed Underground 2\
  SPEED2.EXE
  dinput8.dll
  net_u2.asi
  net_u2.ini   (host = 127.0.0.1)

C:\Program Files (x86)\Need for Speed Most Wanted 2005\
  speed.exe
  dinput8.dll
  net_mw.asi
  net_mw.ini   (host = 127.0.0.1)
```

Los `.ini` se cambiarán a `nfs-fps.duckdns.org` para el paquete público.
No sobrescribir un loader existente (`dinput8.dll`, `dsound.dll`, `version.dll`, etc.) sin respaldarlo.

## Comandos de desarrollo local

```powershell
# Levantar servidor U2/MW en Docker Desktop
docker compose -f docker/compose.dev.yml up -d --build

# Estado y logs
docker exec nfs-server-dev python nfs_online.py status
docker logs nfs-server-dev --tail 80
Get-Content logs\classic.log -Tail 80

# Apagar
docker compose -f docker/compose.dev.yml down

# Verificación del árbol público.
# El checker recorre el filesystem, no git: con el stack local corriendo
# también ve data/, runtime/, logs/ y __pycache__. Verificar sobre lo commiteado:
git archive HEAD --format=zip -o "$env:TEMP\nfs-clean.zip"
Expand-Archive "$env:TEMP\nfs-clean.zip" "$env:TEMP\nfs-clean" -Force
python tools/check_public_tree.py "$env:TEMP\nfs-clean"
```

No ejecutar `python nfs_online.py stop` en Windows mientras el stack Docker está activo: el `runtime/services.json` contiene PIDs del contenedor y el launcher de Windows puede interpretarlos mal. Usar `docker compose down`.

## Compilar clientes

El build oficial requiere Zig 0.16.0 y Linux. En esta PC se usó WSL Debian:

```bash
cd source/client-zig
./build_linux.sh
```

El script descarga Zig en `.tools/` y luego `check_source.py` puede fallar al escanear ese directorio. Workaround usado:

1. Copiar `source/client-zig` y `clients/` a un árbol temporal que respete `<repo>/source/client-zig`.
2. Descargar Zig 0.16.0 fuera del árbol.
3. Ejecutar `ZIG=/ruta/zig ./build_linux.sh`.
4. Copiar `zig-out/bin/net_*.asi` a `E:\vscode-workspace\NFS-Online-Artifacts\vendor\nfs-online-client-current\`.

El `file` final del script no es necesario; el audit PE (`tools/audit_pe.py`) sí debe pasar.

## Protocolo de pruebas y commits

Cada cambio debe seguir este ciclo:

1. **Test primero cuando aplique:** unitario o de integración antes de la implementación.
2. **Ejecutar la prueba** y guardar el comando y el resultado.
3. **Documentar** el resultado en `docs/PROGRESS.md` (qué se probó, resultado, limitaciones).
4. **Commit detallado** con cuerpo: qué cambió, qué tests se corrieron y qué queda pendiente.

Matriz de pruebas:

| Nivel | Herramienta | Alcance |
|---|---|---|
| Unitario | `pytest` | Servicios web, cuentas, descargas, leaderboards, empaquetado |
| Integración | `pytest` + `TestClient` + SQLite temporal | API, sesiones, CSRF, registro/login |
| Docker | `docker compose`, `docker exec`, logs, puertos | Servidor U2/MW, persistencia, reinicio |
| Navegador | Playwright / browser | Landing, registro, cuenta, leaderboards, admin |
| Juego | Lanzar U2/MW + `native-devtools` si hace falta | Login, lobby, sala visible en logs/status |
| Árbol público | `git archive HEAD` + `tools/check_public_tree.py` | Que no se versionen binarios ni datos |

Reglas:

- No commitear `data/`, `runtime/`, `logs/`, `__pycache__`, binarios, ZIPs, ISOs ni credenciales.
- Para el juego, la fuente de verdad son `logs/classic.log`, `runtime/classic-status.json` y `net_u2.log`/`net_mw.log`; la automatización de escritorio es solo un medio.
- Si una prueba del juego requiere tomar mouse/teclado, pedir confirmación antes.
- Un commit por paso lógico, con mensaje `tipo(scope): resumen` y cuerpo con tests y resultados.

## Widescreen Fix (U2/MW)

- Instalado en `scripts/` de cada juego; solo se copiaron `.asi`, `.ini` y `.dat`/`.tpk`.
- **No** se reemplazó el `dinput8.dll` actual.
- U2 `NFSUnderground2.WidescreenFix.ini`: `WindowedMode = 1`, `SkipIntro = 1`, `NoOpticalDriveFix = 1`.
- MW `NFSMostWanted.WidescreenFix.ini`: `WindowedMode = 1`, `SkipIntro = 1`.
- Resultado U2: `WindowedMode = 1` abre borderless 1920x1080 en (0,0) y tapa la barra de tareas; la lista de resolución incluye 2560x1440 (DSR) y se aplicó.
- `Win+Shift+Left/Right` no mueve la ventana borderless porque el juego captura la tecla Windows; `WindowedMode = 3` sí se puede arrastrar pero muestra borde y barra de tareas.
- Para multi-monitor: `WindowedMode = 3`; para DSR: `WindowedMode = 0` + resolución DSR.
- Detalle y fuentes: `docs/research/2026-11-21-nfs-widescreen-dsr.md`.

## Web local (`web/`)

- MVP en la rama `feat/web-mvp`: FastAPI + SQLite compartida.
- Módulos: `web/config.py`, `web/db.py`, `web/accounts.py`, `web/downloads.py`,
  `web/api.py`, `web/security.py`, `web/app.py`.
- Frontend: `web/static/index.html`, `account.html`, `styles.css`, `app.js`,
  `account.js`.
- Prueba completa: `python -m pytest web/tests tests/test_package_clients.py -q`
  → 34 passed.
- Correr en Docker (recomendado):

```powershell
$env:NFS_PUBLIC_HOST = "192.0.2.37"
$env:NFS_LOCAL_IPV4 = "192.0.2.37"
$env:NFS_WEB_PUBLIC_HOST = "192.0.2.37"
$env:NFS_WEB_SITE_URL = "http://192.0.2.37:8096"
$env:NFS_WEB_INVITE_REQUIRED = "0"
$env:NFS_DOWNLOADS_DIR = "E:/vscode-workspace/NFS-Online-Artifacts/downloads"
docker compose -f docker/compose.dev.yml up -d --build nfs-web
```

- URL LAN: `http://192.0.2.37:8096`.
- **No** correr `uvicorn` en Windows contra la SQLite viva mientras el
  contenedor del juego la usa: produce `sqlite3.OperationalError: disk I/O error`.
  La web debe correr en Docker con el mismo bind mount `../data`.
- El puerto **8080** está ocupado por `sbrw-core`/NFS World; Assetto ocupa `8081-8088`; NFS usa **8096**.
- Registro abierto en la prueba LAN (`NFS_WEB_INVITE_REQUIRED=0`). Para
  invitaciones: `python tools/create_invite.py --uses 5 --days 7`.
- Paquetes: `python tools/package_clients.py --host 192.0.2.37 ...`; salen en
  `E:\vscode-workspace\NFS-Online-Artifacts\downloads\` con `manifest.json`.
- El pack incluye `INSTALAR.bat`, `install.ps1`, `LEEME.txt`, `DESINSTALAR.bat`,
  licencias, loader y Widescreen Fix en `WindowedMode = 1`.
- Detalle: `docs/local-testing.md`.

## Producción en Debian

- Ruta: `/opt/nfs-online/repo` (código), `data/`, `runtime/`, `logs/`,
  `artifacts/downloads/`, `env/nfs.env`.
- Juego: contenedor `nfs-server` (UID 1000, DNS `1.1.1.1`), anuncia
  `nfs-fps.duckdns.org` y `<IP publica>`; systemd deshabilitado.
- Stack: `nfs-online` con `nfs-server` + `nfs-web`; en Portainer se ven
  en **Containers** (proyecto `nfs-online`).
- DNS: el router tiene Static DNS de los dominios a `192.0.2.200`
  para la LAN; es intencional. `nfs-server` usa `dns: 1.1.1.1` para
  anunciar la IP pública. El contenedor `duckdns` actualiza
  `nextcloud-<usuario>`; `duckdns-nfs` actualiza `nfs-fps` con su token.
- Web: contenedor `nfs-web`, loopback `127.0.0.1:8096`, red
  `nginx-proxy-manager-new_default` como `nfs-web:8080`.
- NPM: `nfs-fps.duckdns.org` → `http://nfs-web:8080`, Force SSL y HTTP/2.
- HTTPS público verificado: `/healthz`, landing, `/account`, `/api/connect`
  y descarga con SHA-256 correcto.
- UFW: abiertos TCP `13505`, `20921-20923`, `30920-30921` y UDP
  `20000-20005`; `8096` queda en loopback.
- TCP de juego verificados desde Internet; falta la prueba de carrera
  externa para confirmar UDP.
- Panel admin: `https://nfs-fps.duckdns.org/admin`; usuario `admin` y
  clave hasheada en `NFS_WEB_ADMIN_PASSWORD_HASH` dentro de
  `/opt/nfs-online/env/web.env` (solo como semilla) y luego en SQLite.
- Invitaciones: el panel lista el código, usos, vencimiento y estado;
  permite crear y revocar. El código se guarda en la SQLite para poder
  consultarlo después (además del hash).
- Recuperación: cuenta + email + código `NFS-REC-...`; la web muestra
  una temporal `NFS-TMP-...` válida 24 h y obliga a cambiarla. El admin
  puede resetear cualquier cuenta desde el panel.
- Email obligatorio para cuentas nuevas; las viejas lo cargan desde
  `/account`.
- Anti-spam: 5 intentos por minuto por IP real para login, registro,
  recuperación y login admin. La IP real se toma de `X-Real-IP`
  (`X-Forwarded-For` como respaldo) solo desde
  `NFS_WEB_TRUSTED_PROXY_IPS=172.28.0.0/16` (red de NPM).
- Runbook: `docs/deployment.md`. Actualización: `deploy/update.sh`.

## Automatización del juego en Windows

El juego ignora la entrada sintética si la ventana no está en primer plano. La secuencia que funcionó:

1. `SetForegroundWindow` + `BringWindowToTop` sobre `speed.exe`/`SPEED2.EXE`.
2. Navegar con scancodes (`keybd_event` con el flag extendido para flechas).
3. Seleccionar el campo, pulsar **Enter** para entrar en modo edición.
4. Escribir con `keybd_event` usando **VK + scancode** (no solo scancode).
5. Navegar al siguiente campo con **Down** y repetir.
6. Seleccionar `Continuar` y pulsar **Enter**.

Los clics sintéticos no son fiables para los campos de texto; el teclado sí. Para verificar el resultado, usar `logs/classic.log` y `runtime/classic-status.json`, no solo la pantalla.

## Problemas conocidos

- **U2:** el chequeo de **Disc 2** quedó resuelto externamente por el usuario. El ISO disponible es el instalador ElAmigos, no el disco de juego.
- **MW:** los videos `attract_movie_*`, `ealogo_*` y `psa_*` de `MOVIES` están renombrados a `.bak` para saltar el intro. Es reversible.
- **U2:** `FMVOpening.vp6`, `ealogo.vp6`, `PSA.vp6` y `THX_logo.vp6` de `MOVIES` están renombrados a `.bak` por el mismo motivo. Es reversible.
- `python nfs_online.py status` falla en Windows con `OSError: [WinError 87]` en `os.kill(pid, 0)`. Usar `docker exec nfs-server-dev python nfs_online.py status`.
- El servidor lanzado con `start --daemon` en Windows no sobrevive al cierre del comando; por eso se usa Docker Desktop.
- Los juegos son repacks de ElAmigos. Si el `.exe` fue modificado por el No-CD, los offsets del plugin pueden no coincidir. Si el cliente no engancha, probar con un ejecutable original 1.2/1.3.
- Docker Desktop no reproduce exactamente el host networking de Linux; la validación final es en el Debian.
- La web NFS corre en Docker y comparte `data/accounts.sqlite3` con el servidor. No ejecutar `uvicorn` en Windows contra esa base mientras el contenedor está activo: aparecen `disk I/O error`.
- El puerto `8080` lo usa NFS World; Assetto ocupa `8081-8088`; la web NFS usa `8096` en loopback.
- En Debian, NPM debe apuntar a `nfs-web:8080` (red Docker), no a `192.0.2.200:8096`. El bind loopback es lo que evita exponer la web sin TLS.
- Para LAN, el servidor debe arrancar con `NFS_PUBLIC_HOST=192.0.2.37` y `NFS_LOCAL_IPV4=192.0.2.37`; si no, anuncia `127.0.0.1` y el cliente remoto no encuentra el lobby.

## Próximo paso

1. [x] Login de MW con `TestDriver`: `auth result=ok`, persona y Messenger autenticados, sala creada.
2. [x] Login de U2 con `TestDriver`: `auth result=ok`, `pers result=ok`, Messenger y sala `017.TestDriver`.
3. [x] Desde la otra PC de la LAN: cuenta `driver4`/`DriverD`, descarga e instalación del pack, entrada a la sala.
4. [x] Sala `016.TestDriver` con 2 jugadores y carrera sincronizada; relay UDP `20000` con dos clientes.
5. [ ] Completar la web (leaderboards, noticias/TOS, admin) y desplegar en el Debian.
