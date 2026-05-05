"""Main Zeekr project API client."""

import hashlib
import json
import logging
import secrets
import time
from typing import Any

from aiohttp import ClientSession

from .const import X_CA_SECRET
from .exceptions import ZeekrAPIError, ZeekrAuthError
from .utils import redact_sensitive

_LOGGER = logging.getLogger(__name__)
BASE_URL = "https://api-gw-toc.zeekrlife.com"


class ClientMain:
    """Main Zeekr project API client."""

    def __init__(
        self,
        session: ClientSession,
        device_id: str,
    ) -> None:
        """Initialize."""
        self._session = session
        self.device_id = device_id
        self.jwt_token = ""

    @staticmethod
    def get_sign(timestamp: str, nonce: str) -> str:
        """Get sign."""
        combined = "".join(sorted([timestamp, nonce, X_CA_SECRET]))
        return hashlib.sha1(combined.encode()).hexdigest()

    def _make_header(self):
        """Make header."""
        timestamp = str(int(time.time() * 1000))
        nonce = str(secrets.choice(range(10_000_000, 100_000_000)))
        user_agent = f"ZeekrLife/4.0.2 (iPhone; iOS 17.4.1; Scale/3.00){self.device_id}"
        headers = {
            "user-agent": user_agent,
            "request-original": "zeekr-app",
            "accept-language": "zh-Hans-CN;q=1, en-CN;q=0.9",
            "content-type": "application/json",
            "x_ca_secret": X_CA_SECRET,
            "accept": "*/*",
            "risktoken": "G4y5f5YrG1BEGxRBBEKF73higM/lOd6e",
            "version": "2",
            "workspaceid": "prod",
            "x_ca_key": "APP-SIGN-SECRET-KEY",
            "app_type": "IOS",
            "app_version": "4.0.2",
            "phone_model": "iPhone13",
            "phone_version": "17.4.1",
            "x_gray_code": "gray74",
            "x_ca_timestamp": timestamp,
            "x_ca_nonce": nonce,
            "x_ca_sign": self.__class__.get_sign(timestamp, nonce),
            "app_code": "toc_ios_zeekrapp",
            "device_id": self.device_id,
        }
        if self.jwt_token:
            headers["authorization"] = self.jwt_token
        return headers

    async def _fetch(self, method: str, url: str, **kwargs: Any):
        """Fetch GW_TOC_API_URL function."""
        full_url = f"{BASE_URL}{url}"
        if kwargs.get("data") is not None:
            kwargs["data"] = json.dumps(kwargs["data"])
        kwargs["headers"] = self._make_header()
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
        code, msg = response.get("code"), response.get("msg", "")
        if str(code) != "000000":
            _LOGGER.error(
                "请求失败 %s result code: %s, response: %s",
                full_url,
                code,
                redact_sensitive(response),
            )
            raise ZeekrAPIError(msg)
        _LOGGER.info("请求成功 %s result code: %s, msg: %s", full_url, code, msg)
        return response.get("data"), code, msg

    async def send_SMS_code(self, phone: str):
        """Send SMS code."""
        return await self._fetch(
            method="get",
            url="/zeekrlife-app-user/v1/user/pub/sms/authCode",
            params={
                "mobile": phone,
                "regionCode": "+86",
                "x_ca_time": str(int(time.time() * 1000)),
            },
        )

    async def login_by_SMS_code(self, phone: str, code: str):
        """Login by SMS code, get main project token."""
        return await self._fetch(
            method="post",
            url="/zeekrlife-app-user/v1/user/pub/login/mobile",
            data={
                "mobile": phone,
                "deviceId": self.device_id,
                "smsCode": code,
                "channel": 2,
                "x_ca_time": str(int(time.time() * 1000)),
                "deviceName": "iPhone13",
                "skipSmsCode": "0",
                "regionCode": "+86",
                "ip": "192.168.1.1",
            },
        )

    async def get_auth_code(self):
        """Get auth code."""
        return await self._fetch(
            method="get",
            url="/zeekrlife-mp-auth2/v1/auth/accessCodeList",
            params={"envType": 3},
        )

    async def get_user_info(self) -> Any:
        """Get user info."""
        return await self._fetch(
            method="get",
            url="/zeekrlife-app-user/v1/user/info/query",
        )
