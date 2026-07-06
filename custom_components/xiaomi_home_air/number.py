"""Number entities for Xiaomi devices."""

from __future__ import annotations

from typing import Any

from homeassistant.components.number import NumberEntity
from homeassistant.const import PERCENTAGE, UnitOfTemperature, UnitOfTime

from .coordinator import XiaomiHomeAirCoordinator
from .entity import XiaomiAirEntity
from .spec import MIoTProperty, display_name, is_number_property


async def async_setup_entry(hass, entry, async_add_entities) -> None:
    """Set up number entities."""

    coordinator: XiaomiHomeAirCoordinator = hass.data["xiaomi_home_air"][entry.entry_id]
    entities = []
    for did, spec in coordinator.specs.items():
        for prop in spec.properties:
            if is_number_property(prop):
                entities.append(XiaomiGenericNumber(coordinator, did, prop))
    async_add_entities(entities)


class XiaomiGenericNumber(XiaomiAirEntity, NumberEntity):
    """Generic number backed by a writable numeric MIoT property."""

    def __init__(
        self,
        coordinator: XiaomiHomeAirCoordinator,
        did: str,
        prop: MIoTProperty,
    ) -> None:
        super().__init__(coordinator, did, f"number_{prop.service_name}_{prop.name}")
        self.prop = prop
        self._attr_name = display_name(prop.service_name, prop.name)
        self._attr_native_unit_of_measurement = _unit(prop)
        if prop.value_range and len(prop.value_range) == 3:
            self._attr_native_min_value = prop.value_range[0]
            self._attr_native_max_value = prop.value_range[1]
            self._attr_native_step = prop.value_range[2]

    @property
    def native_value(self) -> Any:
        return self.coordinator.value(self.did, self.prop)

    async def async_set_native_value(self, value: float) -> None:
        if self.prop.format.startswith(("uint", "int")):
            value = int(value)
        await self.coordinator.async_set_property(self.did, self.prop, value)


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

