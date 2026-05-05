"""Coordinator."""

import logging
from datetime import timedelta

from homeassistant.core import callback
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .const import DEFAULT_SCAN_INTERVAL, DOMAIN
from .zeekr_api.controller import Controller

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
        """Fetch data from API endpoint."""
        _LOGGER.debug("Coordinator update for vin: %s", self.vin)
        return await self.controller.update(self.vin)
