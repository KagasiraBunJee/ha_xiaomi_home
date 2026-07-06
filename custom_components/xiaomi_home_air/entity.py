"""Shared entity helpers for Xiaomi Home Devices."""

from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import XiaomiHomeAirCoordinator


class XiaomiAirEntity(CoordinatorEntity[XiaomiHomeAirCoordinator]):
    """Base entity for one Xiaomi device feature."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: XiaomiHomeAirCoordinator,
        did: str,
        entity_suffix: str,
    ) -> None:
        super().__init__(coordinator)
        self.did = did
        self.device = coordinator.devices[did]
        self._attr_unique_id = f"{did}_{entity_suffix}"

    @property
    def available(self) -> bool:
        return self.coordinator.available(self.did)

    @property
    def device_info(self) -> DeviceInfo:
        return DeviceInfo(
            identifiers={(DOMAIN, self.did)},
            name=self.device.name,
            manufacturer=self.device.manufacturer or "Xiaomi",
            model=self.device.model,
            sw_version=self.device.fw_version,
        )
