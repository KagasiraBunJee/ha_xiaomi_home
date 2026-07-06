"""Constants for Xiaomi Home Devices."""

from __future__ import annotations

DOMAIN = "xiaomi_home_air"
NAME = "Xiaomi Home Devices"

OAUTH2_CLIENT_ID = "2882303761520251711"
OAUTH2_AUTH_URL = "https://account.xiaomi.com/oauth2/authorize"
DEFAULT_OAUTH2_API_HOST = "ha.api.io.mi.com"
OAUTH_REDIRECT_URL = "http://homeassistant.local:8123"

CONF_REGION = "region"
CONF_UUID = "uuid"
CONF_REDIRECT_URL = "redirect_url"
CONF_UID = "uid"
CONF_ACCESS_TOKEN = "access_token"
CONF_REFRESH_TOKEN = "refresh_token"
CONF_EXPIRES_TS = "expires_ts"

CLOUD_SERVERS = {
    "cn": "Mainland China",
    "de": "Europe",
    "i2": "India",
    "ru": "Russia",
    "sg": "Singapore",
    "us": "United States",
}

AIR_PURIFIER_URN_FRAGMENT = "device:air-purifier:0000A007"
DEFAULT_SCAN_INTERVAL_SECONDS = 60
