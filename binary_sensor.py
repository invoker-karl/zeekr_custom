"""Support for Tesla binary sensors."""

import logging

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.core import HomeAssistant

from .base import ZeekrCarEntity
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

DOOR_SENSORS = {
    "door driver front": ("door_driver_front", "door_df", "door_pos_df"),
    "door driver rear": ("door_driver_rear", "door_dr", "door_pos_dr"),
    "door passenger front": ("door_passenger_front", "door_pf", "door_pos_pf"),
    "door passenger rear": ("door_passenger_rear", "door_pr", "door_pos_pr"),
}

WINDOW_SENSORS = {
    "window driver front": ("window_driver_front", "window_fd", "window_pos_fd"),
    "window driver rear": ("window_driver_rear", "window_rd", "window_pos_rd"),
    "window passenger front": ("window_passenger_front", "window_fp", "window_pos_fp"),
    "window passenger rear": ("window_passenger_rear", "window_rp", "window_pos_rp"),
}


def _open_position(*, position: int | None):
    """Return string of 'Open' or 'Closed' when passed a window integer state."""
    if position is None:
        return None
    return position


def _open_or_closed(*, status: bool | None):
    if status is None:
        return None
    return "Open" if status else "Closed"


async def async_setup_entry(hass: HomeAssistant, config_entry, async_add_entities):
    """Set up the Tesla selects by config_entry."""
    entry_data = hass.data[DOMAIN][config_entry.entry_id]
    coordinators = entry_data["coordinators"]
    cars = entry_data["cars"]
    entities = []

    for vin, car in cars.items():
        coordinator = coordinators[vin]
        entities.append(ZeekrCarDoors(car, coordinator))
        for door_sensor in DOOR_SENSORS:
            entities.append(ZeekrCarDoor(car, coordinator, door_sensor))
        entities.append(ZeekrCarWindows(car, coordinator))
        for window_sensor in WINDOW_SENSORS:
            entities.append(ZeekrCarWindow(car, coordinator, window_sensor))
        entities.append(ZeekrCarEngine(car, coordinator))
        entities.append(ZeekrCarUnlocked(car, coordinator))
        entities.append(ZeekrCarPluggedIn(car, coordinator))
        entities.append(ZeekrCarTrunk(car, coordinator))
        entities.append(ZeekrCarEngineHood(car, coordinator))
        entities.append(ZeekrCarSunroof(car, coordinator))
        entities.append(ZeekrCarRearSunshade(car, coordinator))
        entities.append(ZeekrCarDefrost(car, coordinator))
        entities.append(ZeekrCarSteeringWheelHeating(car, coordinator))

    async_add_entities(entities, update_before_add=True)


class ZeekrCarDoors(ZeekrCarEntity, BinarySensorEntity):
    """Representation of a Zeekr car door sensor."""

    type = "doors"
    _attr_translation_key = "car_door"
    _attr_device_class = BinarySensorDeviceClass.DOOR
    _attr_icon = "mdi:car-door"

    @property
    def is_on(self) -> bool:
        """Return True if a car door is open."""
        car = self._car
        return car.door_df or car.door_dr or car.door_pf or car.door_pr

    @property
    def extra_state_attributes(self):
        """Return device state attributes."""
        car = self._car
        return {
            "Driver Front": _open_or_closed(status=car.door_df),
            "Driver Rear": _open_or_closed(status=car.door_dr),
            "Passenger Front": _open_or_closed(status=car.door_pf),
            "Passenger Rear": _open_or_closed(status=car.door_pr),
            "Driver Front Percent": _open_position(position=car.door_pos_df),
            "Driver Rear Percent": _open_position(position=car.door_pos_dr),
            "Passenger Front Percent": _open_position(position=car.door_pos_pf),
            "Passenger Rear Percent": _open_position(position=car.door_pos_pr),
        }


class ZeekrCarDoor(ZeekrCarEntity, BinarySensorEntity):
    """Representation of a single Zeekr car door sensor."""

    _attr_device_class = BinarySensorDeviceClass.DOOR
    _attr_icon = "mdi:car-door"

    def __init__(self, car, coordinator, door_sensor: str) -> None:
        """Initialize single door entity."""
        self._door_sensor = door_sensor
        self._translation_key, self._status_key, self._position_key = DOOR_SENSORS[
            door_sensor
        ]
        self.type = door_sensor
        super().__init__(car, coordinator)

    @property
    def translation_key(self):
        """Return the name of the sensor."""
        return self._translation_key

    @property
    def is_on(self):
        """Return True if this door is open."""
        return getattr(self._car, self._status_key)

    @property
    def extra_state_attributes(self):
        """Return door position attribute."""
        return {
            "position": getattr(self._car, self._position_key),
        }


class ZeekrCarWindows(ZeekrCarEntity, BinarySensorEntity):
    """Representation of a Zeekr window door sensor."""

    type = "windows"
    _attr_translation_key = "car_window"
    _attr_device_class = BinarySensorDeviceClass.WINDOW
    _attr_icon = "mdi:car-door"

    @property
    def is_on(self):
        """Return True if a car window is open."""
        car = self._car
        return car.window_fd or car.window_fp or car.window_rd or car.window_rp

    @property
    def extra_state_attributes(self):
        """Return device state attributes."""
        car = self._car
        return {
            "Driver Front": _open_or_closed(status=car.window_fd),
            "Driver Rear": _open_or_closed(status=car.window_rd),
            "Passenger Front": _open_or_closed(status=car.window_fp),
            "Passenger Rear": _open_or_closed(status=car.window_rp),
            "Driver Front Percent": _open_position(position=car.window_pos_fd),
            "Driver Rear Percent": _open_position(position=car.window_pos_rd),
            "Passenger Front Percent": _open_position(position=car.window_pos_fp),
            "Passenger Rear Percent": _open_position(position=car.window_pos_rp),
        }


