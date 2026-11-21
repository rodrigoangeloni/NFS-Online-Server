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
- [ ] Login real de U2/MW contra el servidor local.
- [ ] Implementación de `web/` (registro, landing, leaderboards, admin).
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
  downloads\                          # aquí irán los ZIP finales
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

# Verificación del árbol público
python tools/check_public_tree.py
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

## Problemas conocidos

- `python nfs_online.py status` falla en Windows con `OSError: [WinError 87]` en `os.kill(pid, 0)`. Usar `docker exec nfs-server-dev python nfs_online.py status`.
- El servidor lanzado con `start --daemon` en Windows no sobrevive al cierre del comando; por eso se usa Docker Desktop.
- Los juegos son repacks de ElAmigos. Si el `.exe` fue modificado por el No-CD, los offsets del plugin pueden no coincidir. Si el cliente no engancha, probar con un ejecutable original 1.2/1.3.
- Docker Desktop no reproduce exactamente el host networking de Linux; la validación final es en el Debian.

## Próximo paso

1. Probar login en U2/MW con `TestDriver`.
2. Revisar `logs/classic.log` y `runtime/classic-status.json`.
3. Si el login funciona, implementar `web/` siguiendo el plan.
4. Si no, revisar `net_u2.log` / `net_mw.log` en la carpeta del juego.
