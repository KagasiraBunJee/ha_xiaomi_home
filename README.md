# Xiaomi Home Devices

Home Assistant custom integration for Xiaomi Home devices using Xiaomi
OAuth and MIoT cloud APIs.

## Status

This is a focused v1:

- Discovers Xiaomi Home devices that expose MIoT specs
- Creates generic sensor, switch, select, number, and button entities from MIoT properties/actions
- Keeps a richer fan entity for MIoT air purifiers
- Uses cloud polling only
- Does not implement MQTT push, LAN control, BLE, Zigbee, IR, or gateway-local control yet

## Development

Start Home Assistant in the devcontainer:

```bash
python -m homeassistant -c .devcontainer/hass-config --debug
```

Then open <http://localhost:8123> and add `Xiaomi Home Devices` from Settings >
Devices & services.

Run tests:

```bash
pytest tests
```

Plain Docker:

```bash
docker build -f .devcontainer/Dockerfile -t xiaomi-home-devices-ha-dev .
docker run --rm -it \
  -p 8123:8123 \
  -v "$PWD":/workspaces/ha_xiaomi_home \
  -w /workspaces/ha_xiaomi_home \
  xiaomi-home-devices-ha-dev \
  sh -c 'sh .devcontainer/post-create.sh && python -m homeassistant -c .devcontainer/hass-config --debug'
```

## HACS

Add this repository to HACS as a custom repository of type `Integration`:

```text
KagasiraBunJee/ha_xiaomi_home
```

Install a tagged release such as `v0.1.0`; installing directly from an
unversioned branch/commit can make HACS see a commit hash as the version.

## License

This project is licensed under the MIT License. Xiaomi, Xiaomi Home, Mijia, and
Home Assistant names and trademarks belong to their respective owners.
