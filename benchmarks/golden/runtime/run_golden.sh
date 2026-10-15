#!/usr/bin/env bash
# Run one Golden Journey on the ECS host against the live API, inside the
# released image (host Python is too old). usage: run_golden.sh NAME "TEXT" [deadline_s]
set -euo pipefail
name="$1"; text="$2"; deadline="${3:-3600}"
root=/data/watt/golden/$(date -u +%Y%m%dT%H%M%SZ)-$name
mkdir -p "$root"; chmod 0777 "$root"
cp /data/watt/golden/golden_journey.py "$root/"
token_file="$(mktemp)"; trap 'rm -f "$token_file"' EXIT
grep '^SPG_OPERATOR_TOKEN=' /data/watt/runtime/.env > "$token_file"
chown 10001 "$token_file"; chmod 0400 "$token_file"
docker run --rm --network watt-cloud-worker_control \
  -v "$root:/out" -v "$token_file:/run/watt.env:ro" \
  --entrypoint python watt-cloud-worker:local /out/golden_journey.py \
  --base http://api:8000 --name "$name" --text "$text" --token-file /run/watt.env \
  --out /out --deadline "$deadline" > "$root/journey.log" 2>&1 || true
echo "$root"
