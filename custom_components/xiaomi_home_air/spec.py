"""MIoT-Spec-V2 parsing helpers for Xiaomi devices."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


def urn_name(urn: str) -> str:
    """Extract the human-readable MIoT instance name from a URN."""

    parts = urn.split(":")
    return parts[3] if len(parts) > 3 else urn


@dataclass(slots=True)
class MIoTValueListItem:
    """One MIoT value-list option."""

    value: Any
    description: str


@dataclass(slots=True)
class MIoTProperty:
    """A MIoT property in a service."""

    siid: int
    piid: int
    service_name: str
    name: str
    description: str
    format: str
    access: set[str]
    unit: str | None = None
    value_range: list[Any] | None = None
    value_list: list[MIoTValueListItem] = field(default_factory=list)

    @property
    def readable(self) -> bool:
        return "read" in self.access

    @property
    def writable(self) -> bool:
        return "write" in self.access

    @property
    def key(self) -> str:
        return f"{self.siid}.{self.piid}"

    @property
    def entity_key(self) -> str:
        return f"{self.service_name}:{self.name}"

    @property
    def options(self) -> list[str]:
        return [item.description for item in self.value_list]

    def value_for_option(self, option: str) -> Any:
        for item in self.value_list:
            if item.description == option:
                return item.value
        raise ValueError(f"unknown option {option!r} for {self.entity_key}")

    def option_for_value(self, value: Any) -> str | None:
        for item in self.value_list:
            if item.value == value:
                return item.description
        return None


@dataclass(slots=True)
class MIoTAction:
    """A MIoT action in a service."""

    siid: int
    aiid: int
    service_name: str
    name: str
    description: str
    in_: list[int] = field(default_factory=list)

    @property
    def entity_key(self) -> str:
        return f"{self.service_name}:{self.name}"


@dataclass(slots=True)
class MIoTSpec:
    """Parsed MIoT-Spec-V2 instance."""

    urn: str
    description: str
    properties: list[MIoTProperty]
    actions: list[MIoTAction]

    def prop(self, service_name: str, prop_name: str) -> MIoTProperty | None:
        for prop in self.properties:
            if prop.service_name == service_name and prop.name == prop_name:
                return prop
        return None

    def first_prop(self, candidates: list[tuple[str, str]]) -> MIoTProperty | None:
        for service_name, prop_name in candidates:
            prop = self.prop(service_name, prop_name)
            if prop:
                return prop
        return None

    def action(self, service_name: str, action_name: str) -> MIoTAction | None:
        for action in self.actions:
            if action.service_name == service_name and action.name == action_name:
                return action
        return None

    def readable_poll_props(self) -> list[MIoTProperty]:
        return [
            prop
            for prop in self.properties
            if prop.readable and is_entity_property(prop)
        ]


POLL_SENSOR_KEYS = {
    "air-purifier:fault",
    "environment:pm2.5-density",
    "environment:relative-humidity",
    "environment:temperature",
    "filter:filter-life-level",
    "filter:filter-used-time",
    "motor-speed:motor-speed",
    "motor-speed:motor-set-speed",
    "use-time:use-time",
}

POLL_CONTROL_KEYS = {
    "air-purifier:on",
    "air-purifier:mode",
    "air-purifier:fan-level",
    "alarm:alarm",
    "indicator-light:brightness",
    "indicator-light:on",
    "physical-controls-locked:physical-controls-locked",
}

POLLED_ENTITY_KEYS = POLL_SENSOR_KEYS | POLL_CONTROL_KEYS

NUMERIC_FORMATS = {
    "uint8",
    "uint16",
    "uint32",
    "uint64",
    "int8",
    "int16",
    "int32",
    "int64",
    "float",
    "double",
}


def is_entity_property(prop: MIoTProperty) -> bool:
    """Return whether a property should be polled and exposed."""

    if not prop.readable:
        return False
    if prop.name in {"manufacturer", "model", "serial-number", "firmware-revision"}:
        return False
    if prop.format == "bool":
        return True
    if prop.value_list:
        return True
    if prop.format in NUMERIC_FORMATS:
        return True
    return prop.format in {"string"}


def is_number_property(prop: MIoTProperty) -> bool:
    """Return whether a property can be represented as a number entity."""

    return (
        prop.readable
        and prop.writable
        and prop.format in NUMERIC_FORMATS
        and bool(prop.value_range)
        and not prop.value_list
    )


def display_name(*parts: str) -> str:
    """Make a compact Home Assistant display name from MIoT names."""

    words = " ".join(part for part in parts if part).replace("_", "-").split("-")
    return " ".join(word.upper() if word.lower() in {"pm2.5", "aqi", "led"} else word.capitalize() for word in words)


def parse_miot_spec(raw: dict[str, Any]) -> MIoTSpec:
    """Parse enough MIoT-Spec-V2 to build Home Assistant entities."""

    properties: list[MIoTProperty] = []
    actions: list[MIoTAction] = []
    for service in raw.get("services", []) or []:
        siid = service.get("iid")
        if not isinstance(siid, int):
            continue
        service_name = urn_name(str(service.get("type", "")))
        for prop in service.get("properties", []) or []:
            piid = prop.get("iid")
            if not isinstance(piid, int):
                continue
            value_list = [
                MIoTValueListItem(value=item.get("value"), description=str(item.get("description")))
                for item in prop.get("value-list", []) or []
                if "value" in item and "description" in item
            ]
            properties.append(
                MIoTProperty(
                    siid=siid,
                    piid=piid,
                    service_name=service_name,
                    name=urn_name(str(prop.get("type", ""))),
                    description=str(prop.get("description") or ""),
                    format=str(prop.get("format") or ""),
                    access=set(prop.get("access", []) or []),
                    unit=prop.get("unit"),
                    value_range=prop.get("value-range"),
                    value_list=value_list,
                )
            )
        for action in service.get("actions", []) or []:
            aiid = action.get("iid")
            if not isinstance(aiid, int):
                continue
            actions.append(
                MIoTAction(
                    siid=siid,
                    aiid=aiid,
                    service_name=service_name,
                    name=urn_name(str(action.get("type", ""))),
                    description=str(action.get("description") or ""),
                    in_=list(action.get("in", []) or []),
                )
            )
    return MIoTSpec(
        urn=str(raw.get("type") or ""),
        description=str(raw.get("description") or ""),
        properties=properties,
        actions=actions,
    )
