# NFS Online Server · Comunidad Underground 2 + Most Wanted

Servidor comunitario **self-hosted** para Need for Speed: Underground 2 y Most Wanted (2005): juego online, cuentas, descargas y panel de administración, con clientes ASI, web FastAPI y despliegue Docker.

<p align="center">
  <a href="https://nfs-fps.duckdns.org">
    <img src="https://nfs-fps.duckdns.org/og-image.jpg" alt="NFS Online: Underground 2 y Most Wanted" width="900">
  </a>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.10%2B-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python 3.10+">
  <img src="https://img.shields.io/badge/FastAPI-009688?style=for-the-badge&logo=fastapi&logoColor=white" alt="FastAPI">
  <img src="https://img.shields.io/badge/Docker-2496ED?style=for-the-badge&logo=docker&logoColor=white" alt="Docker">
  <img src="https://img.shields.io/badge/SQLite-003B57?style=for-the-badge&logo=sqlite&logoColor=white" alt="SQLite">
  <img src="https://img.shields.io/badge/Zig-0.16-F7A41D?style=for-the-badge&logo=zig&logoColor=black" alt="Zig 0.16">
  <img src="https://img.shields.io/badge/License-AGPL--3.0--or--later-c9f53b?style=for-the-badge" alt="AGPL-3.0-or-later">
</p>

<p align="center">
  <a href="https://nfs-fps.duckdns.org"><img src="https://img.shields.io/badge/Servidor-nfs--fps.duckdns.org-c9f53b?style=for-the-badge" alt="Servidor público"></a>
</p>

---

## Contenido

