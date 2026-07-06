"""Fan entities for Xiaomi devices."""

from __future__ import annotations

from typing import Any

from homeassistant.components.fan import FanEntity, FanEntityFeature

from .coordinator import XiaomiHomeAirCoordinator
from .entity import XiaomiAirEntity
from .spec import MIoTProperty


async def async_setup_entry(hass, entry, async_add_entities) -> None:
    """Set up fan entities."""

    coordinator: XiaomiHomeAirCoordinator = hass.data["xiaomi_home_air"][entry.entry_id]
    entities = []
    for did, spec in coordinator.specs.items():
        power = spec.prop("air-purifier", "on")
        if power:
            entities.append(XiaomiAirPurifierFan(coordinator, did, power))
    async_add_entities(entities)


class XiaomiAirPurifierFan(XiaomiAirEntity, FanEntity):
    """Air purifier main fan control."""

    _attr_name = None

    def __init__(
        self,
        coordinator: XiaomiHomeAirCoordinator,
        did: str,
        power: MIoTProperty,
    ) -> None:
        super().__init__(coordinator, did, "fan")
        spec = coordinator.specs[did]
        self.power = power
        self.mode = spec.prop("air-purifier", "mode")
        self.fan_level = spec.prop("air-purifier", "fan-level")

    @property
    def supported_features(self) -> FanEntityFeature:
        features = FanEntityFeature.TURN_ON | FanEntityFeature.TURN_OFF
        if self.mode and self.mode.value_list:
            features |= FanEntityFeature.PRESET_MODE
        if self.fan_level and self.fan_level.value_list:
            features |= FanEntityFeature.SET_SPEED
        return features

    @property
    def is_on(self) -> bool | None:
        value = self.coordinator.value(self.did, self.power)
        return bool(value) if value is not None else None

    @property
    def preset_modes(self) -> list[str] | None:
        return self.mode.options if self.mode and self.mode.value_list else None

    @property
    def preset_mode(self) -> str | None:
        if not self.mode:
            return None
        return self.mode.option_for_value(self.coordinator.value(self.did, self.mode))

    @property
    def percentage(self) -> int | None:
        if not self.fan_level or not self.fan_level.value_list:
            return None
        value = self.coordinator.value(self.did, self.fan_level)
        values = [item.value for item in self.fan_level.value_list]
        if value not in values:
            return None
        return round(((values.index(value) + 1) / len(values)) * 100)

    @property
    def percentage_step(self) -> int | None:
        if not self.fan_level or not self.fan_level.value_list:
            return None
        return round(100 / len(self.fan_level.value_list))

    async def async_turn_on(
        self,
        percentage: int | None = None,
        preset_mode: str | None = None,
        **kwargs: Any,
    ) -> None:
        await self.coordinator.async_set_property(self.did, self.power, True)
        if preset_mode:
            await self.async_set_preset_mode(preset_mode)
        elif percentage is not None:
            await self.async_set_percentage(percentage)

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self.coordinator.async_set_property(self.did, self.power, False)

    async def async_set_preset_mode(self, preset_mode: str) -> None:
        if not self.mode:
            return
        await self.coordinator.async_set_property(
            self.did,
            self.mode,
            self.mode.value_for_option(preset_mode),
        )

    async def async_set_percentage(self, percentage: int) -> None:
        if not self.fan_level or not self.fan_level.value_list:
            return
        index = min(
            len(self.fan_level.value_list) - 1,
            max(0, round((percentage / 100) * len(self.fan_level.value_list)) - 1),
        )
        await self.coordinator.async_set_property(
            self.did,
            self.fan_level,
            self.fan_level.value_list[index].value,
        )
