#!/usr/bin/env bash
set -euo pipefail

# Dedicated Watt node: preserve all running containers, images in use, and
# persistent volumes. Remove only old build cache and abandoned Docker objects.
docker builder prune --force --filter 'until=168h' --keep-storage 5GB
docker image prune --force --filter 'until=168h'
docker container prune --force --filter 'until=168h'
find /data/logs -maxdepth 1 -type f -name 'watt-update-*.log' -mtime +14 -delete
docker system df