class ZeekrCarWindow(ZeekrCarEntity, BinarySensorEntity):
    """Representation of a single Zeekr car window sensor."""

    _attr_device_class = BinarySensorDeviceClass.WINDOW
    _attr_icon = "mdi:car-door"

    def __init__(self, car, coordinator, window_sensor: str) -> None:
        """Initialize single window entity."""
        self._window_sensor = window_sensor
        self._translation_key, self._status_key, self._position_key = WINDOW_SENSORS[
            window_sensor
        ]
        self.type = window_sensor
        super().__init__(car, coordinator)

    @property
    def translation_key(self):
        """Return the name of the sensor."""
        return self._translation_key

    @property
    def is_on(self):
        """Return True if this window is open."""
        return getattr(self._car, self._status_key)

    @property
    def extra_state_attributes(self):
        """Return window position attribute."""
        return {
            "position": getattr(self._car, self._position_key),
        }


class ZeekrCarEngine(ZeekrCarEntity, BinarySensorEntity):
    """Representation of a Zeekr engine sensor."""

    type = "engine_running"
    _attr_translation_key = "engine_running"
    _attr_device_class = BinarySensorDeviceClass.RUNNING
    _attr_icon = "mdi:engine"

    @property
    def is_on(self):
        """Return True if a car window is open."""
        _LOGGER.debug("engine_status: %s", self._car.engine_status)
        return self._car.engine_status

    @property
    def icon(self):
        """Return icon for the engine."""
        return "mdi:engine" if self.is_on else "mdi:engine-off"


class ZeekrCarUnlocked(ZeekrCarEntity, BinarySensorEntity):
    """Representation of a Zeekr central lock sensor."""

    type = "unlocked"
    _attr_translation_key = "unlocked"
    _attr_device_class = BinarySensorDeviceClass.LOCK

    @property
    def is_on(self):
        """Return True if the car is unlocked."""
        return self._car.is_unlocked

    @property
    def icon(self):
        """Return icon for the lock."""
        return "mdi:lock-open-variant" if self.is_on else "mdi:lock"


class ZeekrCarPluggedIn(ZeekrCarEntity, BinarySensorEntity):
    """Representation of a Zeekr plugged-in sensor."""

    type = "plugged_in"
    _attr_translation_key = "plugged_in"
    _attr_device_class = BinarySensorDeviceClass.PLUG
    _attr_icon = "mdi:ev-plug-type2"

    @property
    def is_on(self):
        """Return True if charge cable is connected."""
        return self._car.is_plugged_in


class ZeekrCarTrunk(ZeekrCarEntity, BinarySensorEntity):
    """Representation of a Zeekr trunk sensor."""

    type = "trunk"
    _attr_translation_key = "trunk"
    _attr_device_class = BinarySensorDeviceClass.OPENING
    _attr_icon = "mdi:car-back"

    @property
    def is_on(self):
        """Return True if trunk is open."""
        return self._car.trunk_open


class ZeekrCarEngineHood(ZeekrCarEntity, BinarySensorEntity):
    """Representation of a Zeekr engine hood sensor."""

    type = "engine_hood"
    _attr_translation_key = "engine_hood"
    _attr_device_class = BinarySensorDeviceClass.OPENING
    _attr_icon = "mdi:car"

    @property
    def is_on(self):
        """Return True if engine hood is open."""
        return self._car.engine_hood_open


class ZeekrCarSunroof(ZeekrCarEntity, BinarySensorEntity):
    """Representation of a Zeekr sunroof sensor."""

    type = "sunroof"
    _attr_translation_key = "sunroof"
    _attr_device_class = BinarySensorDeviceClass.WINDOW
    _attr_icon = "mdi:window-closed-variant"

    @property
    def is_on(self):
        """Return True if sunroof is open."""
        return self._car.sunroof_open

    @property
    def icon(self):
        """Return icon for the sunroof."""
        return "mdi:window-open-variant" if self.is_on else "mdi:window-closed-variant"


class ZeekrCarDefrost(ZeekrCarEntity, BinarySensorEntity):
    """Representation of a Zeekr defrost sensor."""

    type = "defrost"
    _attr_translation_key = "defrost"
    _attr_icon = "mdi:car-defrost-front"

    @property
    def is_on(self):
        """Return True if defrost is on."""
        return self._car.defrost_on


class ZeekrCarRearSunshade(ZeekrCarEntity, BinarySensorEntity):
    """Representation of a Zeekr rear sunshade sensor."""

    type = "rear_sunshade"
    _attr_translation_key = "rear_sunshade"
    _attr_device_class = BinarySensorDeviceClass.OPENING
    _attr_icon = "mdi:roller-shade"

    @property
    def is_on(self):
        """Return True if rear sunshade is open."""
        return self._car.rear_sunshade_open


class ZeekrCarSteeringWheelHeating(ZeekrCarEntity, BinarySensorEntity):
    """Representation of a Zeekr steering wheel heating sensor."""

    type = "steering_wheel_heating"
    _attr_translation_key = "steering_wheel_heating"
    _attr_device_class = BinarySensorDeviceClass.HEAT
    _attr_icon = "mdi:steering"

    @property
    def is_on(self):
        """Return True if steering wheel heating is on."""
        return self._car.steering_wheel_heating_on
