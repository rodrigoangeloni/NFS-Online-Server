#!/bin/sh
set -eu

cd /app
python nfs_online.py start --games "${NFS_GAMES:-u2,mw}" --daemon

stop() {
    python nfs_online.py stop || true
    exit 0
}
trap stop TERM INT

while :; do
    sleep 3600 &
    wait $!
done
