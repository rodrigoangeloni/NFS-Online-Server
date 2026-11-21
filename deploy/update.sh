#!/bin/sh
set -eu

REPO_DIR=${NFS_REPO_DIR:-/opt/nfs-online/repo}
WEB_ENV=${NFS_WEB_ENV_FILE:-/opt/nfs-online/env/web.env}
GAME_ENV=${NFS_GAME_ENV_FILE:-/opt/nfs-online/env/nfs.env}

cd "$REPO_DIR"

echo "== git =="
git pull --ff-only

echo "== config =="
set -a
. "$GAME_ENV"
set +a
python3 nfs_online.py check

echo "== juego =="
docker compose -f docker/compose.server.yml up -d --build
sleep 3
docker ps --filter name=nfs-server --format "{{.Names}} {{.Status}} {{.Ports}}"
docker logs nfs-server --tail 15

echo "== web =="
docker compose --env-file "$WEB_ENV" -f docker/compose.web.yml up -d --build
sleep 2
curl -fsS http://127.0.0.1:8096/healthz
echo
echo "== listo =="
