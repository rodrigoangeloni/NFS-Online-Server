# Despliegue en Debian

**Servidor:** `debian-server` (`<usuario>@192.0.2.200`)
**Dominio:** `nfs-fps.duckdns.org` → `<IP publica>`
**Web local:** `127.0.0.1:8096` (NPM hace el proxy)
**Juego:** puertos nativos, sin Docker

## 1. Requisitos

- Debian 12 con Python 3.11, Docker y Docker Compose.
- Nginx Proxy Manager (`nginx-proxy-manager-new-app-1`) en la red
  `nginx-proxy-manager-new_default`.
- UFW activo.
- El router debe reenviar al Debian (`192.0.2.200`):
  - TCP `80`, `443` (NPM; probablemente ya está).
  - TCP `13505`, `20921`, `20922`, `20923`, `30920`, `30921`.
  - UDP `20000-20005`.
- El puerto `8080` es de NFS World y `8081-8088` de Assetto: **no usarlos**.

## 2. Copiar el proyecto

```bash
sudo mkdir -p /opt/nfs-online/{repo,artifacts/downloads,data,runtime,logs,env}
sudo chown -R <usuario>:<usuario> /opt/nfs-online
```

Copiar el árbol desde la PC de desarrollo (sin `data/`, `runtime/`, `logs/`):

```powershell
git archive HEAD --format=tar.gz -o "$env:TEMP\nfs-online-repo.tar.gz"
scp "$env:TEMP\nfs-online-repo.tar.gz" debian:/tmp/
```

```bash
tar -xzf /tmp/nfs-online-repo.tar.gz -C /opt/nfs-online/repo
```

Copiar los paquetes de descarga generados con el dominio público:

```powershell
python tools/package_clients.py `
  --host nfs-fps.duckdns.org `
  --out-dir "$env:TEMP\nfs-downloads" `
  --asi-dir "E:\vscode-workspace\NFS-Online-Artifacts\vendor\nfs-online-client-current" `
  --asi-loader "E:\vscode-workspace\NFS-Online-Artifacts\vendor\Ultimate-ASI-Loader\dinput8.dll" `
  --widescreen-dir "E:\vscode-workspace\NFS-Online-Artifacts\vendor\widescreen-fixes"

scp "$env:TEMP\nfs-downloads\*" debian:/opt/nfs-online/artifacts/downloads/
```

## 3. Configuración del servidor

```bash
cp /opt/nfs-online/repo/deploy/env.example /opt/nfs-online/env/nfs.env
chmod 600 /opt/nfs-online/env/nfs.env
```

Contenido:

```ini
NFS_PUBLIC_HOST=nfs-fps.duckdns.org
NFS_GAMES=u2,mw
NFS_LOG_LEVEL=INFO
```

### 3.1 Clave de administrador

Generar el hash PBKDF2 de la clave que va a usar el panel:

```bash
cd /opt/nfs-online/repo
python3 tools/admin_password.py
```

Copiar el hash que imprime en:

```bash
/opt/nfs-online/env/web.env
```

Contenido de `web.env`:

```ini
NFS_UID=1000
NFS_GID=1000
NFS_WEB_PUBLIC_HOST=nfs-fps.duckdns.org
NFS_WEB_SITE_URL=https://nfs-fps.duckdns.org
NFS_WEB_DOWNLOADS_DIR=/opt/nfs-online/artifacts/downloads
NFS_WEB_INVITE_REQUIRED=1
NFS_WEB_EMAIL_REQUIRED=1
NFS_WEB_ADMIN_USERNAME=admin
NFS_WEB_TRUSTED_PROXY_IPS=172.28.0.0/16
NFS_WEB_ADMIN_PASSWORD_HASH=pbkdf2_sha256$...
```

El panel queda en `https://nfs-fps.duckdns.org/admin`. El usuario por
defecto es `admin`; la clave es la que generaste. Ahí se ven,
crean y revocan invitaciones, se listan cuentas y se puede resetear
la contraseña de un jugador. El código de invitación se guarda en la
SQLite para poder consultarlo después.

Comprobar:

```bash
cd /opt/nfs-online/repo
python3 nfs_online.py check
```

## 4. Servicio systemd

```bash
sudo cp /opt/nfs-online/repo/deploy/systemd/nfs-online.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now nfs-online.service
systemctl status nfs-online.service --no-pager
python3 nfs_online.py status
```

Logs:

```bash
tail -f /opt/nfs-online/repo/logs/classic.log
```

## 5. Web en Docker

