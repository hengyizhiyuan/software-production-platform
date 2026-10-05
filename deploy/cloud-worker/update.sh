#!/usr/bin/env bash
set -euo pipefail

runtime=/data/watt/runtime
source_dir="$runtime/source"
mkdir -p /data/logs
exec > >(tee -a "/data/logs/watt-update-$(date -u +%Y%m%dT%H%M%SZ).log") 2>&1
install -d -m 0750 /data/watt/app/native-workspaces \
  /data/watt/app/native-executor /data/watt/app/native-tool-receipts \
  /data/watt/app/managed-source
chown 10001:10001 /data/watt/app/native-workspaces \
  /data/watt/app/native-executor /data/watt/app/native-tool-receipts \
  /data/watt/app/managed-source
cd "$source_dir"

test -z "$(git status --porcelain)"
branch="$(git symbolic-ref --quiet --short HEAD)"
test -n "$branch"
git fetch origin --prune
git merge --ff-only "origin/$branch"

"$source_dir/deploy/cloud-worker/prepare-owners.sh"

if ! grep -q '^WATT_GITEA_PASSWORD=' "$runtime/.env"; then
  umask 077
  printf 'WATT_GITEA_PASSWORD=%s\n' "$(openssl rand -hex 24)" >> "$runtime/.env"
fi

install -m 0644 deploy/cloud-worker/docker-compose.yml "$runtime/docker-compose.yml"
cd "$runtime"
docker compose config --quiet
docker compose build migrate
docker compose up -d
if ! docker compose exec -T gitea gitea admin user list | grep -q 'watt-managed'; then
  WATT_GITEA_PASSWORD="$(sed -n 's/^WATT_GITEA_PASSWORD=//p' "$runtime/.env" | tail -1)"
  test -n "$WATT_GITEA_PASSWORD"
  docker compose exec -T gitea gitea admin user create \
    --username watt-managed --password "$WATT_GITEA_PASSWORD" \
    --email watt-managed@localhost.invalid --admin
fi
install -m 0750 "$source_dir"/deploy/cloud-worker/*.sh "$runtime/scripts/"
