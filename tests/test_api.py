"""Tests for the Xiaomi Home cloud client."""

from __future__ import annotations

import json

import pytest

from custom_components.xiaomi_home_air.api import (
    XiaomiHomeClient,
    build_oauth_state,
    build_oauth_url,
)


class FakeResponse:
    """Small aiohttp response stand-in."""

    def __init__(self, payload, status=200):
        self.payload = payload
        self.status = status

    async def text(self):
        return json.dumps(self.payload)


class FakeSession:
    """Record requests and return queued responses."""

    def __init__(self):
        self.get_responses = []
        self.post_responses = []
        self.get_calls = []
        self.post_calls = []

    async def get(self, url, **kwargs):
        self.get_calls.append((url, kwargs))
        return FakeResponse(self.get_responses.pop(0))

    async def post(self, url, **kwargs):
        self.post_calls.append((url, kwargs))
        return FakeResponse(self.post_responses.pop(0))


@pytest.mark.asyncio
async def test_oauth_url_and_token_exchange():
    session = FakeSession()
    session.get_responses.append(
        {
            "code": 0,
            "result": {
                "access_token": "access",
                "refresh_token": "refresh",
                "expires_in": 3600,
            },
        }
    )
    client = XiaomiHomeClient(session, region="us")

    auth_url = build_oauth_url(redirect_url="http://ha.local:8123", device_uuid="abc")

    assert "client_id=2882303761520251711" in auth_url
    assert build_oauth_state("abc") in auth_url

    token = await client.async_get_access_token(
        code="the-code",
        redirect_url="http://ha.local:8123",
        device_uuid="abc",
    )

    assert token.access_token == "access"
    assert token.refresh_token == "refresh"
    assert session.get_calls[0][0] == "https://us.ha.api.io.mi.com/app/v2/ha/oauth/get_token"
    data = json.loads(session.get_calls[0][1]["params"]["data"])
    assert data["code"] == "the-code"
    assert data["device_id"] == "ha.abc"


@pytest.mark.asyncio
async def test_air_purifier_discovery_filters_by_urn():
    session = FakeSession()
    session.post_responses.append(
        {
            "code": 0,
            "result": {
                "has_more": False,
                "list": [
                    {
                        "did": "1",
                        "name": "Purifier",
                        "model": "zhimi.airpurifier.mb3",
                        "spec_type": "urn:miot-spec-v2:device:air-purifier:0000A007:zhimi-mb3:1",
                        "isOnline": True,
                    },
                    {
                        "did": "2",
                        "name": "Lamp",
                        "model": "yeelink.light.foo",
                        "spec_type": "urn:miot-spec-v2:device:light:0000A001:yeelink-foo:1",
                        "isOnline": True,
                    },
                ],
            },
        }
    )
    client = XiaomiHomeClient(session, region="de", access_token="token")

    devices = await client.async_get_air_purifiers()

    assert [device.did for device in devices] == ["1"]
    assert session.post_calls[0][0] == "https://de.ha.api.io.mi.com/app/v2/home/device_list_page"
    assert session.post_calls[0][1]["headers"]["Authorization"] == "Bearertoken"


@pytest.mark.asyncio
async def test_miot_device_discovery_keeps_all_spec_devices():
    session = FakeSession()
    session.post_responses.append(
        {
            "code": 0,
            "result": {
                "has_more": False,
                "list": [
                    {
                        "did": "1",
                        "name": "Purifier",
                        "model": "zhimi.airpurifier.mb3",
                        "spec_type": "urn:miot-spec-v2:device:air-purifier:0000A007:zhimi-mb3:1",
                        "isOnline": True,
                    },
                    {
                        "did": "2",
                        "name": "Lamp",
                        "model": "yeelink.light.foo",
                        "spec_type": "urn:miot-spec-v2:device:light:0000A001:yeelink-foo:1",
                        "isOnline": True,
                    },
                    {
                        "did": "3",
                        "name": "Legacy",
                        "model": "legacy.device",
                        "spec_type": "",
                        "isOnline": True,
                    },
                ],
            },
        }
    )
    client = XiaomiHomeClient(session, region="de", access_token="token")

    devices = await client.async_get_miot_devices()

    assert [device.did for device in devices] == ["1", "2"]


@pytest.mark.asyncio
async def test_set_prop_and_action_payloads():
    session = FakeSession()
    session.post_responses.extend(
        [
            {"code": 0, "result": [{"code": 0}]},
            {"code": 0, "result": {"code": 0, "out": []}},
        ]
    )
    client = XiaomiHomeClient(session, region="cn", access_token="token")

    await client.async_set_prop(did="123", siid=2, piid=2, value=True)
    await client.async_action(did="123", siid=4, aiid=1)

    assert session.post_calls[0][0] == "https://ha.api.io.mi.com/app/v2/miotspec/prop/set"
    assert session.post_calls[0][1]["json"] == {
        "params": [{"did": "123", "siid": 2, "piid": 2, "value": True}]
    }
    assert session.post_calls[1][1]["json"] == {
        "params": {"did": "123", "siid": 4, "aiid": 1, "in": []}
    }
