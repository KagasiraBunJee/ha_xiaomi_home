"""Small Xiaomi Home MIoT cloud client for device control."""

from __future__ import annotations

import base64
import hashlib
import json
import time
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlencode

from .const import (
    AIR_PURIFIER_URN_FRAGMENT,
    DEFAULT_OAUTH2_API_HOST,
    OAUTH2_AUTH_URL,
    OAUTH2_CLIENT_ID,
)

TOKEN_EXPIRES_TS_RATIO = 0.7
HTTP_TIMEOUT = 30
MAX_PROP_BATCH_SIZE = 150


class XiaomiApiError(Exception):
    """Raised when Xiaomi Home cloud returns an unusable response."""


@dataclass(slots=True)
class XiaomiOAuthToken:
    """OAuth token payload stored in Home Assistant config entries."""

    access_token: str
    refresh_token: str
    expires_ts: int


@dataclass(slots=True)
class XiaomiCloudDevice:
    """Device metadata returned by Xiaomi Home cloud."""

    did: str
    name: str
    model: str
    urn: str
    online: bool
    manufacturer: str | None = None
    token: str | None = None
    local_ip: str | None = None
    fw_version: str | None = None


def cloud_host(region: str) -> str:
    """Return the Xiaomi Home API host for a cloud region."""

    return DEFAULT_OAUTH2_API_HOST if region == "cn" else f"{region}.{DEFAULT_OAUTH2_API_HOST}"


def build_oauth_state(device_uuid: str) -> str:
    """Build the Xiaomi OAuth state used by the official HA client."""

    return hashlib.sha1(f"d=ha.{device_uuid}".encode("utf-8")).hexdigest()


def build_oauth_url(
    *,
    redirect_url: str,
    device_uuid: str,
    state: str | None = None,
    skip_confirm: bool = False,
) -> str:
    """Build the user-facing Xiaomi OAuth authorization URL."""

    query = urlencode(
        {
            "redirect_uri": redirect_url,
            "client_id": int(OAUTH2_CLIENT_ID),
            "response_type": "code",
            "device_id": f"ha.{device_uuid}",
            "state": state or build_oauth_state(device_uuid),
            "skip_confirm": str(skip_confirm).lower(),
        }
    )
    return f"{OAUTH2_AUTH_URL}?{query}"


