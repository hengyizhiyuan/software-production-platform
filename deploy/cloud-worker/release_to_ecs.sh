#!/usr/bin/env bash
# Workstation-side release of the three-project composite image.
# Builds Watt + the Owners pinned in owners.lock locally, runs the release gate
# inside the built image, ships the image to ECS and recreates every service
# from that single image (previous images kept as rollback tags).
# usage: deploy/cloud-worker/release_to_ecs.sh [ssh-host] [stage_owners args...]
set -euo pipefail
host="${1:-watt-ecs}"
root="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$root"
test -z "$(git status --porcelain -- src deploy migrations docker pyproject.toml uv.lock owners.lock)" \
  || { echo "uncommitted release inputs" >&2; exit 1; }
revision="$(git rev-parse HEAD)"
tag="watt-cloud-worker:$revision"
py="${PYTHON:-python}"
"$py" deploy/cloud-worker/stage_owners.py --output build/owners "${@:2}"
context="$(mktemp -d -p "${RELEASE_TMP:-/tmp}")"
git -c core.autocrlf=false archive --format=tar "$revision" | tar -x -C "$context"
cp -r build "$context/build"
docker build -q -f "$context/deploy/cloud-worker/Dockerfile" --target runtime \
  --build-arg "WATT_REVISION=$revision" -t "$tag" "$context"
MSYS_NO_PATHCONV=1 docker run --rm --network none --entrypoint python "$tag" \
  /app/deploy/cloud-worker/release_gate.py > "$context/release-gate.json"
grep -q '"status": "PASS"' "$context/release-gate.json"
remote="/data/watt/releases/${revision:0:12}"
ssh -o BatchMode=yes "$host" "mkdir -p $remote"
docker save "$tag" | gzip -1 | ssh -o BatchMode=yes "$host" "gunzip | docker load -q"
rm -rf "$context/build"
scp -q "$context/release-gate.json" "$context/deploy/cloud-worker/docker-compose.yml" "$host:$remote/"
cat > "$context/remote-release.sh" <<'REMOTE'
#!/usr/bin/env bash
set -euo pipefail
remote="$1"; revision="$2"; runtime=/data/watt/runtime; tag="watt-cloud-worker:$revision"
docker run --rm --network none --entrypoint python "$tag" /app/deploy/cloud-worker/release_gate.py \
  > "$remote/release-gate-ecs.json"
grep -q '"status": "PASS"' "$remote/release-gate-ecs.json"
for service in api native-coordinator native-tool-host native-worker; do
  id="$(docker ps -q --filter "name=^watt-cloud-worker-${service}-1$")"
  if [ -n "$id" ]; then
    docker tag "$(docker inspect --format '{{.Image}}' "$id")" "watt-cloud-worker:rollback-$service-${revision:0:12}"
  fi
done
docker tag "$tag" watt-cloud-worker:local
cp "$runtime/docker-compose.yml" "$remote/previous-docker-compose.yml"
install -m 0644 "$remote/docker-compose.yml" "$runtime/docker-compose.yml"
if grep -q '^WATT_REVISION=' "$runtime/.env"; then
  sed -i "s/^WATT_REVISION=.*/WATT_REVISION=$revision/" "$runtime/.env"
else
  printf 'WATT_REVISION=%s\n' "$revision" >> "$runtime/.env"
fi
cd "$runtime"
compose=(docker compose -p watt-cloud-worker -f "$runtime/docker-compose.yml")
"${compose[@]}" config --quiet
"${compose[@]}" run --rm --no-deps -T migrate < /dev/null
"${compose[@]}" up -d --no-build --force-recreate api native-coordinator native-tool-host native-worker < /dev/null
for _ in $(seq 1 120); do
  if curl -fsS http://127.0.0.1:8080/health >/dev/null 2>&1; then break; fi
  sleep 3
done
curl -fsS http://127.0.0.1:8080/health
echo
expected="$(docker image inspect --format '{{.Id}}' "$tag")"
for service in api native-coordinator native-tool-host native-worker; do
  actual="$(docker inspect --format '{{.Image}}' "watt-cloud-worker-${service}-1")"
  printf '%s %s\n' "$service" "$actual"
  test "$actual" = "$expected" || { echo "service $service is not running the release image" >&2; exit 1; }
done
echo RELEASE_REMOTE_PASS
REMOTE
scp -q "$context/remote-release.sh" "$host:$remote/remote-release.sh"
ssh -o BatchMode=yes "$host" bash "$remote/remote-release.sh" "$remote" "$revision" < /dev/null | tee "$context/remote.log"
grep -q RELEASE_REMOTE_PASS "$context/remote.log"
echo "released $revision"
