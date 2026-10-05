#!/usr/bin/env bash
set -euo pipefail

# Pin independent owner implementations without moving their canonical branches.
root=/data/watt/owners
install -d -m 0755 "$root"

ensure_owner() {
  local name="$1" url="$2" revision="$3" path="$root/$name"
  # A pinned, content-addressed owner source bundle can be pre-provisioned
  # through the existing Cloud Connection when this ECS cannot fetch private Git.
  if [ -f "$path/.owner-revision" ]; then
    test "$(cat "$path/.owner-revision")" = "$revision"
    test -f "$path/src/$name/runtime.py"
    test -f "$path/src/$name/__init__.py"
    return
  fi
  if [ ! -d "$path/.git" ]; then
    test ! -e "$path"
    git clone "$url" "$path"
  fi
  test -z "$(git -C "$path" status --porcelain)"
  if ! git -C "$path" cat-file -e "$revision^{commit}"; then
    git -C "$path" fetch origin "$revision"
  fi
  git -C "$path" switch --detach "$revision"
  test "$(git -C "$path" rev-parse HEAD)" = "$revision"
  test -z "$(git -C "$path" status --porcelain)"
}

ensure_owner ecf \
  https://github.com/hengyizhiyuan/engineering-context-fabric.git \
  8b2c7b68d6e1752c32050c2042e168b654d8139f
ensure_owner guardian \
  https://github.com/hengyizhiyuan/guardian.git \
  27bf5691e30104bf9a460df29a6f7dd4fb884a30