- [Servidor público](#servidor-público)
- [Qué es](#qué-es)
- [Características](#características)
- [Tecnologías](#tecnologías)
- [Estructura del proyecto](#estructura-del-proyecto)
- [Puesta en marcha](#puesta-en-marcha)
- [Clientes y pack](#clientes-y-pack)
- [Pruebas](#pruebas)
- [Despliegue](#despliegue)
- [Estado del proyecto](#estado-del-proyecto)
- [Soporte y contribución](#soporte-y-contribución)
- [Créditos](#créditos)
- [Licencia](#licencia)

## Servidor público

| | |
|---|---|
| **Web** | [nfs-fps.duckdns.org](https://nfs-fps.duckdns.org) |
| **Cuenta** | [Crear cuenta / iniciar sesión](https://nfs-fps.duckdns.org/account) |
| **Descargas** | [Pack U2 + MW](https://nfs-fps.duckdns.org/#descargas) |
| **Juego** | `nfs-fps.duckdns.org` (U2 y MW) |

- El registro es con **invitación**; pedila al operador.
- El pack incluye el cliente ASI, el ASI Loader y el Widescreen Fix. **No incluye los juegos**: usá tu copia de U2/MW.
- Los jugadores solo descargan el pack, ejecutan `INSTALAR.bat` y abren el juego. El instalador configura el host; no hay que editar INIs a mano.
- Fase actual: **U2 + MW**. Carbon queda para la Fase 1b.

## Qué es

Este repositorio es un **fork self-hosted** de [NFS-Online-Server](https://github.com/moio9/NFS-Online-Server). Mantiene el servidor de juego (protocolos de U2/MW, Messenger, lobby y relay UDP) y agrega lo necesario para operar una comunidad:

- una **web FastAPI** que comparte la SQLite de cuentas con el servidor;
- **descargas** con manifiesto y SHA-256;
- **panel de administración** de invitaciones, cuentas, reset y ban;
- **empaquetado** del cliente para Windows con instalador;
- **Docker Compose** para el servidor y la web;
- runbook de despliegue con Nginx Proxy Manager, DuckDNS y UFW.

La web no escribe en el estado del juego: lee `runtime/classic-status.json` y las tablas compartidas de cuentas y estadísticas. El servidor de juego sigue siendo la fuente de verdad (`logs/classic.log`, `runtime/classic-status.json`).

## Características

| | |
|---|---|
| 🎮 | **U2 y MW online** — login, personas, Messenger, salas y carreras. Relay UDP probado con jugadores fuera de la LAN. |
| 👤 | **Cuentas** — registro con invitación, login, sesiones, CSRF, email obligatorio, recuperación y cambio de contraseña. Cuentas y personas de 3–15 caracteres. |
| 🛠️ | **Panel admin** — invitaciones, reset de contraseña, ban/desban y auditoría de acciones. |
| 📦 | **Pack de cliente** — `INSTALAR.bat`, `host.txt`, Ultimate ASI Loader y Widescreen Fix. El instalador fuerza el host en U2/MW. |
| 🖥️ | **Estado en vivo** — la landing lee `runtime/classic-status.json` y muestra las salas U2/MW. |
| 🐳 | **Docker** — `nfs-server` + `nfs-web`; NPM/DuckDNS; actualización con `deploy/update.sh`. |
| 🖼️ | **Social preview** — Open Graph/Twitter con imagen 1200×630 servida por la web. |
| 🧪 | **Pruebas** — suite web/empaquetado con pytest, tests de protocolo/CLI y checker del árbol público. |

## Tecnologías

| Tecnología | Uso |
|---|---|
| Python 3.10+ | servidor de juego, CLI y web |
| FastAPI + Uvicorn | cuentas, API, descargas y admin |
| SQLite | cuentas, sesiones, estadísticas y progreso |
| Docker Compose | stack `nfs-server` + `nfs-web` |
| Zig 0.16 | clientes `net_u2.asi`, `net_mw.asi`, `net_carbon.asi` |
| HTML/CSS/JS | frontend sin framework |
| Nginx Proxy Manager + DuckDNS | TLS y DNS del dominio público |
| pytest + unittest | web, empaquetado, CLI y protocolos |

## Estructura del proyecto

```text
.
├── nfs_online.py            # CLI del servidor
├── start.sh                 # arranque rápido
├── config/server.toml       # configuración única
├── server/                  # protocolos U2/MW/Carbon
├── web/                     # FastAPI, frontend y tests
├── clients/                 # plantillas net_*.ini
├── source/client-zig/       # clientes ASI en Zig
├── packaging/client/        # instalador para jugadores
├── tools/                   # empaquetado, invitaciones, OG, chequeos
├── docker/                  # compose y Dockerfiles
├── deploy/                  # env de ejemplo, DuckDNS y update.sh
├── docs/                    # despliegue, progreso e investigación
└── tests/                   # tests de CLI, reportes y empaquetado
```

`data/`, `runtime/` y `logs/` se generan al correr el servidor y no se versionan (salvo los `.gitkeep` y los assets de Carbon).

## Puesta en marcha

### Requisitos

- **Docker + Docker Compose** para el stack completo (recomendado).
- **Python 3.10+** si corrés el servidor sin Docker.
- **Zig 0.16.0** solo para recompilar los clientes ASI.
- Los **archivos del juego** (U2/MW) no se incluyen.

### Docker (recomendado)

```bash
git clone https://github.com/rodrigoangeloni/NFS-Online-Server.git
cd NFS-Online-Server
docker compose -f docker/compose.dev.yml up -d --build
```

- Web local: `http://localhost:8096`.
- Servidor de juego: los puertos de la tabla de abajo.
- Estado: `docker exec nfs-server-dev python nfs_online.py status`.
- Logs: `docker logs nfs-server-dev --tail 80` y `tail -n 80 logs/classic.log`.
- Para LAN/Internet, configurá `NFS_PUBLIC_HOST`, `NFS_LOCAL_IPV4`, `NFS_WEB_PUBLIC_HOST` y `NFS_WEB_SITE_URL`; el detalle está en [docs/local-testing.md](docs/local-testing.md).

El registro local se abre con `NFS_WEB_INVITE_REQUIRED=0`; en producción va en `1` y se usan invitaciones.

### Servidor nativo

```bash
python nfs_online.py check
python nfs_online.py configure --public-host nfs-fps.duckdns.org
python nfs_online.py create-account
python nfs_online.py start --games u2,mw
# o:
./start.sh u2
```

La web se corre aparte; la forma recomendada es el contenedor. En Windows no corras `uvicorn` contra la SQLite viva mientras el contenedor del juego la usa.

### Configuración

- `config/server.toml` concentra `PUBLIC_HOST`, límites de autenticación y puertos. El valor por defecto es `127.0.0.1`; en producción se cambia a `nfs-fps.duckdns.org`.
- Los clientes usan `clients/underground2/net_u2.ini` y `clients/most-wanted/net_mw.ini` como plantillas. El pack reescribe el host; no edites los INIs de los jugadores.
- La web toma sus variables de entorno (`NFS_WEB_*`); los nombres están en [docker/compose.prod.yml](docker/compose.prod.yml) y el runbook [docs/deployment.md](docs/deployment.md). [deploy/env.example](deploy/env.example) cubre las variables del servidor.
- **Nunca** commitees `.env`, hashes de admin, tokens de DuckDNS, IPs reales, cuentas ni bases de datos. En producción viven en `/opt/nfs-online/env/` y en la SQLite del servidor.

### Puertos

| Servicio | Protocolo | Puerto |
|---|---|---|
| Messenger compartido | TCP | 13505 |
| U2 bootstrap/lobby/PREL | TCP | 20921-20923 |
| MW bootstrap/lobby | TCP | 30920-30921 |
| Carreras U2/MW | UDP | 20000-20005 |
| Web pública | HTTPS | 443 (NPM → `nfs-web:8080`) |
| Web local | HTTP | 8096 (dev/LAN; en producción loopback) |
| Carbon (Fase 1b) | TCP/UDP | 18210, 18215, 19119, 9000 |

Abrí solo los puertos de los juegos que corrés. El runbook de UFW, router y NPM está en [docs/deployment.md](docs/deployment.md).

## Clientes y pack

### Para jugadores

1. Entrá a [nfs-fps.duckdns.org/#descargas](https://nfs-fps.duckdns.org/#descargas).
2. Descargá el pack U2 + MW y verificá el SHA-256 del manifiesto.
3. Cerrá U2 y MW.
4. Ejecutá `INSTALAR.bat` (pide permisos de administrador).
5. Abrí el juego y logueate con tu cuenta.

El instalador lee `host.txt`, fuerza el host en `net_u2.ini`/`net_mw.ini`, instala el ASI Loader y el Widescreen Fix, y no toca los archivos del juego. El pack **no** incluye ISOs ni ejecutables originales.

### Para el operador

El pack se genera fuera del repo, en `NFS-Online-Artifacts/downloads/`:

```bash
python tools/package_clients.py --host nfs-fps.duckdns.org
```

Produce `NFS-Online-Client-Pack-v<version>.zip`, los ZIP por juego y `manifest.json` con tamaños y SHA-256. La web los sirve desde el directorio de descargas (`NFS_DOWNLOADS_DIR`). La versión se puede fijar con `--version`.

Para recompilar los ASI (Linux/WSL):

```bash
cd source/client-zig
./build_linux.sh
```

Salidas: `net_u2.asi`, `net_mw.asi` y `net_carbon.asi` en `source/client-zig/zig-out/bin/`.

### Widescreen Fix

- U2 usa `WindowedMode = 1` y `SkipIntro = 1`.
- MW usa `WindowedMode = 1` y **`SkipIntro = 0`**: con `1`, algunas builds de `speed.exe` 1.3 crashean al arrancar (`0xc0000005` en `0x0017dbb3`, issue [#2253](https://github.com/ThirteenAG/WidescreenFixesPack/issues/2253)). El pack fuerza `0`; no lo cambies a `1` en esa build.
- El detalle de la investigación está en [docs/research/2026-11-21-nfs-widescreen-dsr.md](docs/research/2026-11-21-nfs-widescreen-dsr.md).

## Pruebas

```bash
# Web + empaquetado (requiere pytest)
python -m pip install pytest
python -m pytest web/tests tests/test_package_clients.py -q

# CLI, reportes y checker (unittest del CI)
python -m unittest discover -s tests -q

# Protocolos
(cd server/common && PYTHONPATH=.. python -m unittest discover -s tests -q)
(cd server/classic && PYTHONPATH=.. python -m unittest discover -s tests -q)
(cd server/carbon && PYTHONPATH=.. python -m unittest discover -s tests -q)

# Validaciones
python nfs_online.py check
python tools/check_public_tree.py   # en CI o sobre git archive HEAD
```

La suite web/empaquetado dio **65 passed** al 2026-11-22. El workflow de CI compila los clientes Zig y valida el árbol público; la suite web se corre localmente con pytest.

## Despliegue

- **Debian** con Docker y Docker Compose.
- **Nginx Proxy Manager** termina TLS en `443` y apunta a `nfs-web:8080`; `8096` queda en loopback para desarrollo.
- **DuckDNS** actualiza `nfs-fps.duckdns.org`; el contenedor `duckdns-nfs` está en [deploy/duckdns-nfs.compose.yml](deploy/duckdns-nfs.compose.yml).
- **UFW** abre los puertos de U2/MW y el relay UDP; el runbook está en [docs/deployment.md](docs/deployment.md).
- La actualización es `deploy/update.sh`: `git pull` + rebuild de los contenedores.
- Los packs, el `manifest.json` y `og-image.jpg` viven en `/opt/nfs-online/artifacts/downloads/` (fuera del repo) y se montan en `nfs-web` como `/app/downloads`.

Stack de producción: [docker/compose.prod.yml](docker/compose.prod.yml). Variables reales: `/opt/nfs-online/env/` (no versionado).

## Estado del proyecto

- **Fase 1 (U2 + MW):** online; login, salas y carreras con jugadores fuera de la LAN verificados.
- **Web:** registro con invitación, login, recuperación, descargas, admin, estado en vivo y social preview. Leaderboards, noticias/TOS y estado completo: pendientes.
- **MW:** login verificado después del fix (`SkipIntro = 0`); DSR en fullscreen: pendiente.
- **Fase 1b:** Carbon.
- **Evidencias:** [docs/PROGRESS.md](docs/PROGRESS.md). Contexto operativo y decisiones: [AGENTS.md](AGENTS.md). Diseño: [spec](docs/superpowers/specs/2026-11-21-nfs-online-selfhost-design.md); plan: [plan](docs/superpowers/plans/2026-11-21-nfs-online-selfhost.md).

## Soporte y contribución

- **Cuenta/recuperación:** usá [nfs-fps.duckdns.org/account](https://nfs-fps.duckdns.org/account) o pedile al operador un reset desde el panel admin.
- **Bugs y pedidos:** abrí un issue en [GitHub](https://github.com/rodrigoangeloni/NFS-Online-Server/issues).
- **Seguridad:** seguí [SECURITY.md](SECURITY.md); no publiques credenciales, IPs privadas, bases de datos ni capturas con identidades.
- **Contribuciones:** [CONTRIBUTING.md](CONTRIBUTING.md) y el flujo de pull requests. No commitees ASI, ZIPs, ISOs, bases de datos ni secretos.

## Créditos

- **Fork y servidor:** Rodrigo Angeloni (RoanDev) — [@rodrigoangeloni](https://github.com/rodrigoangeloni).
- **Proyecto original:** [moio9/NFS-Online-Server](https://github.com/moio9/NFS-Online-Server).
- **Widescreen Fix:** [ThirteenAG/WidescreenFixesPack](https://github.com/ThirteenAG/WidescreenFixesPack).
- **Ultimate ASI Loader:** [ThirteenAG/Ultimate-ASI-Loader](https://github.com/ThirteenAG/Ultimate-ASI-Loader).
- **Licencias de terceros:** [LICENSES/](LICENSES) y [packaging/client/LICENCIAS.txt](packaging/client/LICENCIAS.txt).

## Licencia

El código original está bajo **AGPL-3.0-or-later**. Ver [LICENSE](LICENSE) y [LICENSE-NOTICE.md](LICENSE-NOTICE.md).

Need for Speed y los nombres relacionados son marcas de Electronic Arts. Este proyecto es no oficial y no está afiliado ni respaldado por Electronic Arts.
