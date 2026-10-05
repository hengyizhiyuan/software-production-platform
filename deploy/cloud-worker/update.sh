#!/usr/bin/env bash
set -euo pipefail

runtime=/data/watt/runtime
source_dir="$runtime/source"
mkdir -p /data/logs
exec > >(tee -a "/data/logs/watt-update-$(date -u +%Y%m%dT%H%M%SZ).log") 2>&1
cd "$source_dir"

test -z "$(git status --porcelain)"
branch="$(git symbolic-ref --quiet --short HEAD)"
test -n "$branch"
git fetch origin --prune
git merge --ff-only "origin/$branch"

install -m 0644 deploy/cloud-worker/docker-compose.yml "$runtime/docker-compose.yml"
cd "$runtime"
docker compose config --quiet
docker compose build migrate
docker compose up -d
