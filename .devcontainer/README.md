# Devcontainer

This devcontainer installs Home Assistant Core `2025.12.5` and mounts this
repository's `custom_components` directory into a local Home Assistant config
directory.

Start Home Assistant:

```bash
python -m homeassistant -c .devcontainer/hass-config --debug
```

Open <http://localhost:8123> and add the `Xiaomi Home Devices` integration from
Settings > Devices & services.

Run tests:

```bash
pytest tests
```

Plain Docker CLI:

```bash
docker build -f .devcontainer/Dockerfile -t xiaomi-home-devices-ha-dev .
docker run --rm -it \
  -p 8123:8123 \
  -v "$PWD":/workspaces/ha_xiaomi_home \
  -w /workspaces/ha_xiaomi_home \
  xiaomi-home-devices-ha-dev \
  sh -c 'sh .devcontainer/post-create.sh && python -m homeassistant -c .devcontainer/hass-config --debug'
```
