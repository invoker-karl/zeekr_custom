"""Coordinator."""

import logging
from datetime import timedelta

from homeassistant.core import callback
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DEFAULT_SCAN_INTERVAL, DOMAIN
from .zeekr_api.controller import Controller
from .zeekr_api.exceptions import ZeekrAPIError, ZeekrAuthError

_LOGGER = logging.getLogger(__name__)


class ZeekrDataUpdateCoordinator(DataUpdateCoordinator):
    """Class to manage fetching Zeekr data."""

    def __init__(
        self,
        hass,
        config_entry,
        controller: Controller,
        vin: str,
        update_interval: int = DEFAULT_SCAN_INTERVAL,
    ) -> None:
        """Initialize global Zeekr data updater."""
        self.controller = controller
        self.config_entry = config_entry
        self.vin = vin
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=update_interval),
        )

    @callback
    def set_update_interval(self, update_interval):
        """Set update interval."""
        self.update_interval = timedelta(seconds=update_interval)

    async def _async_update_data(self):
        """Fetch data from API endpoint.

        Raises:
            ConfigEntryAuthFailed: when re-auth via the controller still fails,
                so HA shows the user a "Reconfigure" prompt instead of a
                generic update error.
            UpdateFailed: for transient/transport errors that may recover on
                the next poll.
        """
        _LOGGER.debug("Coordinator update for vin: %s", self.vin)
        try:
            return await self.controller.update(self.vin)
        except ZeekrAuthError as err:
            raise ConfigEntryAuthFailed(
                f"Zeekr auth failed for {self.vin}: {err}"
            ) from err
        except ZeekrAPIError as err:
            raise UpdateFailed(f"Zeekr API error for {self.vin}: {err}") from err
