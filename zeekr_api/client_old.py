"""Old model Zeekr vehicle API client."""

import base64
import hashlib
import hmac
import json
import logging
import time
import uuid
from typing import Any
from urllib import parse
from urllib.parse import quote

from aiohttp import ClientSession

from .const import SECRET_KEY
from .exceptions import ZeekrAPIError, ZeekrAuthError
from .utils import redact_sensitive

_LOGGER = logging.getLogger(__name__)
BASE_URL = "https://api.zeekrline.com"


class ClientOld:
    """Old model Zeekr vehicle API client."""

    def __init__(
        self,
        session: ClientSession,
        device_id: str,
    ) -> None:
        """Initialize."""
        self.device_id = device_id
        self._session = session
        self.user_id = ""
        self.client_id = ""
        self.access_token = ""
        self.refresh_token = ""

    @staticmethod
    def get_sign(method: str, url: str, headers: dict, **kwargs: Any) -> str:
        """Get sign."""
        nonce = headers.get("x-api-signature-nonce")
        timestamp = headers.get("x-timestamp")
        params = kwargs.get("params")
        data = kwargs.get("data") or ""
        data_md5 = base64.b64encode(
            hashlib.md5(data.encode() if data else b"").digest()
        ).decode()
        sorted_params: str = ""
        if params:
            sorted_params = parse.urlencode(
                {k: params[k] for k in sorted(params.keys())}, doseq=True
            )
        # Note: this hardcoded mime string is what the zeekr_old server expects
        # in the signing canon (despite request content-type header being plain
        # "application/json"). R5 (Phase 7) tried to read from headers dynamically
        # — that broke signing with code 1445 "验签签名错误". Reverted to literal.
        lines = [
            "application/json;responseformat=3",
            f"x-api-signature-nonce:{nonce}",
            "x-api-signature-version:1.0",
            "",
            sorted_params,
            data_md5,
            timestamp,
            method.upper(),
            url,
        ]
        sign_str: str = "\n".join(lines)
        signature: str = base64.b64encode(
            hmac.new(SECRET_KEY.encode(), sign_str.encode(), hashlib.sha1).digest()
        ).decode()
        return signature

    def _make_header(self, method: str, url: str, **kwargs: Any):
        """Make header."""
        timestamp = str(int(time.time() * 1000))
        nonce = str(uuid.uuid4()).upper()
        headers = {
            "x-timestamp": timestamp,
            "x-api-signature-nonce": nonce,
            "content-type": "application/json",
            "x-api-signature-version": "1.0",
            "x-app-id": "ZEEKRAPP",
            "user-agent": "ZeekrLife/4.0.2 (iPhone; iOS 17.4.1; Scale/3.00)",
            "x-device-model": "iPhone",
            "x-device-manufacture": "Apple",
            "x-agent-type": "iOS",
            "x-device-type": "mobile",
            "platform": "NON-CMA",
            "x-env-type": "production",
            "accept-language": "zh-Hans-CN;q=1, en-CN;q=0.9",
            "x-agent-version": "17.4.1",
            "accept": "application/json;responseformat=3",
            "x-device-brand": "Apple",
            "x-operator-code": "ZEEKR",
            "x-device-identifier": self.device_id,
        }
        headers.update(kwargs.pop("headers", {}))
        headers["x-signature"] = self.__class__.get_sign(method, url, headers, **kwargs)
        if self.access_token:
            headers["authorization"] = self.access_token
        if self.client_id:
            headers["x-client-id"] = self.client_id
        return headers

    async def _fetch(self, method: str, url: str, **kwargs: Any):
        """Fetch API_URL function."""
        full_url = f"{BASE_URL}{url}"
        if kwargs.get("data") is not None:
            kwargs["data"] = json.dumps(kwargs["data"])
        kwargs["headers"] = self._make_header(method, url, **kwargs)
        async with self._session.request(method=method, url=full_url, **kwargs) as r:
            status = r.status
            raw = await r.read()
            _LOGGER.info(
                "发送请求\nmethod: %s \nurl: %s \nkwargs: %s",
                method,
                full_url,
                redact_sensitive(kwargs),
            )
            if status != 200:
                _LOGGER.error(
                    "请求出错 %s result status: %s, reason: %s",
                    full_url,
                    status,
                    r.reason,
                )
                error_msg = f"response status {status}"
                if status == 401:
                    raise ZeekrAuthError(error_msg)
                raise ZeekrAPIError(error_msg)
            try:
                response = json.loads(raw)
            except json.JSONDecodeError as err:
                raise ZeekrAPIError("invalid JSON response") from err
        code, msg = response.get("code"), response.get("message", "")
        if str(code) != "1000":
            _LOGGER.error(
                "请求失败 %s result code: %s, response: %s",
                full_url,
                code,
                redact_sensitive(response),
            )
            raise ZeekrAPIError(msg)
        _LOGGER.info("请求成功 %s result code: %s, msg: %s", full_url, code, msg)
        return response.get("data"), code, msg

    async def auth_by_auth_code(self, auth_code: str):
        """通过授权码授权."""
        data, code, msg = await self._fetch(
            method="post",
            url="/auth/account/session/secure",
            params={
                "identity_type": "zeekr",
            },
            data={"authCode": auth_code},
        )
        self.user_id = data["userId"]
        self.client_id = data["clientId"]
        self.access_token = data["accessToken"]
        self.refresh_token = data["refreshToken"]
        return data, code, msg

    async def auth_by_refresh_token(self):
        """Authorize vehicle security by refresh token."""
        data, code, msg = await self._fetch(
            method="put",
            url="/auth/account/session/secure",
            data={"refreshToken": self.refresh_token},
        )
        self.access_token = data["accessToken"]
        self.refresh_token = data["refreshToken"]
        return data, code, msg

    async def get_vehicles(self):
        """Get old model vehicle list."""
        return await self._fetch(
            method="get",
            url="/device-platform/user/vehicle/secure",
            params={
                "id": self.user_id,
                "needSharedCar": 1,
            },
        )

    async def get_vehicle_data(self, vin: str):
        """Get old model vehicle data."""
        return await self._fetch(
            method="get",
            url=f"/remote-control/vehicle/status/{vin}",
            params={
                "latest": "Local",
                "target": quote("basic,more", safe=""),
                "userId": self.user_id,
            },
        )
