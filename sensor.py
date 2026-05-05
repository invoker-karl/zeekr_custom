"""Minimal sensor platform for zeekr integration."""

from __future__ import annotations

from typing import TYPE_CHECKING

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.const import UnitOfPressure, UnitOfTemperature
from homeassistant.const import UnitOfLength, UnitOfTime
from homeassistant.helpers.icon import icon_for_battery_level

from .base import ZeekrCarEntity
from .const import DOMAIN, PERCENTAGE

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddEntitiesCallback

    from .coordinator import ZeekrDataUpdateCoordinator
    from .zeekr_api.car import ZeekrCar

TPMS_SENSORS = {
    "TPMS front left": "tpms_pressure_fl",
    "TPMS front right": "tpms_pressure_fr",
    "TPMS rear left": "tpms_pressure_rl",
    "TPMS rear right": "tpms_pressure_rr",
}

TYRE_TEMP_SENSORS = {
    "tyre temperature front left": "tyre_temp_fl",
    "tyre temperature front right": "tyre_temp_fr",
    "tyre temperature rear left": "tyre_temp_rl",
    "tyre temperature rear right": "tyre_temp_rr",
}


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Add sensors for Zeekr cars."""
    entry_data = hass.data[DOMAIN][config_entry.entry_id]
    coordinators = entry_data["coordinators"]
    cars = entry_data["cars"]
    entities = []
    for vin, car in cars.items():
        coordinator = coordinators[vin]
        entities.append(ZeekrCarModel(car, coordinator))
        entities.append(ZeekrCarDisplayState(car, coordinator))
        entities.append(ZeekrCarTemp(car, coordinator))
        entities.append(ZeekrCarTemp(car, coordinator, inside=True))
        for tpms_sensor in TPMS_SENSORS:
            entities.append(ZeekrCarTpmsPressureSensor(car, coordinator, tpms_sensor))  # noqa: PERF401
        for tyre_temp_sensor in TYRE_TEMP_SENSORS:
            entities.append(ZeekrCarTyreTemp(car, coordinator, tyre_temp_sensor))  # noqa: PERF401
        entities.append(ZeekrCarBattery(car, coordinator))
        entities.append(ZeekrCarChargingStatus(car, coordinator))
        entities.append(ZeekrCarSpeed(car, coordinator))
        entities.append(ZeekrCarDirection(car, coordinator))
        entities.append(ZeekrCarAltitude(car, coordinator))
        entities.append(ZeekrCarDistanceToEmptyBattery(car, coordinator))
        entities.append(ZeekrCarTimeToFullyCharged(car, coordinator))
        entities.append(ZeekrCarChargeVoltage(car, coordinator))
        entities.append(ZeekrCarChargeCurrent(car, coordinator))
        entities.append(ZeekrCarAveragePowerConsumption(car, coordinator))
        entities.append(ZeekrCarOdometer(car, coordinator))
        entities.append(ZeekrCarDaysToService(car, coordinator))
        entities.append(ZeekrCarDistanceToService(car, coordinator))
        entities.append(ZeekrCarLowVoltageBatteryVoltage(car, coordinator))
        entities.append(ZeekrCarAverageSpeed(car, coordinator))
        entities.append(ZeekrCarTripMeter2(car, coordinator))
        entities.append(ZeekrCarSunroofPosition(car, coordinator))
        entities.append(ZeekrCarRearSunshadePosition(car, coordinator))
        entities.append(ZeekrCarDriverSeatHeating(car, coordinator))
        entities.append(ZeekrCarPassengerSeatHeating(car, coordinator))
        entities.append(ZeekrCarDriverSeatVentilation(car, coordinator))
        entities.append(ZeekrCarPassengerSeatVentilation(car, coordinator))
    async_add_entities(entities, update_before_add=True)


class ZeekrCarTemp(ZeekrCarEntity, SensorEntity):
    """Representation of the Zeekr car interior/exterior temperature sensor."""

    _attr_device_class = SensorDeviceClass.TEMPERATURE
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
    _attr_icon = "mdi:thermometer"

    def __init__(
        self,
        car: ZeekrCar,
        coordinator: ZeekrDataUpdateCoordinator,
        *,
        inside=False,
    ) -> None:
        """Initialize temp entity."""
        self.inside = inside
        self.type = "temperature_inside" if inside else "temperature_outside"
        super().__init__(car, coordinator)

    @property
    def translation_key(self):
        """Return the name of the sensor."""
        if self.inside:
            return "temperature_inside"
        return "temperature_outside"

    @property
    def native_value(self):
        """Return car temperature."""
        temp = self._car.interior_temp if self.inside else self._car.exterior_temp
        if temp is not None:
            return temp
        return None


class ZeekrCarModel(ZeekrCarEntity, SensorEntity):
    """Representation of the Zeekr car model sensor."""

    type = "model"
    _attr_translation_key = "model"
    _attr_icon = "mdi:car-info"

    @property
    def native_value(self):
        """Return car model name."""
        return self._car.model_name

    @property
    def extra_state_attributes(self):
        """Return model metadata."""
        return {
            "model_code": self._car.model_code,
            "os_version": self._car.os_version,
        }


class ZeekrCarDisplayState(ZeekrCarEntity, SensorEntity):
    """Representation of the Zeekr car dashboard display state sensor."""

    type = "display_state"
    _attr_translation_key = "display_state"
    _attr_icon = "mdi:car-cog"

    @property
    def native_value(self):
        """Return high-level dashboard display state."""
        return self._car.display_state

    @property
    def extra_state_attributes(self):
        """Return dashboard-friendly status attributes."""
        return self._car.display_state_attributes


class ZeekrCarTyreTemp(ZeekrCarEntity, SensorEntity):
    """Representation of the Zeekr car tyre temperature sensor."""

    _attr_device_class = SensorDeviceClass.TEMPERATURE
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
    _attr_icon = "mdi:thermometer"

    def __init__(
        self,
        car: ZeekrCar,
        coordinator: ZeekrDataUpdateCoordinator,
        tyre_temp_sensor: str,
    ) -> None:
        """Initialize tyre temp entity."""
        self._tyre_temp_sensor = tyre_temp_sensor
        self.type = tyre_temp_sensor
        super().__init__(car, coordinator)

    @property
    def translation_key(self):
        """Return the name of the sensor."""
        return TYRE_TEMP_SENSORS.get(self._tyre_temp_sensor, "")

    @property
    def native_value(self) -> float | None:
        """Return tyre temperature."""
        value = getattr(self._car, self.translation_key)
        if value is not None:
            return value
        return None


class ZeekrCarTpmsPressureSensor(ZeekrCarEntity, SensorEntity):
    """Representation of the Zeekr car TPMS Pressure sensor."""

    _attr_device_class = SensorDeviceClass.PRESSURE
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = UnitOfPressure.KPA
    _attr_suggested_unit_of_measurement = UnitOfPressure.KPA
    _attr_icon = "mdi:gauge-full"

    def __init__(
        self,
        car: ZeekrCar,
        coordinator: ZeekrDataUpdateCoordinator,
        tpms_sensor: str,
    ) -> None:
        """Initialize TPMS Pressure sensor."""
        self._tpms_sensor = tpms_sensor
        self.type = tpms_sensor
        super().__init__(car, coordinator)

    @property
    def translation_key(self):
        """Return the name of the sensor."""
        return TPMS_SENSORS.get(self._tpms_sensor, "")

    @property
    def native_value(self) -> float | None:
        """Return TPMS Pressure."""
        value = getattr(self._car, self.translation_key)
        if value is not None:
            return value
        return None


class ZeekrCarBattery(ZeekrCarEntity, SensorEntity):
    """Representation of the Zeekr car battery sensor."""

    type = "battery"
    _attr_translation_key = "battery_level"
    _attr_device_class = SensorDeviceClass.BATTERY
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_icon = "mdi:battery"

    @staticmethod
    def has_battery() -> bool:
        """Return whether the device has a battery."""
        return True

    @property
    def native_value(self):
        """Return battery level."""
        return self._car.charge_level

    @property
    def icon(self):
        """Return icon for the battery."""
        return icon_for_battery_level(
            battery_level=self.native_value, charging=self._car.is_charging
        )


class ZeekrCarChargingStatus(ZeekrCarEntity, SensorEntity):
    """Representation of the Zeekr car charging status sensor."""

    type = "charging_status"
    _attr_translation_key = "charging_status"
    _attr_icon = "mdi:ev-station"

    @property
    def native_value(self):
        """Return charging status."""
        return self._car.charging_status


class ZeekrCarSpeed(ZeekrCarEntity, SensorEntity):
    """Representation of the Zeekr car speed sensor."""

    type = "speed"
    _attr_translation_key = "speed"
    _attr_device_class = SensorDeviceClass.SPEED
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = "km/h"
    _attr_icon = "mdi:speedometer"

    @property
    def native_value(self):
        """Return speed."""
        return self._car.speed


class ZeekrCarDirection(ZeekrCarEntity, SensorEntity):
    """Representation of the Zeekr car direction sensor."""

    type = "direction"
    _attr_translation_key = "direction"
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = "deg"
    _attr_icon = "mdi:compass"

    @property
    def native_value(self):
        """Return direction."""
        return self._car.direction


class ZeekrCarAltitude(ZeekrCarEntity, SensorEntity):
    """Representation of the Zeekr car altitude sensor."""

    type = "altitude"
    _attr_translation_key = "altitude"
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = "m"
    _attr_icon = "mdi:elevation-rise"

    @property
    def native_value(self):
        """Return altitude."""
        return self._car.altitude


class ZeekrCarDistanceToEmptyBattery(ZeekrCarEntity, SensorEntity):
    """Representation of the Zeekr car battery range sensor."""

    type = "distance_to_empty_battery"
    _attr_translation_key = "distance_to_empty_battery"
    _attr_device_class = SensorDeviceClass.DISTANCE
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = UnitOfLength.KILOMETERS
    _attr_icon = "mdi:map-marker-distance"

    @property
    def native_value(self):
        """Return battery-only distance to empty."""
        return self._car.distance_to_empty_battery


class ZeekrCarTimeToFullyCharged(ZeekrCarEntity, SensorEntity):
    """Representation of the Zeekr car time to full charge sensor."""

    type = "time_to_fully_charged"
    _attr_translation_key = "time_to_fully_charged"
    _attr_device_class = SensorDeviceClass.DURATION
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = UnitOfTime.MINUTES
    _attr_icon = "mdi:timer-outline"

    @property
    def native_value(self):
        """Return time to fully charged."""
        return self._car.time_to_fully_charged


class ZeekrCarChargeVoltage(ZeekrCarEntity, SensorEntity):
    """Representation of the Zeekr car charge voltage sensor."""

    type = "charge_voltage"
    _attr_translation_key = "charge_voltage"
    _attr_device_class = SensorDeviceClass.VOLTAGE
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = "V"
    _attr_icon = "mdi:sine-wave"

    @property
    def native_value(self):
        """Return charge voltage."""
        return self._car.charge_voltage


class ZeekrCarChargeCurrent(ZeekrCarEntity, SensorEntity):
    """Representation of the Zeekr car charge current sensor."""

    type = "charge_current"
    _attr_translation_key = "charge_current"
    _attr_device_class = SensorDeviceClass.CURRENT
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = "A"
    _attr_icon = "mdi:current-ac"

    @property
    def native_value(self):
        """Return charge current."""
        return self._car.charge_current


class ZeekrCarAveragePowerConsumption(ZeekrCarEntity, SensorEntity):
    """Representation of the Zeekr car average power consumption sensor."""

    type = "average_power_consumption"
    _attr_translation_key = "average_power_consumption"
    _attr_device_class = SensorDeviceClass.ENERGY_DISTANCE
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = "kWh/100km"
    _attr_icon = "mdi:lightning-bolt"

    @property
    def native_value(self):
        """Return average power consumption."""
        return self._car.average_power_consumption


class ZeekrCarOdometer(ZeekrCarEntity, SensorEntity):
    """Representation of the Zeekr car odometer sensor."""

    type = "odometer"
    _attr_translation_key = "odometer"
    _attr_device_class = SensorDeviceClass.DISTANCE
    _attr_state_class = SensorStateClass.TOTAL_INCREASING
    _attr_native_unit_of_measurement = UnitOfLength.KILOMETERS
    _attr_icon = "mdi:counter"

    @property
    def native_value(self):
        """Return odometer."""
        return self._car.odometer


class ZeekrCarDaysToService(ZeekrCarEntity, SensorEntity):
    """Representation of the Zeekr car days to service sensor."""

    type = "days_to_service"
    _attr_translation_key = "days_to_service"
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = "d"
    _attr_icon = "mdi:calendar-clock"

    @property
    def native_value(self):
        """Return days until service."""
        return self._car.days_to_service


class ZeekrCarDistanceToService(ZeekrCarEntity, SensorEntity):
    """Representation of the Zeekr car distance to service sensor."""

    type = "distance_to_service"
    _attr_translation_key = "distance_to_service"
    _attr_device_class = SensorDeviceClass.DISTANCE
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = UnitOfLength.KILOMETERS
    _attr_icon = "mdi:wrench-clock"

    @property
    def native_value(self):
        """Return distance until service."""
        return self._car.distance_to_service


class ZeekrCarLowVoltageBatteryVoltage(ZeekrCarEntity, SensorEntity):
    """Representation of the Zeekr car low-voltage battery sensor."""

    type = "low_voltage_battery_voltage"
    _attr_translation_key = "low_voltage_battery_voltage"
    _attr_device_class = SensorDeviceClass.VOLTAGE
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = "V"
    _attr_icon = "mdi:car-battery"

    @property
    def native_value(self):
        """Return low-voltage battery voltage."""
        return self._car.low_voltage_battery_voltage


class ZeekrCarAverageSpeed(ZeekrCarEntity, SensorEntity):
    """Representation of the Zeekr car average speed sensor."""

    type = "average_speed"
    _attr_translation_key = "average_speed"
    _attr_device_class = SensorDeviceClass.SPEED
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = "km/h"
    _attr_icon = "mdi:speedometer-medium"

    @property
    def native_value(self):
        """Return average speed."""
        return self._car.average_speed


class ZeekrCarTripMeter2(ZeekrCarEntity, SensorEntity):
    """Representation of the Zeekr car trip meter sensor."""

    type = "trip_meter_2"
    _attr_translation_key = "trip_meter_2"
    _attr_device_class = SensorDeviceClass.DISTANCE
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = UnitOfLength.KILOMETERS
    _attr_icon = "mdi:map-marker-path"

    @property
    def native_value(self):
        """Return trip meter 2."""
        return self._car.trip_meter_2


class ZeekrCarSunroofPosition(ZeekrCarEntity, SensorEntity):
    """Representation of the Zeekr car sunroof position sensor."""

    type = "sunroof_position"
    _attr_translation_key = "sunroof_position"
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_icon = "mdi:window-closed-variant"

    @property
    def native_value(self):
        """Return sunroof position."""
        return self._car.sunroof_position


class ZeekrCarRearSunshadePosition(ZeekrCarEntity, SensorEntity):
    """Representation of the Zeekr car rear sunshade position sensor."""

    type = "rear_sunshade_position"
    _attr_translation_key = "rear_sunshade_position"
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_icon = "mdi:roller-shade"

    @property
    def native_value(self):
        """Return rear sunshade position."""
        return self._car.rear_sunshade_position


class ZeekrCarDriverSeatHeating(ZeekrCarEntity, SensorEntity):
    """Representation of the Zeekr car driver seat heating sensor."""

    type = "driver_seat_heating"
    _attr_translation_key = "driver_seat_heating"
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_icon = "mdi:car-seat-heater"

    @property
    def native_value(self):
        """Return driver seat heating level."""
        return self._car.driver_seat_heating


class ZeekrCarPassengerSeatHeating(ZeekrCarEntity, SensorEntity):
    """Representation of the Zeekr car passenger seat heating sensor."""

    type = "passenger_seat_heating"
    _attr_translation_key = "passenger_seat_heating"
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_icon = "mdi:car-seat-heater"

    @property
    def native_value(self):
        """Return passenger seat heating level."""
        return self._car.passenger_seat_heating


class ZeekrCarDriverSeatVentilation(ZeekrCarEntity, SensorEntity):
    """Representation of the Zeekr car driver seat ventilation sensor."""

    type = "driver_seat_ventilation"
    _attr_translation_key = "driver_seat_ventilation"
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_icon = "mdi:car-seat-cooler"

    @property
    def native_value(self):
        """Return driver seat ventilation level."""
        return self._car.driver_seat_ventilation


class ZeekrCarPassengerSeatVentilation(ZeekrCarEntity, SensorEntity):
    """Representation of the Zeekr car passenger seat ventilation sensor."""

    type = "passenger_seat_ventilation"
    _attr_translation_key = "passenger_seat_ventilation"
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_icon = "mdi:car-seat-cooler"

    @property
    def native_value(self):
        """Return passenger seat ventilation level."""
        return self._car.passenger_seat_ventilation
