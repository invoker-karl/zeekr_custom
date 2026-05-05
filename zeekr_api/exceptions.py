"""Exceptions for the Zeekr web API."""


class ZeekrAPIError(Exception):
    """General Zeekr web API error."""


class ZeekrAuthError(ZeekrAPIError):
    """Auth-related error from Zeekr web API (HTTP status codes 401)."""
