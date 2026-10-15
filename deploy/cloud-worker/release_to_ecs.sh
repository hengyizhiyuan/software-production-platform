#!/usr/bin/env bash
# Workstation-side release: bundle exact Watt source + staged Owners, ship to
# ECS, build the composite image there, gate it, and recreate every service.
# usage: deploy/cloud-worker/release_to_ecs.sh [ssh-host]
set -euo pipefail
host="${1:-watt-ecs}"
root="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$root"
test -z "$(git status --porcelain -- src deploy migrations docker pyproject.toml uv.lock owners.lock)" \
  || { echo "uncommitted release inputs" >&2; exit 1; }
revision="$(git rev-parse HEAD)"
py="${PYTHON:-python}"
"$py" deploy/cloud-worker/stage_owners.py --output build/owners "${@:2}"
bundle="$(mktemp -d)/watt-release-${revision:0:12}.tar"
git -c core.autocrlf=false archive --format=tar -o "$bundle" "$revision"
tar --append -f "$bundle" build/owners
sha="$(sha256sum "$bundle" | cut -d' ' -f1)"
remote="/data/watt/releases/${revision:0:12}"
ssh -o BatchMode=yes "$host" "test ! -e $remote && mkdir -p $remote"
scp -q "$bundle" "$host:$remote/release.tar"
ssh -o BatchMode=yes "$host" bash -s -- "$remote" "$sha" "$revision" <<'REMOTE'
set -euo pipefail
remote="$1"; sha="$2"; revision="$3"; runtime=/data/watt/runtime
cd "$remote"
test "$(sha256sum release.tar | cut -d' ' -f1)" = "$sha"
mkdir source && tar -xf release.tar -C source
cd source
docker build --network none -f deploy/cloud-worker/Dockerfile --target runtime \
  --build-arg "WATT_REVISION=$revision" -t "watt-cloud-worker:$revision" . > "$remote/build.log" 2>&1
docker run --rm --network none --entrypoint python "watt-cloud-worker:$revision" \
  /app/deploy/cloud-worker/release_gate.py | tee "$remote/release-gate.json"
for service in api native-coordinator native-tool-host native-worker; do
  id="$(docker ps -q --filter "name=^watt-cloud-worker-${service}-1$")"
  if [ -n "$id" ]; then docker tag "$(docker inspect --format '{{.Image}}' "$id")" "watt-cloud-worker:rollback-$service-${revision:0:12}"; fi
done
docker tag "watt-cloud-worker:$revision" watt-cloud-worker:local
cp "$runtime/docker-compose.yml" "$remote/previous-docker-compose.yml"
install -m 0644 deploy/cloud-worker/docker-compose.yml "$runtime/docker-compose.yml"
sed -i "s/^WATT_REVISION=.*/WATT_REVISION=$revision/" "$runtime/.env"
cd "$runtime"
docker compose config --quiet
docker compose run --rm migrate
docker compose up -d --no-build --force-recreate api native-coordinator native-tool-host native-worker
for _ in $(seq 1 120); do
  if curl -fsS http://127.0.0.1:8080/health >/dev/null 2>&1; then break; fi; sleep 3
done
curl -fsS http://127.0.0.1:8080/health
echo
for service in api native-coordinator native-tool-host native-worker; do
  printf '%s %s\n' "$service" "$(docker inspect --format '{{.Image}} {{.State.Status}}' "watt-cloud-worker-${service}-1")"
done
REMOTE
echo "released $revision"
