"""Utility helpers for Zeekr API clients."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

SENSITIVE_KEYS = {
    "authorization",
    "access_token",
    "accessToken",
    "accesstoken",
    "authCode",
    "authcode",
    "device_id",
    "deviceId",
    "deviceid",
    "jwtToken",
    "jwttoken",
    "latitude",
    "longitude",
    "mobile",
    "phone",
    "plateNo",
    "plateno",
    "refresh_token",
    "refreshToken",
    "refreshtoken",
    "smsCode",
    "smscode",
    "token",
    "vin",
    "x-client-id",
    "x-device-id",
    "x-device-identifier",
    "x-vin",
}


def redact_sensitive(value: Any) -> Any:
    """Return a copy of a value with sensitive fields redacted for logging."""
    if isinstance(value, Mapping):
        redacted = {}
        for key, item in value.items():
            key_str = str(key).lower()
            if key_str in SENSITIVE_KEYS:
                redacted[key] = "***"
            else:
                redacted[key] = redact_sensitive(item)
        return redacted
    if isinstance(value, list):
        return [redact_sensitive(item) for item in value]
    if isinstance(value, tuple):
        return tuple(redact_sensitive(item) for item in value)
    return value
