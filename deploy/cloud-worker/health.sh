#!/usr/bin/env bash
set -euo pipefail

cd /data/watt/runtime
curl --fail --silent --show-error http://127.0.0.1:8000/health
printf '\n'
docker compose exec -T postgres pg_isready -U spg -d spg_dev
docker compose ps --status running api native-worker native-coordinator native-tool-host postgres
