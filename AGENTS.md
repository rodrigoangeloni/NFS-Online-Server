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
- Servidor de juego: nativo con systemd en Debian; en esta PC se prueba con Docker Desktop.
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
- [x] Web levantada en LAN (`http://192.0.2.37:8081`) dentro de Docker.
- [ ] Probar registro, descarga e instalación desde la otra PC de la LAN.
- [ ] Login online después del Widescreen Fix en MW y DSR en fullscreen.
- [ ] Probar la sala con un segundo jugador/cuenta.
- [ ] Completar web: estado en vivo completo, leaderboards, noticias/TOS y admin.
- [ ] Despliegue en Debian + NPM + DuckDNS.
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
$env:NFS_WEB_SITE_URL = "http://192.0.2.37:8081"
$env:NFS_WEB_INVITE_REQUIRED = "0"
$env:NFS_DOWNLOADS_DIR = "E:/vscode-workspace/NFS-Online-Artifacts/downloads"
docker compose -f docker/compose.dev.yml up -d --build nfs-web
```

- URL LAN: `http://192.0.2.37:8081`.
- **No** correr `uvicorn` en Windows contra la SQLite viva mientras el
  contenedor del juego la usa: produce `sqlite3.OperationalError: disk I/O error`.
  La web debe correr en Docker con el mismo bind mount `../data`.
- El puerto **8080** está ocupado por `sbrw-core`; NFS usa **8081**.
- Registro abierto en la prueba LAN (`NFS_WEB_INVITE_REQUIRED=0`). Para
  invitaciones: `python tools/create_invite.py --uses 5 --days 7`.
- Paquetes: `python tools/package_clients.py --host 192.0.2.37 ...`; salen en
  `E:\vscode-workspace\NFS-Online-Artifacts\downloads\` con `manifest.json`.
- El pack incluye `INSTALAR.bat`, `install.ps1`, `LEEME.txt`, `DESINSTALAR.bat`,
  licencias, loader y Widescreen Fix en `WindowedMode = 1`.
- Detalle: `docs/local-testing.md`.

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
- El puerto `8080` de esta PC lo ocupa `sbrw-core`; la web NFS usa `8081`.
- Para LAN, el servidor debe arrancar con `NFS_PUBLIC_HOST=192.0.2.37` y `NFS_LOCAL_IPV4=192.0.2.37`; si no, anuncia `127.0.0.1` y el cliente remoto no encuentra el lobby.

## Próximo paso

1. [x] Login de MW con `TestDriver`: `auth result=ok`, persona y Messenger autenticados, sala creada.
2. [x] Login de U2 con `TestDriver`: `auth result=ok`, `pers result=ok`, Messenger y sala `017.TestDriver`.
3. [ ] Desde la otra PC de la LAN: abrir `http://192.0.2.37:8081`, crear cuenta, descargar el pack e instalarlo.
4. [ ] Probar la sala con el segundo jugador y confirmar que el servidor anuncia `192.0.2.37`.
5. [ ] Completar la web (leaderboards, noticias/TOS, admin) y desplegar en el Debian.