class XiaomiHomeClient:
    """Minimal async client for Xiaomi OAuth and MIoT cloud APIs."""

    def __init__(
        self,
        session: Any,
        *,
        region: str,
        access_token: str | None = None,
        client_id: str = OAUTH2_CLIENT_ID,
    ) -> None:
        self._session = session
        self.region = region
        self.host = cloud_host(region)
        self.base_url = f"https://{self.host}"
        self.client_id = client_id
        self.access_token = access_token

    async def async_get_access_token(
        self,
        *,
        code: str,
        redirect_url: str,
        device_uuid: str,
    ) -> XiaomiOAuthToken:
        """Exchange an OAuth authorization code for access tokens."""

        return await self._async_get_token(
            {
                "client_id": int(self.client_id),
                "redirect_uri": redirect_url,
                "code": code,
                "device_id": f"ha.{device_uuid}",
            }
        )

    async def async_refresh_access_token(
        self,
        *,
        refresh_token: str,
        redirect_url: str,
    ) -> XiaomiOAuthToken:
        """Refresh an access token."""

        return await self._async_get_token(
            {
                "client_id": int(self.client_id),
                "redirect_uri": redirect_url,
                "refresh_token": refresh_token,
            }
        )

    async def _async_get_token(self, data: dict[str, Any]) -> XiaomiOAuthToken:
        response = await self._session.get(
            f"{self.base_url}/app/v2/ha/oauth/get_token",
            params={"data": json.dumps(data, separators=(",", ":"))},
            headers={"content-type": "application/x-www-form-urlencoded"},
            timeout=HTTP_TIMEOUT,
        )
        payload = await self._json_from_response(response)
        result = payload.get("result")
        if payload.get("code") != 0 or not isinstance(result, dict):
            raise XiaomiApiError(f"invalid OAuth response: {payload}")
        try:
            access_token = str(result["access_token"])
            refresh_token = str(result["refresh_token"])
            expires_in = int(result["expires_in"])
        except (KeyError, TypeError, ValueError) as err:
            raise XiaomiApiError(f"incomplete OAuth response: {payload}") from err
        return XiaomiOAuthToken(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_ts=int(time.time() + expires_in * TOKEN_EXPIRES_TS_RATIO),
        )

    def update_access_token(self, access_token: str) -> None:
        """Update bearer token after config flow or token refresh."""

        self.access_token = access_token

    async def async_get_user_info(self) -> dict[str, Any]:
        """Return Xiaomi account profile information."""

        if not self.access_token:
            raise XiaomiApiError("missing access token")
        response = await self._session.get(
            "https://open.account.xiaomi.com/user/profile",
            params={"clientId": self.client_id, "token": self.access_token},
            headers={"content-type": "application/x-www-form-urlencoded"},
            timeout=HTTP_TIMEOUT,
        )
        payload = await self._json_from_response(response)
        if payload.get("code") != 0 or not isinstance(payload.get("data"), dict):
            raise XiaomiApiError(f"invalid user profile response: {payload}")
        return payload["data"]

    async def async_get_devices(self) -> list[XiaomiCloudDevice]:
        """Fetch all devices visible to the Xiaomi account."""

        devices: list[XiaomiCloudDevice] = []
        start_did: str | None = None
        while True:
            data: dict[str, Any] = {
                "limit": 200,
                "get_split_device": True,
                "get_third_device": True,
                "dids": [],
            }
            if start_did:
                data["start_did"] = start_did
            payload = await self._async_api_post("/app/v2/home/device_list_page", data)
            result = payload.get("result")
            if not isinstance(result, dict):
                raise XiaomiApiError(f"invalid device list response: {payload}")
            for raw in result.get("list", []) or []:
                parsed = self._parse_cloud_device(raw)
                if parsed:
                    devices.append(parsed)
            start_did = result.get("next_start_did")
            if not result.get("has_more") or not start_did:
                return devices

    async def async_get_air_purifiers(self) -> list[XiaomiCloudDevice]:
        """Fetch only MIoT air purifier devices."""

        return [
            device
            for device in await self.async_get_devices()
            if AIR_PURIFIER_URN_FRAGMENT in device.urn
        ]

    async def async_get_miot_devices(self) -> list[XiaomiCloudDevice]:
        """Fetch all devices that expose a MIoT spec type."""

        return [
            device
            for device in await self.async_get_devices()
            if device.urn.startswith("urn:")
        ]

    async def async_get_spec(self, urn: str) -> dict[str, Any]:
        """Fetch the MIoT-Spec-V2 instance for a device URN."""

        response = await self._session.get(
            "https://miot-spec.org/miot-spec-v2/instance",
            params={"type": urn},
            timeout=HTTP_TIMEOUT,
        )
        payload = await self._json_from_response(response)
        if not isinstance(payload.get("services"), list):
            raise XiaomiApiError(f"invalid MIoT spec response for {urn}: {payload}")
        return payload

    async def async_get_props(self, params: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Read MIoT properties."""

        if not params:
            return []
        if len(params) > MAX_PROP_BATCH_SIZE:
            results: list[dict[str, Any]] = []
            for index in range(0, len(params), MAX_PROP_BATCH_SIZE):
                results.extend(await self.async_get_props(params[index : index + MAX_PROP_BATCH_SIZE]))
            return results
        payload = await self._async_api_post(
            "/app/v2/miotspec/prop/get",
            {"datasource": 1, "params": params},
        )
        result = payload.get("result")
        if not isinstance(result, list):
            raise XiaomiApiError(f"invalid get props response: {payload}")
        return result

    async def async_set_prop(self, *, did: str, siid: int, piid: int, value: Any) -> None:
        """Set one MIoT property and raise if Xiaomi reports an error."""

        payload = await self._async_api_post(
            "/app/v2/miotspec/prop/set",
            {"params": [{"did": did, "siid": siid, "piid": piid, "value": value}]},
            timeout=15,
        )
        self._raise_for_result_code(payload)

    async def async_action(
        self,
        *,
        did: str,
        siid: int,
        aiid: int,
        values: list[Any] | None = None,
    ) -> None:
        """Call one MIoT action."""

        payload = await self._async_api_post(
            "/app/v2/miotspec/action",
            {"params": {"did": did, "siid": siid, "aiid": aiid, "in": values or []}},
            timeout=15,
        )
        self._raise_for_result_code(payload)

    async def _async_api_post(
        self,
        path: str,
        data: dict[str, Any],
        timeout: int = HTTP_TIMEOUT,
    ) -> dict[str, Any]:
        if not self.access_token:
            raise XiaomiApiError("missing access token")
        response = await self._session.post(
            f"{self.base_url}{path}",
            json=data,
            headers=self._api_headers,
            timeout=timeout,
        )
        payload = await self._json_from_response(response)
        if payload.get("code") != 0:
            raise XiaomiApiError(f"Xiaomi API error for {path}: {payload}")
        return payload

    @property
    def _api_headers(self) -> dict[str, str]:
        return {
            "Host": self.host,
            "X-Client-BizId": "haapi",
            "Content-Type": "application/json",
            "Authorization": f"Bearer{self.access_token}",
            "X-Client-AppId": self.client_id,
        }

    async def _json_from_response(self, response: Any) -> dict[str, Any]:
        status = getattr(response, "status", None)
        text = await response.text()
        if status != 200:
            raise XiaomiApiError(f"unexpected HTTP status {status}: {text}")
        try:
            return json.loads(text)
        except json.JSONDecodeError as err:
            raise XiaomiApiError(f"invalid JSON response: {text}") from err

    def _parse_cloud_device(self, raw: dict[str, Any]) -> XiaomiCloudDevice | None:
        did = raw.get("did")
        name = raw.get("name")
        urn = raw.get("spec_type")
        model = raw.get("model")
        if not all(isinstance(value, str) and value for value in (did, name, urn, model)):
            return None
        return XiaomiCloudDevice(
            did=did,
            name=name,
            model=model,
            urn=urn,
            online=bool(raw.get("isOnline", False)),
            manufacturer=model.split(".")[0] if "." in model else None,
            token=raw.get("token"),
            local_ip=raw.get("local_ip"),
            fw_version=(raw.get("extra") or {}).get("fw_version"),
        )

    def _raise_for_result_code(self, payload: dict[str, Any]) -> None:
        result = payload.get("result")
        if isinstance(result, list) and result:
            code = result[0].get("code")
        elif isinstance(result, dict):
            code = result.get("code")
        else:
            code = None
        if code not in (0, 1):
            raise XiaomiApiError(f"MIoT command failed: {payload}")


def decode_basic_token(token: str) -> str:
    """Return a short safe token preview for diagnostics."""

    digest = base64.urlsafe_b64encode(hashlib.sha256(token.encode()).digest())[:8]
    return digest.decode("ascii")