La red de NPM ya existe:

```bash
docker network ls | grep nginx-proxy-manager
```

Levantar la web:

```bash
cd /opt/nfs-online/repo
docker compose --env-file /opt/nfs-online/env/web.env \
  -f docker/compose.web.yml up -d --build
```

La web escucha en `127.0.0.1:8096` y en la red Docker de NPM como
`nfs-web:8080`. Verificar desde el host:

```bash
curl -fsS http://127.0.0.1:8096/healthz
```

## 6. NPM

Crear un **Proxy Host**:

- Domain Names: `nfs-fps.duckdns.org`
- Scheme: `http`
- Forward Hostname/IP: `nfs-web`
- Forward Port: `8080`
- Block Common Exploits: sí
- Force SSL: sí
- HTTP/2 Support: sí
- Access List: ninguna (el sitio es público)

`nfs-web` está conectado a `nginx-proxy-manager-new_default`; NPM lo
resuelve por DNS de Docker y usa el puerto interno `8080`. No usar
`192.0.2.200:8096`: ese puerto queda solo en loopback para
diagnóstico y no debe publicarse.

## 7. Firewall UFW

```bash
sudo ufw allow 13505/tcp comment 'NFS Online Messenger'
sudo ufw allow 20921:20923/tcp comment 'NFS Online U2'
sudo ufw allow 30920:30921/tcp comment 'NFS Online MW'
sudo ufw allow 20000:20005/udp comment 'NFS Online race relay'
sudo ufw reload
sudo ufw status numbered
```

No abrir `8096`: solo escucha en loopback y NPM llega por la red Docker.
Si el router reenvía todo (DMZ), el bind loopback es lo que impide que
`8096` quede público.

## 8. Invitaciones y recuperación

Con `NFS_WEB_INVITE_REQUIRED=1`, crear un código:

```bash
cd /opt/nfs-online/repo
PYTHONPATH=server NFS_WEB_CONFIG=config/server.toml \
NFS_WEB_DOWNLOADS_DIR=/opt/nfs-online/artifacts/downloads \
python3 tools/create_invite.py --label "amigos" --uses 10 --days 30
```

Pasarlo a los amigos. El registro queda en
`https://nfs-fps.duckdns.org/account`.

Cada cuenta nueva recibe un **código de recuperación**. Si olvida la
contraseña, en `/account` → “Olvidé mi contraseña” ingresa cuenta +
email + código; la web le muestra una contraseña temporal válida 24 h
y lo obliga a cambiarla. Si perdió el código, desde `/admin` se puede
resetear la cuenta y pasarle la temporal.

## 9. Verificación pública

1. `dig +short nfs-fps.duckdns.org` → `<IP publica>`.
2. `curl https://nfs-fps.duckdns.org/healthz` → `{"ok":true}`.
3. Abrir `https://nfs-fps.duckdns.org/` y `/account`.
4. Crear una cuenta con invitación.
5. Descargar un ZIP y verificar el SHA-256 del manifest.
6. Instalar en un juego y entrar desde una red externa (no la LAN).
7. Crear una sala y confirmar que aparece en la landing.

## 10. Router

El Debian no tiene la IP pública directamente: está detrás de
`192.0.2.1`. Hay que reenviar los puertos del punto 1 a
`192.0.2.200` en el router. Sin eso, el registro y las descargas
pueden funcionar por NPM (80/443), pero el juego no conectará desde
Internet.

## 11. Actualización

```bash
cd /opt/nfs-online/repo
git fetch --all
git switch main
git pull --ff-only
sudo systemctl restart nfs-online.service
docker compose -f docker/compose.web.yml up -d --build
```

Antes de actualizar, backup:

```bash
sqlite3 /opt/nfs-online/repo/data/accounts.sqlite3 \
  ".backup '/opt/nfs-online/backups/accounts-$(date +%F-%H%M).sqlite3'"
```

## 12. Problemas conocidos

- **No ejecutar `uvicorn` en el host Windows** contra la SQLite viva del
  contenedor: produce `disk I/O error`. En Debian, la web corre en Docker.
- `NFS_WEB_ALLOW_INSECURE=1` en producción es temporal: NPM termina TLS y
  el puerto está en loopback. Endurecer con CIDRs de proxy confiables.
- Si NPM no resuelve `nfs-web`, verificar que el contenedor esté en
  `nginx-proxy-manager-new_default`.
- Si el juego no conecta desde Internet, revisar primero el reenvío de
  puertos del router y después `sudo ufw status`.
