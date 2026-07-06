#!/bin/sh
set -eu

IMAGE_NAME="xiaomi-home-devices-ha-dev"
WORKSPACE_DIR="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"

if ! docker image inspect "$IMAGE_NAME" >/dev/null 2>&1; then
  docker build -f "$WORKSPACE_DIR/.devcontainer/Dockerfile" -t "$IMAGE_NAME" "$WORKSPACE_DIR"
fi

docker run --rm -it \
  -p 8123:8123 \
  -v "$WORKSPACE_DIR":/workspaces/ha_xiaomi_home \
  -w /workspaces/ha_xiaomi_home \
  "$IMAGE_NAME" \
  sh -c 'sh .devcontainer/post-create.sh && python -m homeassistant -c .devcontainer/hass-config --debug'
