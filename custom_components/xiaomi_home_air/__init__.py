"""Xiaomi Home Devices custom integration."""

from __future__ import annotations

import logging
import time

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import XiaomiApiError, XiaomiHomeClient
from .const import (
    CONF_ACCESS_TOKEN,
    CONF_EXPIRES_TS,
    CONF_REDIRECT_URL,
    CONF_REFRESH_TOKEN,
    CONF_REGION,
    DOMAIN,
)
from .coordinator import XiaomiHomeAirCoordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS = [
    Platform.FAN,
    Platform.SENSOR,
    Platform.SWITCH,
    Platform.SELECT,
    Platform.NUMBER,
    Platform.BUTTON,
]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Xiaomi Home Devices from a config entry."""

    hass.data.setdefault(DOMAIN, {})
    session = async_get_clientsession(hass)
    client = XiaomiHomeClient(
        session,
        region=entry.data[CONF_REGION],
        access_token=entry.data[CONF_ACCESS_TOKEN],
    )
    await _async_refresh_token_if_needed(hass, entry, client)
    coordinator = XiaomiHomeAirCoordinator(hass, client, entry)
    await coordinator.async_config_entry_first_refresh()
    hass.data[DOMAIN][entry.entry_id] = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""

    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id, None)
    return unload_ok


async def _async_refresh_token_if_needed(
    hass: HomeAssistant,
    entry: ConfigEntry,
    client: XiaomiHomeClient,
) -> None:
    """Refresh OAuth token when it is close to expiry."""

    expires_ts = int(entry.data.get(CONF_EXPIRES_TS, 0))
    if expires_ts - int(time.time()) > 300:
        return
    try:
        token = await client.async_refresh_access_token(
            refresh_token=entry.data[CONF_REFRESH_TOKEN],
            redirect_url=entry.data[CONF_REDIRECT_URL],
        )
    except XiaomiApiError as err:
        _LOGGER.warning("Unable to refresh Xiaomi OAuth token: %s", err)
        return
    client.update_access_token(token.access_token)
    hass.config_entries.async_update_entry(
        entry,
        data={
            **entry.data,
            CONF_ACCESS_TOKEN: token.access_token,
            CONF_REFRESH_TOKEN: token.refresh_token,
            CONF_EXPIRES_TS: token.expires_ts,
        },
    )
