#!/usr/bin/env bash
set -euo pipefail

df -h /data /
du -sh /data/docker /data/postgres /data/watt /data/logs
docker system df
docker builder du
