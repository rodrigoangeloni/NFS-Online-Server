# Progreso — NFS Online autoalojado

**Fecha:** 2026-11-21
**Rama:** `main`
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
| Login real | Pendiente de probar |
| Web `web/` | Pendiente de implementar |
| Debian/NPM/DuckDNS | Pendiente de desplegar |

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

## Commits de esta etapa

| Commit | Mensaje |
|---|---|
| `d130c9e` | `chore(repo): keep game media and local artifacts out of git` |
| `b7ea59e` | `docs(plan): document self-host architecture and U2/MW rollout` |
| `84bcced` | `feat(dev): run U2/MW server in Docker Desktop` |

Este documento y `AGENTS.md` forman parte de este mismo commit.

## Verificación actual

- Servidor:
  - `docker exec nfs-server-dev python nfs_online.py status` → `Classic: running`, `Messenger: running in Classic`.
  - `Test-NetConnection 127.0.0.1` OK en `13505`, `20921`, `20922`, `20923`, `30920`, `30921`.
  - `runtime/classic-status.json` reporta U2 y MW habilitados, sin salas todavía.
- Clientes:
  - Archivos presentes en ambas carpetas.
  - `dinput8.dll` idéntico en U2/MW.
  - `net_u2.ini` y `net_mw.ini` con `host = 127.0.0.1`.
- Repo:
  - Working tree: el checker ve `data/accounts.sqlite3`, `data/server-state.json`, `runtime/*.json`, `logs/*.log` y `__pycache__` del test local (ignorados por git).
  - Árbol commiteado: `git archive HEAD` + checker → OK.
  - Sin `.iso`, `.asi`, `.dll` ni `.zip` versionados.

## Pendiente inmediato

1. Abrir U2 o MW y probar login online:
   - Cuenta: `TestDriver`
   - Persona: `TestDriver`
   - Contraseña: definida localmente (no versionada).
2. Revisar `logs/classic.log` y `runtime/classic-status.json` después del login.
3. Si el cliente no engancha, revisar `net_u2.log` / `net_mw.log` en la carpeta del juego.
4. Si el login funciona, comenzar la implementación de `web/` según el plan.

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
- `python nfs_online.py status` falla en Windows (`WinError 87`); usar la versión dentro del contenedor.
- Docker Desktop no reproduce el networking exacto de Linux; la prueba final es en el Debian.
- No ejecutar `nfs_online.py stop` en Windows mientras el stack Docker está activo.
