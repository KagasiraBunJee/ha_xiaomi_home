"""Tests for MIoT spec parsing."""

from __future__ import annotations

from custom_components.xiaomi_home_air.spec import parse_miot_spec


SPEC = {
    "type": "urn:miot-spec-v2:device:air-purifier:0000A007:zhimi-mb3:1",
    "description": "Air Purifier",
    "services": [
        {
            "iid": 2,
            "type": "urn:miot-spec-v2:service:air-purifier:00007811:zhimi-mb3:1",
            "description": "Air Purifier",
            "properties": [
                {
                    "iid": 2,
                    "type": "urn:miot-spec-v2:property:on:00000006:zhimi-mb3:1",
                    "description": "Switch Status",
                    "format": "bool",
                    "access": ["read", "write", "notify"],
                },
                {
                    "iid": 4,
                    "type": "urn:miot-spec-v2:property:fan-level:00000016:zhimi-mb3:1",
                    "description": "Fan Level",
                    "format": "uint8",
                    "access": ["read", "write", "notify"],
                    "value-list": [
                        {"value": 1, "description": "Level1"},
                        {"value": 2, "description": "Level2"},
                        {"value": 3, "description": "Level3"},
                    ],
                },
                {
                    "iid": 5,
                    "type": "urn:miot-spec-v2:property:mode:00000008:zhimi-mb3:1",
                    "description": "Mode",
                    "format": "uint8",
                    "access": ["read", "write", "notify"],
                    "value-list": [
                        {"value": 0, "description": "Auto"},
                        {"value": 1, "description": "Sleep"},
                    ],
                },
            ],
        },
        {
            "iid": 3,
            "type": "urn:miot-spec-v2:service:environment:0000780A:zhimi-mb3:1",
            "description": "Environment",
            "properties": [
                {
                    "iid": 6,
                    "type": "urn:miot-spec-v2:property:pm2.5-density:00000034:zhimi-mb3:1",
                    "description": "PM2.5",
                    "format": "float",
                    "access": ["read", "notify"],
                    "value-range": [0, 600, 1],
                }
            ],
        },
        {
            "iid": 4,
            "type": "urn:miot-spec-v2:service:filter:0000780B:zhimi-mb3:1",
            "description": "Filter",
            "properties": [
                {
                    "iid": 3,
                    "type": "urn:miot-spec-v2:property:filter-life-level:0000001E:zhimi-mb3:1",
                    "description": "Filter Life Level",
                    "format": "uint8",
                    "access": ["read", "notify"],
                    "unit": "percentage",
                    "value-range": [0, 100, 1],
                }
            ],
            "actions": [
                {
                    "iid": 1,
                    "type": "urn:miot-spec-v2:action:reset-filter-life:00002803:zhimi-mb3:1",
                    "description": "Reset Filter Life",
                    "in": [],
                    "out": [],
                }
            ],
        },
    ],
}


def test_parse_air_purifier_spec():
    spec = parse_miot_spec(SPEC)

    power = spec.prop("air-purifier", "on")
    mode = spec.prop("air-purifier", "mode")
    pm25 = spec.prop("environment", "pm2.5-density")
    action = spec.action("filter", "reset-filter-life")

    assert power is not None
    assert power.key == "2.2"
    assert power.writable
    assert mode is not None
    assert mode.options == ["Auto", "Sleep"]
    assert mode.value_for_option("Sleep") == 1
    assert mode.option_for_value(0) == "Auto"
    assert pm25 is not None
    assert pm25.entity_key in {prop.entity_key for prop in spec.readable_poll_props()}
    assert action is not None
    assert action.siid == 4
    assert action.aiid == 1

