"""New model Zeekr vehicle API client."""

import base64
import hashlib
import hmac
import json
import logging
import time
import uuid
from typing import Any

from aiohttp import ClientSession
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad

from .const import AES_IV, AES_KEY, APP_SECRET, TO_BE_SIGNED_HEADER
from .exceptions import ZeekrAPIError, ZeekrAuthError
from .utils import redact_sensitive

_LOGGER = logging.getLogger(__name__)
BASE_URL = "https://snc-tsp-api.zeekrlife.com"


class ClientNew:
    """New model Zeekr vehicle API client."""

    def __init__(
        self,
        session: ClientSession,
        device_id: str,
    ) -> None:
        """Initialize."""
        self._session = session
        self.device_id = device_id
        self.access_token = None
        self.refresh_token = None

    @staticmethod
    def get_sign(method: str, url: str, headers: dict, **kwargs: Any) -> str:
        """Get sign."""
        content_type: str = ""
        # 1. 处理 header
        header_keys: list[str] = sorted(
            (k for k in headers if k.lower() in TO_BE_SIGNED_HEADER),
            key=lambda x: x.lower(),
        )
        header_part_lines: list[str] = []
        for key in header_keys:
            value = headers[key]
            if isinstance(value, list):
                value = ",".join(value)
            if key.lower() in ("x-vin", "authorization") and (not value):
                continue
            if key.lower() == "content-type":
                content_type = value
            header_part_lines.append(f"{key.lower()}:{value}\n")
        header_part: str = "".join(header_part_lines)

        # 2. 处理 query
        query_part: str = ""
        params = kwargs.get("params")
        if params:
            for k in sorted(params.keys()):
                v = params[k]
                escaped: str = (
                    v.replace("*", "%2A").replace("%2F", "/").replace("%3F", "?")
                    if isinstance(v, str)
                    else str(v)
                )
                if query_part:
                    query_part += "&"
                query_part += f"{k}={escaped}"
            if query_part:
                query_part += "\n"

        # 3. 处理 body MD5（仅 application/json 且有 body）。
        # GET 请求服务端不期望 MD5 行 — 必须 skip 而非发送 empty MD5,
        # 否则签名串多一行导致服务端验签失败 ("验签签名错误")。
        # R4 (Phase 7) 曾尝试 always-emit empty MD5,经实测服务端拒签,回退。
        data = kwargs.get("data")
        data_md5_part: str = ""
        if "application/json" in content_type and data is not None:
            md5_digest = hashlib.md5(data.encode()).digest()
            data_md5_part = base64.b64encode(md5_digest).decode() + "\n"

        # 4. 构造待签名字符串
        canon_parts = [
            header_part,
            query_part,
            data_md5_part,
            method.upper() + "\n",
            url,
        ]
        canon: str = "".join(canon_parts)
        _LOGGER.debug("待签名字符串: %s", canon)
        # 5. HMAC-SHA256 + Base64
        return base64.b64encode(
            hmac.new(APP_SECRET.encode(), canon.encode(), hashlib.sha256).digest()
        ).decode()

    def _make_header(self, method: str, url: str, **kwargs: Any):
        """Make header."""
        timestamp = str(int(time.time() * 1000))
        nonce = str(uuid.uuid4()).upper()
        headers = {
            "X-APP-ID": "ZEEKRCNCH001M0000",
            "X-TIMESTAMP": timestamp,
            "X-API-SIGNATURE-VERSION": "2.0",
            "X-SIGNATURE": "",
            "Accept-Language": "zh-CN",
            "Accept-Encoding": "gzip, deflate, br",
            "Content-Type": "application/json;charset=UTF-8",
            "X-PROJECT-ID": "ZEEKR",
            "X-P": "iOS",
            "X-DEVICE-ID": self.device_id,
            "X-APP-OS-VERSION": "4.9.9",
            "X-PLATFORM": "APP",
            "X-API-SIGNATURE-NONCE": nonce,
            "User-Agent": "ZeekrLife/2025061706 CFNetwork/3826.500.131 Darwin/24.5.0",
        }
        headers.update(kwargs.pop("headers", {}))
        if self.access_token and not headers.get("Authorization"):
            headers["Authorization"] = self.access_token
        # Encrypt X-VIN before signing (do not let get_sign mutate input)
        for key in list(headers.keys()):
            if key.lower() == "x-vin" and headers[key]:
                cipher = AES.new(AES_KEY.encode(), AES.MODE_CBC, AES_IV.encode())
                ct_bytes = cipher.encrypt(pad(headers[key].encode(), AES.block_size))
                headers[key] = base64.b64encode(ct_bytes).decode()
        headers["X-SIGNATURE"] = self.__class__.get_sign(method, url, headers, **kwargs)
        return headers

    async def _fetch(self, method: str, url: str, **kwargs: Any):
        """Fetch SNC_TSP_API_URL function."""
        full_url = f"{BASE_URL}{url}"
        if kwargs.get("data") is not None:
            kwargs["data"] = json.dumps(kwargs["data"])
        kwargs["headers"] = self._make_header(method, url, **kwargs)
        _LOGGER.info(
            "发送请求\nmethod: %s \nurl: %s \nkwargs: %s",
            method,
            full_url,
            redact_sensitive(kwargs),
        )
        async with self._session.request(method=method, url=full_url, **kwargs) as r:
            status = r.status
            raw = await r.read()
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

    async def auth_by_main_token(self, token: str):
        """Authorize vehicle security by main project token."""
        data, code, msg = await self._fetch(
            method="post",
            url="/ms-user-auth/v1.0/auth/login",
            data={
                "loginDeviceType": 1,
                "identityType": 5,
                "loginSystem": "ios",
                "loginDeviceId": self.device_id,
                "token": token,
                "loginPhoneBrand": "Apple",
            },
        )
        self.access_token = data["accessToken"]
        self.refresh_token = data["refreshToken"]
        return data, code, msg

    async def auth_by_refresh_token(self):
        """Refresh new-API access token.

        Currently delegates to a full re-auth via main_token at the
        Controller level (Controller.update catches ZeekrAuthError and
        calls auth_all_api once). If a real refresh endpoint is
        discovered, implement it here without changing the call site.
        """

    async def get_vehicles(self, token: str):
        """Get all vehicle list."""
        return await self._fetch(
            method="get",
            url="/ms-app-bff/api/v3.0/veh/vehicle-list",
            params={"needSharedCar": "true"},
            headers={
                "Authorization": token,
            },
        )

    async def get_vehicle_data(self, vin: str):
        """Get new model vehicle data."""
        return await self._fetch(
            method="get",
            url="/ms-vehicle-status/api/v1.0/vehicle/status/latest",
            params={"latest": "false", "target": "new"},
            headers={
                "X-VIN": vin,
                "X-APP-ID": "ZEEKRCNCH001M0001",
            },
        )
