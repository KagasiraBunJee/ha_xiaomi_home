"""Data coordinator for Xiaomi Home Devices."""

from __future__ import annotations

from datetime import timedelta
import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import XiaomiApiError, XiaomiCloudDevice, XiaomiHomeClient
from .const import DEFAULT_SCAN_INTERVAL_SECONDS, DOMAIN
from .spec import MIoTAction, MIoTProperty, MIoTSpec, parse_miot_spec

_LOGGER = logging.getLogger(__name__)


class XiaomiHomeAirCoordinator(DataUpdateCoordinator[dict[str, dict[str, Any]]]):
    """Coordinator that discovers and polls Xiaomi MIoT devices."""

    def __init__(
        self,
        hass: HomeAssistant,
        client: XiaomiHomeClient,
        entry: ConfigEntry,
    ) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            config_entry=entry,
            update_interval=timedelta(seconds=DEFAULT_SCAN_INTERVAL_SECONDS),
        )
        self.client = client
        self.devices: dict[str, XiaomiCloudDevice] = {}
        self.specs: dict[str, MIoTSpec] = {}

    async def _async_update_data(self) -> dict[str, dict[str, Any]]:
        try:
            if not self.devices:
                await self.async_discover_devices()
            return await self._async_poll_devices()
        except XiaomiApiError as err:
            raise UpdateFailed(str(err)) from err

    async def async_discover_devices(self) -> None:
        """Fetch Xiaomi Home devices and their MIoT specs."""

        devices = await self.client.async_get_miot_devices()
        self.devices = {device.did: device for device in devices}
        self.specs = {}
        for device in devices:
            try:
                self.specs[device.did] = parse_miot_spec(
                    await self.client.async_get_spec(device.urn)
                )
            except XiaomiApiError:
                _LOGGER.exception("Unable to load MIoT spec for %s", device.model)

    async def _async_poll_devices(self) -> dict[str, dict[str, Any]]:
        data: dict[str, dict[str, Any]] = {}
        for did, device in self.devices.items():
            spec = self.specs.get(did)
            if not spec:
                data[did] = {"online": False, "values": {}}
                continue
            props = spec.readable_poll_props()
            response = await self.client.async_get_props(
                [{"did": did, "siid": prop.siid, "piid": prop.piid} for prop in props]
            )
            values = {
                f"{item.get('siid')}.{item.get('piid')}": item.get("value")
                for item in response
                if "siid" in item and "piid" in item and "value" in item
            }
            data[did] = {"online": device.online, "values": values}
        return data

    def value(self, did: str, prop: MIoTProperty) -> Any:
        """Return the latest value for a property."""

        return (self.data or {}).get(did, {}).get("values", {}).get(prop.key)

    def available(self, did: str) -> bool:
        """Return availability for a device."""

        return did in self.devices and did in self.specs

    async def async_set_property(self, did: str, prop: MIoTProperty, value: Any) -> None:
        """Set a MIoT property and refresh data."""

        await self.client.async_set_prop(did=did, siid=prop.siid, piid=prop.piid, value=value)
        await self.async_request_refresh()

    async def async_call_action(self, did: str, action: MIoTAction) -> None:
        """Call a MIoT action and refresh data."""

        await self.client.async_action(did=did, siid=action.siid, aiid=action.aiid)
        await self.async_request_refresh()
