"""Config flow for Xiaomi Home Devices."""

from __future__ import annotations

import logging
from typing import Any
from urllib.parse import parse_qs, urlparse
from uuid import uuid4

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import XiaomiApiError, XiaomiHomeClient, build_oauth_url
from .const import (
    CLOUD_SERVERS,
    CONF_ACCESS_TOKEN,
    CONF_EXPIRES_TS,
    CONF_REDIRECT_URL,
    CONF_REFRESH_TOKEN,
    CONF_REGION,
    CONF_UID,
    CONF_UUID,
    DOMAIN,
    OAUTH_REDIRECT_URL,
)

_LOGGER = logging.getLogger(__name__)


class XiaomiHomeAirConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a Xiaomi Home Devices config flow."""

    VERSION = 1

    def __init__(self) -> None:
        self._region: str | None = None
        self._device_uuid: str | None = None
        self._redirect_url: str | None = None
        self._auth_url: str | None = None

    async def async_step_user(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> config_entries.ConfigFlowResult:
        """Choose Xiaomi cloud region."""

        if user_input is None:
            return self.async_show_form(step_id="user", data_schema=self._region_schema())

        self._region = user_input[CONF_REGION]
        self._device_uuid = uuid4().hex
        self._redirect_url = self._get_redirect_url()
        self._auth_url = build_oauth_url(
            redirect_url=self._redirect_url,
            device_uuid=self._device_uuid,
        )
        return await self.async_step_auth()

    async def async_step_auth(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> config_entries.ConfigFlowResult:
        """Exchange pasted OAuth code or redirected URL."""

        errors: dict[str, str] = {}
        if user_input is not None:
            code = _extract_code(user_input["code"])
            if not code:
                errors["base"] = "missing_code"
            else:
                try:
                    return await self._async_create_entry(code)
                except XiaomiApiError as err:
                    _LOGGER.warning("Xiaomi OAuth failed: %s", err)
                    errors["base"] = "cannot_connect"

        return self.async_show_form(
            step_id="auth",
            data_schema=vol.Schema({vol.Required("code"): str}),
            errors=errors,
            description_placeholders={"auth_url": self._auth_url or ""},
        )

    async def _async_create_entry(self, code: str) -> config_entries.ConfigFlowResult:
        assert self._region is not None
        assert self._device_uuid is not None
        assert self._redirect_url is not None

        session = async_get_clientsession(self.hass)
        client = XiaomiHomeClient(session, region=self._region)
        token = await client.async_get_access_token(
            code=code,
            redirect_url=self._redirect_url,
            device_uuid=self._device_uuid,
        )
        client.update_access_token(token.access_token)
        user_info = await client.async_get_user_info()
        uid = str(user_info.get("userId") or user_info.get("miliaoNick") or "unknown")
        await self.async_set_unique_id(f"{uid}-{self._region}")
        self._abort_if_unique_id_configured()
        nickname = user_info.get("miliaoNick") or uid
        return self.async_create_entry(
            title=f"{nickname} ({CLOUD_SERVERS[self._region]})",
            data={
                CONF_REGION: self._region,
                CONF_UUID: self._device_uuid,
                CONF_REDIRECT_URL: self._redirect_url,
                CONF_UID: uid,
                CONF_ACCESS_TOKEN: token.access_token,
                CONF_REFRESH_TOKEN: token.refresh_token,
                CONF_EXPIRES_TS: token.expires_ts,
            },
        )

    def _get_redirect_url(self) -> str:
        return OAUTH_REDIRECT_URL

    def _region_schema(self) -> vol.Schema:
        return vol.Schema(
            {
                vol.Required(CONF_REGION, default="us"): vol.In(CLOUD_SERVERS),
            }
        )


def _extract_code(value: str) -> str | None:
    """Extract OAuth code from raw code or pasted redirected URL."""

    value = value.strip()
    if not value:
        return None
    parsed = urlparse(value)
    if parsed.query:
        code = parse_qs(parsed.query).get("code", [None])[0]
        if code:
            return code
    return value
