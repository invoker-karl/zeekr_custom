"""Support for Zeekr covers."""

import logging

from homeassistant.components.cover import (
    CoverDeviceClass,
    CoverEntity,
    CoverEntityFeature,
)
from homeassistant.core import HomeAssistant

from .base import ZeekrCarEntity
from .const import DOMAIN
from .coordinator import ZeekrDataUpdateCoordinator
from .zeekr_api.car import ZeekrCar

_LOGGER = logging.getLogger(__name__)

WINDOW_COVERS = {
    "window driver front": "window_fd,window_pos_fd",
    "window passenger front": "window_fp,window_pos_fp",
    "window driver rear": "window_rd,window_pos_rd",
    "window passenger rear": "window_rp,window_pos_rp",
}


async def async_setup_entry(hass: HomeAssistant, config_entry, async_add_entities):
    """Set up the Zeekr locks by config_entry."""
    entry_data = hass.data[DOMAIN][config_entry.entry_id]
    coordinators = entry_data["coordinators"]
    cars = entry_data["cars"]
    entities = []

    for vin, car in cars.items():
        coordinator = coordinators[vin]
        for window_cover in WINDOW_COVERS:
            entities.append(ZeekrCarWindows(car, coordinator, window_cover))  # noqa: PERF401

    async_add_entities(entities, update_before_add=True)


class ZeekrCarWindows(ZeekrCarEntity, CoverEntity):
    """Representation of a Zeekr car window cover."""

    _attr_translation_key = "car_window"
    _attr_device_class = CoverDeviceClass.WINDOW
    _attr_icon = "mdi:car-door"
    _attr_supported_features = (
        CoverEntityFeature.OPEN
        | CoverEntityFeature.CLOSE
        | CoverEntityFeature.SET_POSITION
    )

    def __init__(
        self,
        car: ZeekrCar,
        coordinator: ZeekrDataUpdateCoordinator,
        window_cover: str,
    ) -> None:
        """Initialize window cover entity."""
        self._window_cover = window_cover
        self.type = window_cover
        self._status_key, self._pos_key = WINDOW_COVERS[window_cover].split(",")
        self._attr_translation_key = self._status_key
        super().__init__(car, coordinator)

    # async def async_close_cover(self, **kwargs):
    #     """Send close cover command."""
    #     _LOGGER.debug("Closing cover: %s", self.name)
    #     if self.is_closed is False:
    #         await self._car.close_windows()
    #         self.async_write_ha_state()

    # async def async_open_cover(self, **kwargs):
    #     """Send open cover command."""
    #     _LOGGER.debug("Opening cover: %s", self.name)
    #     if self.is_closed is True:
    #         await self._car.vent_windows()
    #         self.async_write_ha_state()

    @property
    def current_cover_position(self):
        """Return the current position of the cover."""
        return getattr(self._car, self._pos_key)

    @property
    def is_closed(self):
        """Return True if all windows are closed."""
        status = getattr(self._car, self._status_key)
        if status is not None:
            return not status
        return getattr(self._car, self._pos_key) == 0

    @property
    def extra_state_attributes(self):
        """Return device state attributes."""
        return {
            "Driver Front": self.is_closed,
        }
