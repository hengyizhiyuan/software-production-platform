#!/usr/bin/env bash
# Run Golden case 8 inside the released image. usage: run_discussion.sh CASE_JSON
set -euo pipefail
case_file="$1"; name="$(basename "$case_file" .json)"
root=/data/watt/golden/$(date -u +%Y%m%dT%H%M%SZ)-$name
mkdir -p "$root"; chmod 0777 "$root"
cp /data/watt/golden/discussion.py "$case_file" "$root/"
env_file="$(mktemp)"; trap 'rm -f "$env_file"' EXIT
grep -E '^(SPG_OPERATOR_TOKEN|SPG_DEEPSEEK_API_KEY)=' /data/watt/runtime/.env > "$env_file"
chown 10001 "$env_file"; chmod 0400 "$env_file"
docker run --rm --network watt-cloud-worker_control -v "$root:/out" -v "$env_file:/run/watt.env:ro" \
  --entrypoint python watt-cloud-worker:local /out/discussion.py --base http://api:8000 --name "$name" \
  --script "/out/$(basename "$case_file")" --token-file /run/watt.env --judge-key-file /run/watt.env \
  --out /out > "$root/run.log" 2>&1 || true
echo "$root"
