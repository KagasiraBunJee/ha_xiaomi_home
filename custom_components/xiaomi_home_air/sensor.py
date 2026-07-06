"""Sensor entities for Xiaomi devices."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity, SensorStateClass
from homeassistant.const import (
    CONCENTRATION_MICROGRAMS_PER_CUBIC_METER,
    PERCENTAGE,
    UnitOfTemperature,
    UnitOfTime,
)

from .coordinator import XiaomiHomeAirCoordinator
from .entity import XiaomiAirEntity
from .spec import MIoTProperty, display_name, is_number_property


@dataclass(frozen=True, slots=True)
class SensorDescription:
    """Static mapping from MIoT property to HA sensor metadata."""

    service: str
    prop: str
    name: str
    device_class: SensorDeviceClass | None = None
    native_unit: str | None = None
    state_class: SensorStateClass | None = SensorStateClass.MEASUREMENT


SENSOR_DESCRIPTIONS = [
    SensorDescription(
        "environment",
        "pm2.5-density",
        "PM2.5",
        SensorDeviceClass.PM25,
        CONCENTRATION_MICROGRAMS_PER_CUBIC_METER,
    ),
    SensorDescription(
        "environment",
        "relative-humidity",
        "Humidity",
        SensorDeviceClass.HUMIDITY,
        PERCENTAGE,
    ),
    SensorDescription(
        "environment",
        "temperature",
        "Temperature",
        SensorDeviceClass.TEMPERATURE,
        UnitOfTemperature.CELSIUS,
    ),
    SensorDescription("filter", "filter-life-level", "Filter Life", None, PERCENTAGE),
    SensorDescription("filter", "filter-used-time", "Filter Used Time", None, UnitOfTime.HOURS),
    SensorDescription("motor-speed", "motor-speed", "Motor Speed", None, None),
    SensorDescription("motor-speed", "motor-set-speed", "Motor Target Speed", None, None),
    SensorDescription("use-time", "use-time", "Use Time", None, UnitOfTime.SECONDS),
    SensorDescription("air-purifier", "fault", "Fault", None, None, None),
]


async def async_setup_entry(hass, entry, async_add_entities) -> None:
    """Set up sensor entities."""

    coordinator: XiaomiHomeAirCoordinator = hass.data["xiaomi_home_air"][entry.entry_id]
    entities = []
    for did, spec in coordinator.specs.items():
        seen: set[str] = set()
        for description in SENSOR_DESCRIPTIONS:
            prop = spec.prop(description.service, description.prop)
            if prop and prop.readable:
                entities.append(XiaomiAirSensor(coordinator, did, prop, description))
                seen.add(prop.key)
        for prop in spec.properties:
            if not _is_generic_sensor(prop, seen):
                continue
            entities.append(XiaomiGenericSensor(coordinator, did, prop))
            seen.add(prop.key)
    async_add_entities(entities)


def _is_generic_sensor(prop: MIoTProperty, seen: set[str]) -> bool:
    if prop.key in seen or not prop.readable:
        return False
    if prop.writable and (prop.format == "bool" or prop.value_list or is_number_property(prop)):
        return False
    return True


class XiaomiAirSensor(XiaomiAirEntity, SensorEntity):
    """Sensor backed by one MIoT property."""

    def __init__(
        self,
        coordinator: XiaomiHomeAirCoordinator,
        did: str,
        prop: MIoTProperty,
        description: SensorDescription,
    ) -> None:
        super().__init__(coordinator, did, f"sensor_{prop.service_name}_{prop.name}")
        self.prop = prop
        self._attr_name = description.name
        self._attr_device_class = description.device_class
        self._attr_native_unit_of_measurement = description.native_unit
        self._attr_state_class = description.state_class

    @property
    def native_value(self) -> Any:
        value = self.coordinator.value(self.did, self.prop)
        if self.prop.value_list:
            return self.prop.option_for_value(value) or value
        return value


class XiaomiGenericSensor(XiaomiAirEntity, SensorEntity):
    """Generic sensor backed by one readable MIoT property."""

    def __init__(
        self,
        coordinator: XiaomiHomeAirCoordinator,
        did: str,
        prop: MIoTProperty,
    ) -> None:
        super().__init__(coordinator, did, f"sensor_{prop.service_name}_{prop.name}")
        self.prop = prop
        self._attr_name = display_name(prop.service_name, prop.name)
        self._attr_native_unit_of_measurement = _unit(prop)
        self._attr_state_class = (
            SensorStateClass.MEASUREMENT if prop.format not in {"bool", "string"} else None
        )

    @property
    def native_value(self) -> Any:
        value = self.coordinator.value(self.did, self.prop)
        if self.prop.value_list:
            return self.prop.option_for_value(value) or value
        return value


def _unit(prop: MIoTProperty) -> str | None:
    if prop.unit == "percentage":
        return PERCENTAGE
    if prop.unit == "celsius":
        return UnitOfTemperature.CELSIUS
    if prop.unit == "hours":
        return UnitOfTime.HOURS
    if prop.unit == "seconds":
        return UnitOfTime.SECONDS
    return prop.unit
