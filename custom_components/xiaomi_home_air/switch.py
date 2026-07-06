"""Switch entities for Xiaomi devices."""

from __future__ import annotations

from dataclasses import dataclass

from homeassistant.components.switch import SwitchEntity

from .coordinator import XiaomiHomeAirCoordinator
from .entity import XiaomiAirEntity
from .spec import MIoTProperty, display_name


@dataclass(frozen=True, slots=True)
class SwitchDescription:
    """Static mapping from MIoT property to HA switch metadata."""

    service: str
    prop: str
    name: str


SWITCH_DESCRIPTIONS = [
    SwitchDescription("physical-controls-locked", "physical-controls-locked", "Child Lock"),
    SwitchDescription("alarm", "alarm", "Buzzer"),
    SwitchDescription("indicator-light", "on", "Display"),
]


async def async_setup_entry(hass, entry, async_add_entities) -> None:
    """Set up switch entities."""

    coordinator: XiaomiHomeAirCoordinator = hass.data["xiaomi_home_air"][entry.entry_id]
    entities = []
    for did, spec in coordinator.specs.items():
        seen: set[str] = set()
        for description in SWITCH_DESCRIPTIONS:
            prop = spec.prop(description.service, description.prop)
            if prop and prop.readable and prop.writable and prop.format == "bool":
                entities.append(XiaomiAirSwitch(coordinator, did, prop, description))
                seen.add(prop.key)
        for prop in spec.properties:
            if prop.key in seen:
                continue
            if prop.readable and prop.writable and prop.format == "bool":
                entities.append(XiaomiGenericSwitch(coordinator, did, prop))
                seen.add(prop.key)
    async_add_entities(entities)


class XiaomiAirSwitch(XiaomiAirEntity, SwitchEntity):
    """Switch backed by a bool MIoT property."""

    def __init__(
        self,
        coordinator: XiaomiHomeAirCoordinator,
        did: str,
        prop: MIoTProperty,
        description: SwitchDescription,
    ) -> None:
        super().__init__(coordinator, did, f"switch_{prop.service_name}_{prop.name}")
        self.prop = prop
        self._attr_name = description.name

    @property
    def is_on(self) -> bool | None:
        value = self.coordinator.value(self.did, self.prop)
        return bool(value) if value is not None else None

    async def async_turn_on(self, **kwargs) -> None:
        await self.coordinator.async_set_property(self.did, self.prop, True)

    async def async_turn_off(self, **kwargs) -> None:
        await self.coordinator.async_set_property(self.did, self.prop, False)


class XiaomiGenericSwitch(XiaomiAirEntity, SwitchEntity):
    """Generic switch backed by a bool MIoT property."""

    def __init__(
        self,
        coordinator: XiaomiHomeAirCoordinator,
        did: str,
        prop: MIoTProperty,
    ) -> None:
        super().__init__(coordinator, did, f"switch_{prop.service_name}_{prop.name}")
        self.prop = prop
        self._attr_name = display_name(prop.service_name, prop.name)

    @property
    def is_on(self) -> bool | None:
        value = self.coordinator.value(self.did, self.prop)
        return bool(value) if value is not None else None

    async def async_turn_on(self, **kwargs) -> None:
        await self.coordinator.async_set_property(self.did, self.prop, True)

    async def async_turn_off(self, **kwargs) -> None:
        await self.coordinator.async_set_property(self.did, self.prop, False)
