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
la contraseña de un jugador o **banearlo/desbanearlo**. El baneo
desconecta al piloto del juego y le invalida la sesión web. El código de invitación se guarda en la
SQLite para poder consultarlo después.

`NFS_WEB_ADMIN_PASSWORD_HASH` es **solo la semilla inicial**. Cuando se
cambia la clave desde `/admin`, la SQLite
(`web_admin_credentials.password_hash`) pasa a mandar y el valor de
`web.env` queda viejo. Si se olvida la clave, se puede restaurar la
semilla sobrescribiendo esa fila con el hash de `web.env`, o borrando la
fila y reiniciando `nfs-web` para que la vuelva a sembrar.

Comprobar:

```bash
cd /opt/nfs-online/repo
python3 nfs_online.py check
```

## 4. Stack Docker (juego + web)

El stack completo está en `docker/compose.prod.yml`; ambos contenedores
aparecen en Portainer → **Containers** (proyecto `nfs-online`).

```bash
# El servidor de juego ya no usa systemd: se elimina el unit si quedó
# de la instalación anterior.
sudo systemctl disable --now nfs-online.service 2>/dev/null || true
sudo rm -f /etc/systemd/system/nfs-online.service
sudo systemctl daemon-reload

cd /opt/nfs-online/repo
docker compose \
  --env-file /opt/nfs-online/env/nfs.env \
  --env-file /opt/nfs-online/env/web.env \
  -f docker/compose.prod.yml up -d --build
docker compose \
  --env-file /opt/nfs-online/env/nfs.env \
  --env-file /opt/nfs-online/env/web.env \
  -f docker/compose.prod.yml ps
```

`nfs-server` usa `dns: 1.1.1.1` para que el DNS split-horizon del router
no le devuelva `192.0.2.200`; así anuncia la IP pública
`<IP publica>`. `nfs-web` queda en `127.0.0.1:8096` y en la red de NPM
como `nfs-web:8080`.

Verificar:

```bash
docker logs nfs-server --tail 20
docker logs nfs-web --tail 20
curl -fsS http://127.0.0.1:8096/healthz
```

## 5. NPM

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

En este HG8245W5-6T se crearon estas reglas (sin tocar las existentes):

| Nombre | Protocolo | Puertos | Destino |
|---|---|---|---|
| `NFS-Online-Msg` | TCP | `13505` | `192.0.2.200` |
| `NFS-Online-U2` | TCP | `20921-20923` | `192.0.2.200` |
| `NFS-Online-MW` | TCP | `30920-30921` | `192.0.2.200` |
| `NFS-Online-Race` | UDP | `20000-20005` | `192.0.2.200` |

Los TCP se verificaron desde Internet; el UDP se confirma con una
carrera entre dos conexiones distintas. `443` ya estaba reenviado a
`192.0.2.200`; `8096` no se reenvía.

## 11. Actualización

```bash
cd /opt/nfs-online/repo
./deploy/update.sh
```

El script hace `git pull --ff-only`, valida la configuración, reconstruye
`nfs-server`, reconstruye `nfs-web` y verifica `/healthz`.

Antes de actualizar, backup:

```bash
sqlite3 /opt/nfs-online/repo/data/accounts.sqlite3 \
  ".backup '/opt/nfs-online/backups/accounts-$(date +%F-%H%M).sqlite3'"
```

## 12. DuckDNS multi-cuenta

La imagen de LinuxServer usa **un token por contenedor**. El contenedor
`duckdns` existente actualiza `nextcloud-<usuario>`; no hay que reemplazarlo.

En este servidor ya está corriendo `duckdns-nfs` para `nfs-fps` con el
token de su cuenta. El token vive en
`/opt/nfs-online/env/duckdns-nfs.env` (chmod 600, no versionado).

Para `nfs-fps` (otra cuenta DuckDNS):

```bash
cat > /opt/nfs-online/env/duckdns-nfs.env <<'EOF'
DUCKDNS_TOKEN=tu_token_de_la_cuenta_nfs_fps
EOF
chmod 600 /opt/nfs-online/env/duckdns-nfs.env

cd /opt/nfs-online/repo
docker compose --env-file /opt/nfs-online/env/duckdns-nfs.env \
  -f deploy/duckdns-nfs.compose.yml up -d
docker logs duckdns-nfs --tail 20
```

El contenedor se llama `duckdns-nfs` y aparece en Portainer. No cambia
el DNS interno del router: el Static DNS sigue apuntando a
`192.0.2.200` para la LAN.

## 13. Problemas conocidos

- **No ejecutar `uvicorn` en el host Windows** contra la SQLite viva del
  contenedor: produce `disk I/O error`. En Debian, la web corre en Docker.
- `NFS_WEB_ALLOW_INSECURE=1` en producción es temporal: NPM termina TLS y
  el puerto está en loopback. Endurecer con CIDRs de proxy confiables.
- Si NPM no resuelve `nfs-web`, verificar que el contenedor esté en
  `nginx-proxy-manager-new_default`.
- Si el juego no conecta desde Internet, revisar primero el reenvío de
  puertos del router y después `sudo ufw status`.
