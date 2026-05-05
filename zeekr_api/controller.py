"""Controller for the Zeekr API."""

import asyncio
import logging

from aiohttp import ClientSession

from .car import ZeekrCar
from .client_main import ClientMain
from .client_new import ClientNew
from .client_old import ClientOld
from .exceptions import ZeekrAuthError

_LOGGER = logging.getLogger(__name__)


class Controller:
    """Controller for the Zeekr API."""

    def __init__(
        self,
        session: ClientSession,
        device_id: str,
        token: str = "",
        phone_number: str = "",
    ) -> None:
        """Initialize the controller."""
        self.session = session
        self.device_id = device_id
        self.main_token = token
        self.phone_number = phone_number

        self.__client_main = ClientMain(session, device_id)
        self.__client_old = ClientOld(session, device_id)
        self.__client_new = ClientNew(session, device_id)
        self.__client_main.jwt_token = token
        self._vehicle_data: dict[str, dict] = {}
        self.all_vehicles = []
        self.old_vehicles = []
        self.cars: dict[str, ZeekrCar] = {}
        self._auth_lock = asyncio.Lock()

    async def login_by_main_token(self, token):
        """Login by main token."""
        self.__client_main.jwt_token = token
        data, _, _ = await self.__client_main.get_user_info()
        self.phone_number = data.get("userInfoDTO", {}).get("mobile", "")
        self.main_token = token

    async def send_SMS_code(self, phone_number):
        """Send SMS code."""
        self.phone_number = phone_number
        await self.__client_main.send_SMS_code(phone_number)

    async def login_by_SMS_code(self, sms_code):
        """Login by SMS code."""
        data, _, _ = await self.__client_main.login_by_SMS_code(
            self.phone_number, sms_code
        )
        self.main_token = data["jwtToken"]
        self.__client_main.jwt_token = self.main_token

    async def _auth_all_api_locked(self):
        """Auth all API (must be called while holding _auth_lock)."""
        data, _, _ = await self.__client_main.get_auth_code()
        auth_code = data["YIKAT_NEW"]
        await self.__client_old.auth_by_auth_code(auth_code)
        await self.__client_new.auth_by_main_token(self.main_token)

    async def auth_all_api(self):
        """Auth all API (serialized to avoid token rotation race)."""
        async with self._auth_lock:
            await self._auth_all_api_locked()

    async def get_all_vehicles(self):
        """Get all vehicles."""
        data, _, _ = await self.__client_new.get_vehicles(self.main_token)
        self.all_vehicles = data or []
        return self.all_vehicles

    async def get_old_vehicles(self):
        """Get old vehicles."""
        data, _, _ = await self.__client_old.get_vehicles()
        self.old_vehicles = (data or {}).get("list") or []
        return self.old_vehicles

    async def get_vehicles(self):
        """Get vehicles."""
        await asyncio.gather(self.get_all_vehicles(), self.get_old_vehicles())

    async def get_vehicle_data(self, vin: str):
        """Get vehicle data."""
        is_old_vehicle = vin in [v.get("vin") for v in self.old_vehicles]
        if is_old_vehicle:
            data, _, _ = await self.__client_old.get_vehicle_data(vin)
            vehicle_data = (data or {}).get("vehicleStatus", {})
        else:
            vehicle_data, _, _ = await self.__client_new.get_vehicle_data(vin)
        return vehicle_data

    async def update(self, vin: str):
        """Update vehicle data with one silent re-auth retry on token expiry.

        If access_token has expired (ZeekrAuthError from the per-VIN
        fetch), try to refresh subtokens once via _auth_all_api_locked
        (uses main_token). If that also fails, the error bubbles up to
        HA's coordinator which surfaces it as ConfigEntryAuthFailed via
        async_setup_entry on next reload, triggering reauth flow.
        """
        async with self._auth_lock:
            try:
                vehicle_data = await self.get_vehicle_data(vin)
            except ZeekrAuthError:
                _LOGGER.info(
                    "Access token expired for %s, attempting silent re-auth", vin
                )
                await self._auth_all_api_locked()
                vehicle_data = await self.get_vehicle_data(vin)
            self._vehicle_data.setdefault(vin, {}).update(vehicle_data)
            return self._vehicle_data[vin]

    async def generate_car_objects(
        self,
        filtered_vins: list[str] | None = None,
    ) -> dict[str, ZeekrCar]:
        """Generate car instances."""
        for car in self.all_vehicles:
            vin = car.get("vin")
            if not vin:
                continue
            if filtered_vins and vin not in filtered_vins:
                _LOGGER.debug("Skipping car with VIN: %s", vin)
                continue

            self._vehicle_data[vin] = {}
            self._vehicle_data[vin] = await self.get_vehicle_data(vin)
            is_old_vehicle = any(item["vin"] == vin for item in self.old_vehicles)
            self.cars[vin] = ZeekrCar(
                car, self, self._vehicle_data[vin], is_old_car=is_old_vehicle
            )

        return self.cars
