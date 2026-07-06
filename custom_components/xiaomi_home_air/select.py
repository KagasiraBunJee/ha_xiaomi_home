"""Select entities for Xiaomi devices."""

from __future__ import annotations

from dataclasses import dataclass

from homeassistant.components.select import SelectEntity

from .coordinator import XiaomiHomeAirCoordinator
from .entity import XiaomiAirEntity
from .spec import MIoTProperty, display_name


@dataclass(frozen=True, slots=True)
class SelectDescription:
    """Static mapping from MIoT value-list property to HA select metadata."""

    service: str
    prop: str
    name: str


SELECT_DESCRIPTIONS = [
    SelectDescription("air-purifier", "mode", "Mode"),
    SelectDescription("indicator-light", "brightness", "Display Brightness"),
]


async def async_setup_entry(hass, entry, async_add_entities) -> None:
    """Set up select entities."""

    coordinator: XiaomiHomeAirCoordinator = hass.data["xiaomi_home_air"][entry.entry_id]
    entities = []
    for did, spec in coordinator.specs.items():
        seen: set[str] = set()
        for description in SELECT_DESCRIPTIONS:
            prop = spec.prop(description.service, description.prop)
            if prop and prop.readable and prop.writable and prop.value_list:
                entities.append(XiaomiAirSelect(coordinator, did, prop, description))
                seen.add(prop.key)
        for prop in spec.properties:
            if prop.key in seen:
                continue
            if prop.readable and prop.writable and prop.value_list and prop.format != "bool":
                entities.append(XiaomiGenericSelect(coordinator, did, prop))
                seen.add(prop.key)
    async_add_entities(entities)


class XiaomiAirSelect(XiaomiAirEntity, SelectEntity):
    """Select backed by a MIoT value-list property."""

    def __init__(
        self,
        coordinator: XiaomiHomeAirCoordinator,
        did: str,
        prop: MIoTProperty,
        description: SelectDescription,
    ) -> None:
        super().__init__(coordinator, did, f"select_{prop.service_name}_{prop.name}")
        self.prop = prop
        self._attr_name = description.name
        self._attr_options = prop.options

    @property
    def current_option(self) -> str | None:
        return self.prop.option_for_value(self.coordinator.value(self.did, self.prop))

    async def async_select_option(self, option: str) -> None:
        await self.coordinator.async_set_property(
            self.did,
            self.prop,
            self.prop.value_for_option(option),
        )


class XiaomiGenericSelect(XiaomiAirEntity, SelectEntity):
    """Generic select backed by a MIoT value-list property."""

    def __init__(
        self,
        coordinator: XiaomiHomeAirCoordinator,
        did: str,
        prop: MIoTProperty,
    ) -> None:
        super().__init__(coordinator, did, f"select_{prop.service_name}_{prop.name}")
        self.prop = prop
        self._attr_name = display_name(prop.service_name, prop.name)
        self._attr_options = prop.options

    @property
    def current_option(self) -> str | None:
        return self.prop.option_for_value(self.coordinator.value(self.did, self.prop))

    async def async_select_option(self, option: str) -> None:
        await self.coordinator.async_set_property(
            self.did,
            self.prop,
            self.prop.value_for_option(option),
        )
