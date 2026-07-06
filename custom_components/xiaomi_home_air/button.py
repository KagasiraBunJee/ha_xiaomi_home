"""Button entities for Xiaomi devices."""

from __future__ import annotations

from dataclasses import dataclass

from homeassistant.components.button import ButtonEntity

from .coordinator import XiaomiHomeAirCoordinator
from .entity import XiaomiAirEntity
from .spec import MIoTAction, display_name


@dataclass(frozen=True, slots=True)
class ButtonDescription:
    """Static mapping from MIoT action to HA button metadata."""

    service: str
    action: str
    name: str


BUTTON_DESCRIPTIONS = [
    ButtonDescription("filter", "reset-filter-life", "Reset Filter Life"),
]


async def async_setup_entry(hass, entry, async_add_entities) -> None:
    """Set up button entities."""

    coordinator: XiaomiHomeAirCoordinator = hass.data["xiaomi_home_air"][entry.entry_id]
    entities = []
    for did, spec in coordinator.specs.items():
        seen: set[str] = set()
        for description in BUTTON_DESCRIPTIONS:
            action = spec.action(description.service, description.action)
            if action and not action.in_:
                entities.append(XiaomiAirButton(coordinator, did, action, description))
                seen.add(action.entity_key)
        for action in spec.actions:
            if action.entity_key in seen:
                continue
            if not action.in_:
                entities.append(XiaomiGenericButton(coordinator, did, action))
                seen.add(action.entity_key)
    async_add_entities(entities)


class XiaomiAirButton(XiaomiAirEntity, ButtonEntity):
    """Button backed by a no-argument MIoT action."""

    def __init__(
        self,
        coordinator: XiaomiHomeAirCoordinator,
        did: str,
        action: MIoTAction,
        description: ButtonDescription,
    ) -> None:
        super().__init__(coordinator, did, f"button_{action.service_name}_{action.name}")
        self.action = action
        self._attr_name = description.name

    async def async_press(self) -> None:
        await self.coordinator.async_call_action(self.did, self.action)


class XiaomiGenericButton(XiaomiAirEntity, ButtonEntity):
    """Generic button backed by a no-argument MIoT action."""

    def __init__(
        self,
        coordinator: XiaomiHomeAirCoordinator,
        did: str,
        action: MIoTAction,
    ) -> None:
        super().__init__(coordinator, did, f"button_{action.service_name}_{action.name}")
        self.action = action
        self._attr_name = display_name(action.service_name, action.name)

    async def async_press(self) -> None:
        await self.coordinator.async_call_action(self.did, self.action)
