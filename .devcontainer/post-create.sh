#!/bin/sh
set -eu

python -m pip install pytest pytest-asyncio

ln -sfn ../../custom_components .devcontainer/hass-config/custom_components

cat <<'MSG'

Home Assistant devcontainer is ready.

Start Home Assistant:
  python -m homeassistant -c .devcontainer/hass-config --debug

Then open:
  http://localhost:8123

Run local tests:
  pytest tests

MSG

