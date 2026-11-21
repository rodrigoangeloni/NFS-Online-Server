# Prueba local de la web

## Requisitos

- Python 3.10 o superior.
- Dependencias de `web/requirements.txt` (`fastapi`, `uvicorn`).
- El servidor de juego puede estar corriendo en Docker Desktop (`nfs-server-dev`).

## Construir los paquetes de descarga

Los binarios viven fuera del repo, en `NFS-Online-Artifacts/`. Desde la raíz:

```powershell
python tools/package_clients.py `
  --host 192.0.2.37 `
  --out-dir "E:\vscode-workspace\NFS-Online-Artifacts\downloads" `
  --asi-dir "E:\vscode-workspace\NFS-Online-Artifacts\vendor\nfs-online-client-current" `
  --asi-loader "E:\vscode-workspace\NFS-Online-Artifacts\vendor\Ultimate-ASI-Loader\dinput8.dll" `
  --widescreen-dir "E:\vscode-workspace\NFS-Online-Artifacts\vendor\widescreen-fixes"
```

El resultado es:

- `NFS-Online-Client-Pack-v0.2.22.zip` (U2 + MW).
- `NFS-Online-U2-Client-v0.2.22.zip`.
- `NFS-Online-MW-Client-v0.2.22.zip`.
- `manifest.json` con tamaños y SHA-256.

## Levantar la web

La forma recomendada es el contenedor, para que la web y el servidor accedan a
la misma SQLite a través de Docker y no se mezclen escrituras del host con el
contenedor (eso produce `disk I/O error`).

```powershell
$env:NFS_PUBLIC_HOST = "192.0.2.37"
$env:NFS_LOCAL_IPV4 = "192.0.2.37"
$env:NFS_WEB_PUBLIC_HOST = "192.0.2.37"
$env:NFS_WEB_SITE_URL = "http://192.0.2.37:8096"
$env:NFS_WEB_INVITE_REQUIRED = "0"
$env:NFS_DOWNLOADS_DIR = "E:/vscode-workspace/NFS-Online-Artifacts/downloads"

docker compose -f docker/compose.dev.yml up -d --build nfs-web
```

Abrir `http://192.0.2.37:8096` desde esta PC o desde otra PC de la LAN.

- El puerto **8096** se usa para no chocar con `sbrw-core`/NFS World en `8080` ni con Assetto en `8081-8088`.
- Registro abierto con `NFS_WEB_INVITE_REQUIRED=0`; en producción debe quedar en `1`.
- La web escribe en la misma `data/accounts.sqlite3` que el servidor de juego.
- `tools/run_web.ps1` sirve para trabajar solo en la interfaz; no lo uses contra
  la base viva mientras el servidor está corriendo, porque el acceso desde
  Windows y desde el contenedor rompe el WAL de SQLite.

## Probar registro y descarga

1. Abrir `/account` desde la otra PC.
2. Crear cuenta con nombre, persona y contraseña de al menos 8 caracteres.
3. Ir a `/#descargas` y descargar el pack U2 + MW.
4. Verificar el SHA-256 contra `manifest.json`.
5. Descomprimir y ejecutar `INSTALAR.bat`.

## Puertos del juego

La web usa `8096`. El servidor de juego usa:

- TCP `13505`, `20921`, `20922`, `20923`, `30920`, `30921`.
- UDP `20000` (relay de carreras).

En Docker Desktop los puertos publicados se ven en `0.0.0.0` y el servidor
anuncia la IP configurada en `NFS_PUBLIC_HOST`. El stack actual ya se levantó
con `NFS_PUBLIC_HOST=192.0.2.37`, así que el cliente de la otra PC debe
usar esa dirección (el paquete descargado ya la trae configurada).

Si el otro jugador no puede entrar, revisar firewall de Windows para los
puertos TCP `13505`, `20921-20923`, `30920-30921` y UDP `20000-20005`.
