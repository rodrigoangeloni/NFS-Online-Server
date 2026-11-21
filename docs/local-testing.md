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

```powershell
.\tools\run_web.ps1 -PublicHost 192.0.2.37 -Port 8080
```

Abrir `http://192.0.2.37:8080` desde esta PC o desde otra PC de la LAN.

- Registro abierto por defecto en la prueba LAN.
- Para exigir invitación: `.\tools\run_web.ps1 -InviteRequired` y crear un código con
  la herramienta de administración cuando esté implementada.
- La web escribe en la misma `data/accounts.sqlite3` que el servidor de juego.

## Probar registro y descarga

1. Abrir `/account` desde la otra PC.
2. Crear cuenta con nombre, persona y contraseña de al menos 8 caracteres.
3. Ir a `/#descargas` y descargar el pack U2 + MW.
4. Verificar el SHA-256 contra `manifest.json`.
5. Descomprimir y ejecutar `INSTALAR.bat`.

## Puertos del juego

La web usa `8080`. El servidor de juego usa:

- TCP `13505`, `20921`, `20922`, `20923`, `30920`, `30921`.
- UDP `20000` (relay de carreras).

En Docker Desktop los puertos publicados pueden quedar ligados a `127.0.0.1`.
Para que otra PC de la LAN pueda entrar al juego hay que publicarlos en
`0.0.0.0` y reiniciar el stack. Esto todavía no se cambió para no cortar la
sesión de prueba actual.
