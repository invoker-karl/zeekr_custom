"""Config flow for Zeekr integration."""

from __future__ import annotations

import logging
import time
import uuid
from collections.abc import Mapping
from typing import Any

import voluptuous as vol
from homeassistant.config_entries import ConfigEntry, ConfigFlow, OptionsFlow
from homeassistant.const import CONF_ACCESS_TOKEN, CONF_CODE, CONF_SCAN_INTERVAL
from homeassistant.core import callback
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.aiohttp_client import async_create_clientsession

from .const import (
    CONF_AUTH_TYPE,
    CONF_DEVICE_ID,
    CONF_MOBILE,
    CONF_VEHICLE,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    MIN_SCAN_INTERVAL,
)
from .zeekr_api.controller import Controller
from .zeekr_api.exceptions import ZeekrAPIError

_LOGGER = logging.getLogger(__name__)

AUTH_MODE = {"mobile": "使用手机号验证码验证", "token": "使用token验证"}


class ZeekrConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Zeekr."""

    def __init__(self) -> None:
        """Initialize the zeekr config flow."""
        self.reauth = False
        self.controller: Controller | None = None
        self.mobile = None
        self._reauth_entry_id: str | None = None

    async def async_step_user(
        self,
        user_input: dict[str, Any] | None = None,
    ):
        """Handle the start of the config flow."""
        data_schema = vol.Schema(
            {
                vol.Required(CONF_AUTH_TYPE, default="mobile"): vol.In(AUTH_MODE),
            }
        )
        session = async_create_clientsession(self.hass)
        device_id = str(uuid.uuid4()).upper()
        self.controller = Controller(session, device_id)
        if user_input is None:
            return self.async_show_form(
                step_id="user",
                data_schema=data_schema,
            )
        if user_input[CONF_AUTH_TYPE] == "mobile":
            return await self.async_step_mobile()
        return await self.async_step_token()

    async def async_step_mobile(
        self,
        user_input: dict[str, Any] | None = None,
    ):
        """Handle the mobile step of the config flow."""
        data_schema = vol.Schema(
            {
                vol.Required(CONF_MOBILE, default=self.mobile): str,
            }
        )
        errors = {}

        if user_input is not None:
            self.mobile = user_input[CONF_MOBILE]
            existing_entry = self._async_entry_for_mobile(user_input[CONF_MOBILE])
            if existing_entry and not self.reauth:
                return self.async_abort(reason="already_configured")

            if self.controller is None:
                return self.async_abort(reason="no_controller")

            # Rate limit: 60 seconds between SMS sends to the same mobile
            throttle = self.hass.data.setdefault(f"{DOMAIN}_sms_throttle", {})
            last_sent = throttle.get(user_input[CONF_MOBILE], 0)
            now = time.time()
            if now - last_sent < 60:
                errors["base"] = "sms_too_soon"
            else:
                try:
                    await self.controller.send_SMS_code(user_input[CONF_MOBILE])
                    throttle[user_input[CONF_MOBILE]] = now
                except ZeekrAPIError as err:
                    errors["base"] = str(err)

                if not errors:
                    return await self.async_step_code()

        return self.async_show_form(
            step_id="mobile",
            data_schema=data_schema,
            errors=errors,
        )

    async def async_step_code(
        self,
        user_input: dict[str, Any] | None = None,
    ):
        """Handle the SMS code step of the config flow."""
        data_schema = vol.Schema(
            {
                vol.Required(CONF_CODE): str,
            }
        )
        errors = {}

        if user_input is not None:
            existing_entry = self._async_entry_for_mobile(self.mobile)

            if self.controller is None:
                return self.async_abort(reason="no_controller")
            try:
                await self.controller.login_by_SMS_code(user_input[CONF_CODE])
            except ZeekrAPIError as err:
                errors["base"] = str(err)

            if not errors:
                if existing_entry:
                    self._async_update_auth_entry(existing_entry)
                    await self.hass.config_entries.async_reload(existing_entry.entry_id)
                    return self.async_abort(reason="reauth_successful")

                return await self.async_step_choose_vehicle()

        return self.async_show_form(
            step_id="code",
            data_schema=data_schema,
            errors=errors,
        )

    async def async_step_token(
        self,
        user_input: dict[str, Any] | None = None,
    ):
        """Handle the JWT step of the config flow."""
        data_schema = vol.Schema(
            {
                vol.Required(CONF_ACCESS_TOKEN): str,
            }
        )
        errors = {}
        if user_input is not None:
            token = user_input[CONF_ACCESS_TOKEN]

            if self.controller is None:
                return self.async_abort(reason="no_controller")
            try:
                await self.controller.login_by_main_token(token)
                self.mobile = self.controller.phone_number
            except ZeekrAPIError as err:
                errors["base"] = str(err)

            if not errors:
                existing_entry = self._async_entry_for_mobile(self.mobile)
                if existing_entry and not self.reauth:
                    return self.async_abort(reason="already_configured")

                if existing_entry:
                    self._async_update_auth_entry(existing_entry)
                    await self.hass.config_entries.async_reload(existing_entry.entry_id)
                    return self.async_abort(reason="reauth_successful")

                return await self.async_step_choose_vehicle()

        return self.async_show_form(
            step_id="token", data_schema=data_schema, errors=errors
        )

    async def async_step_choose_vehicle(
        self,
        user_input: dict[str, Any] | None = None,
    ):
        """Handle the select vehicle step of the config flow."""
        if self.controller is None:
            return self.async_abort(reason="no_controller")
        all_vehicles = await self.controller.get_all_vehicles()
        data_schema = vol.Schema(
            {
                vol.Required(CONF_VEHICLE, default=[]): cv.multi_select(
                    {
                        v.get("vin", ""): "车架号："
                        + v.get("vin", "")
                        + " 车牌号："
                        + v.get("plateNo", "")
                        for v in all_vehicles
                        if v.get("vin")
                    }
                ),
            }
        )
        if user_input is not None and self.mobile:
            return self.async_create_entry(
                title=self.mobile,
                data={
                    CONF_MOBILE: self.mobile,
                    CONF_ACCESS_TOKEN: self.controller.main_token,
                    CONF_VEHICLE: user_input[CONF_VEHICLE],
                    CONF_DEVICE_ID: self.controller.device_id,
                },
            )

        return self.async_show_form(
            step_id="choose_vehicle",
            data_schema=data_schema,
        )

    async def async_step_reauth(
        self, entry_data: Mapping[str, Any]
    ) -> Any:
        """Handle initiation of re-authentication.

        Modern HA (2024+) signature. Currently the user re-runs the auth
        flow from scratch (a fresh device_id is generated). Reusing the
        original device_id is a future optimization (see Phase 6 / spec §I3).
        """
        self.mobile = entry_data.get(CONF_MOBILE)
        self.reauth = True
        # Bind to the original entry by id so reauth cannot accidentally
        # update or duplicate a different entry that happens to share the
        # same mobile number.
        self._reauth_entry_id = self.context.get("entry_id")
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> Any:
        """Confirm re-authentication with the user before re-running auth flow."""
        if user_input is None:
            return self.async_show_form(
                step_id="reauth_confirm",
                description_placeholders={"mobile": self.mobile or "—"},
            )
        # User confirmed. Route to original auth_type they used (mobile
        # or token); default to mobile (most common).
        return await self.async_step_user()

    @callback
    def _async_entry_for_mobile(self, mobile):
        """Find an existing entry for a mobile.

        During reauth, prefer the entry_id captured in async_step_reauth so
        we never accidentally redirect reauth to a different entry that
        happens to share the same mobile.
        """
        if self.reauth and self._reauth_entry_id:
            entry = self.hass.config_entries.async_get_entry(self._reauth_entry_id)
            if entry is not None:
                return entry
        if not mobile:
            return None
        for entry in self._async_current_entries():
            if entry.data.get(CONF_MOBILE) == mobile:
                return entry
        return None

    @callback
    def _async_update_auth_entry(self, entry: ConfigEntry) -> None:
        """Update stored auth data without dropping existing entry metadata."""
        if self.controller is None:
            return
        self.hass.config_entries.async_update_entry(
            entry,
            data={
                **entry.data,
                CONF_MOBILE: self.mobile or entry.data.get(CONF_MOBILE, entry.title),
                CONF_ACCESS_TOKEN: self.controller.main_token,
                CONF_DEVICE_ID: self.controller.device_id,
            },
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlowHandler:
        """Get the options flow for this handler."""
        return OptionsFlowHandler()


class OptionsFlowHandler(OptionsFlow):
    """Options flow for Zeekr."""

    async def async_step_init(self, user_input: dict[str, Any] | None = None):
        """Manage the options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        # DEVICE_ID = str(uuid.uuid4()).upper()
        config = self.config_entry.data
        option = self.config_entry.options
        session = async_create_clientsession(self.hass)
        controller = Controller(
            session,
            config[CONF_DEVICE_ID],
            config[CONF_ACCESS_TOKEN],
            config.get(CONF_MOBILE, self.config_entry.title),
        )
        errors = {}
        data_schema = vol.Schema(
            {
                vol.Optional(
                    CONF_SCAN_INTERVAL,
                    default=self.config_entry.options.get(
                        CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL
                    ),
                ): vol.All(cv.positive_int, vol.Clamp(min=MIN_SCAN_INTERVAL)),
            }
        )
        selected_vehicle = option.get(CONF_VEHICLE, config.get(CONF_VEHICLE, []))
        all_vehicles = []
        try:
            await controller.auth_all_api()
            all_vehicles = await controller.get_all_vehicles()
        except ZeekrAPIError as err:
            errors["base"] = str(err)

        if not errors:
            data_schema = data_schema.extend(
                {
                    vol.Required(
                        CONF_VEHICLE, default=selected_vehicle
                    ): cv.multi_select(
                        {
                            v.get("vin", ""): "车架号："
                            + v.get("vin", "")
                            + " 车牌号："
                            + v.get("plateNo", "")
                            for v in all_vehicles
                            if v.get("vin")
                        }
                    ),
                }
            )

        return self.async_show_form(
            step_id="init", data_schema=data_schema, errors=errors
        )
