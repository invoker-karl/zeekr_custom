"""Zeekr car class."""

"""Charging state of electric vehicle."""

from typing import Any

ChargingState = [
    "NOT_CHARGING",
    "DEFAULT",
    "CHARGING",
    "ERROR",
    "COMPLETE",
    "FULLY_CHARGED",
    "FINISHED_FULLY_CHARGED",
    "FINISHED_NOT_FULL",
    "INVALID",
    "PLUGGED_IN",
    "WAITING_FOR_CHARGING",
    "TARGET_REACHED",
    "UNKNOWN",
    "UNKNOWN",
    "UNKNOWN",
    "DC_CHARGING",
]

MODEL_NAMES = {
    "CX1E": "Zeekr 7X",
}


def _as_float(value: Any) -> float | None:
    """Return value converted to float, or None if it is not available."""
    if value in (None, ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _as_int(value: Any) -> int | None:
    """Return value converted to int, or None if it is not available."""
    if value in (None, ""):
        return None
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return None


def _round_float(value: Any, ndigits: int = 1) -> float | None:
    """Return value rounded as float, or None if it is not available."""
    parsed = _as_float(value)
    if parsed is None:
        return None
    return round(parsed, ndigits)


def _as_bool(value: Any) -> bool | None:
    """Return value converted to bool, or None if it is not available."""
    if isinstance(value, bool):
        return value
    if value in (None, ""):
        return None
    if isinstance(value, (int, float)):
        if value == 1:
            return True
        if value in (0, 2):
            return False
    if isinstance(value, str):
        normalized = value.lower()
        if normalized in {"1", "true", "on", "yes"}:
            return True
        if normalized in {"0", "2", "false", "off", "no"}:
            return False
    return None


class ZeekrCar:
    """A Zeekr Car."""

    def __init__(
        self, car: dict, controller, vehicle_data: dict, *, is_old_car: bool = False
    ) -> None:
        """Initialize the car."""
        self._car = car
        self._controller = controller
        self._vehicle_data = vehicle_data
        self.is_old_car = is_old_car

    @property
    def vin(self):
        """Return vin."""
        return self._car.get("vin", "")

    @property
    def display_name(self):
        """Return display name."""
        return f"{self._car.get('plateNo')} {self._car.get('vin')}"

    @property
    def model_code(self):
        """Return model code."""
        return self._car.get("appModelCode")

    @property
    def model_name(self):
        """Return model name."""
        model_code = self.model_code
        return MODEL_NAMES.get(model_code, model_code)

    @property
    def os_version(self):
        """Return os version."""
        return self._car.get("displayOSVersion")

    @property
    def basic_vehicle_status(self):
        """Return basic vehicle status."""
        return self._vehicle_data.get("basicVehicleStatus", {})

    @property
    def additional_vehicle_status(self):
        """Return additional vehicle status."""
        return self._vehicle_data.get("additionalVehicleStatus", {})

    @property
    def climate_status(self):
        """Return climate status."""
        return self.additional_vehicle_status.get("climateStatus", {})

    @property
    def engine_status(self):
        """Return engine status."""
        return self.basic_vehicle_status.get("engineStatus") == "engine-running"

    @property
    def interior_temp(self):
        """Return interior temperature."""
        # "interiorTemp": "25.8"
        return _round_float(self.climate_status.get("interiorTemp"))

    @property
    def exterior_temp(self):
        """Return exterior temperature."""
        return _round_float(self.climate_status.get("exteriorTemp"))

    @property
    def position(self):
        """Return position."""
        return self.basic_vehicle_status.get("position", {})

    @property
    def enable_car_locator(self):
        """Return car locator switch status."""
        return self.position.get("carLocatorStatUploadEn") == "true"

    @property
    def longitude(self):
        """Return longitude."""
        longitude = _as_float(self.position.get("longitude"))
        if longitude is not None:
            return longitude / 3600000
        return None

    @property
    def latitude(self):
        """Return latitude."""
        latitude = _as_float(self.position.get("latitude"))
        if latitude is not None:
            return latitude / 3600000
        return None

    @property
    def altitude(self):
        """Return altitude."""
        return _round_float(self.position.get("altitude"))

    @property
    def direction(self):
        """Return direction."""
        raw_direction = None
        if self.is_old_car:
            raw_direction = self.basic_vehicle_status.get("direction")
        else:
            raw_direction = self.position.get("direction")
        return _as_int(raw_direction)

    @property
    def speed(self):
        """Return speed."""
        return _round_float(self.basic_vehicle_status.get("speed"))

    @property
    def maintenance_status(self):
        """Return maintenance status."""
        return self.additional_vehicle_status.get("maintenanceStatus", {})

    @property
    def tpms_pressure_fl(self):
        """Return TPMS pressure front left."""
        return _as_int(self.maintenance_status.get("tyreStatusDriver"))

    @property
    def tpms_pressure_fr(self):
        """Return TPMS pressure front right."""
        return _as_int(self.maintenance_status.get("tyreStatusPassenger"))

    @property
    def tpms_pressure_rl(self):
        """Return TPMS pressure rear left."""
        return _as_int(self.maintenance_status.get("tyreStatusDriverRear"))

    @property
    def tpms_pressure_rr(self):
        """Return TPMS pressure rear right."""
        return _as_int(self.maintenance_status.get("tyreStatusPassengerRear"))

    @property
    def tyre_temp_fl(self):
        """Return tyre temperature front left."""
        return _round_float(self.maintenance_status.get("tyreTempDriver"))

    @property
    def tyre_temp_fr(self):
        """Return tyre temperature front right."""
        return _round_float(self.maintenance_status.get("tyreTempPassenger"))

    @property
    def tyre_temp_rl(self):
        """Return tyre temperature rear left."""
        return _round_float(self.maintenance_status.get("tyreTempDriverRear"))

    @property
    def tyre_temp_rr(self):
        """Return tyre temperature rear right."""
        return _round_float(self.maintenance_status.get("tyreTempPassengerRear"))

    @property
    def driving_safety_status(self):
        """Return driving safety status."""
        return self.additional_vehicle_status.get("drivingSafetyStatus", {})

    @property
    def door_df(self):
        """Return driver front door status."""
        return self.driving_safety_status.get("doorOpenStatusDriver") == "1"

    @property
    def door_dr(self):
        """Return driver rear door status."""
        return self.driving_safety_status.get("doorOpenStatusDriverRear") == "1"

    @property
    def door_pf(self):
        """Return passenger front door status."""
        return self.driving_safety_status.get("doorOpenStatusPassenger") == "1"

    @property
    def door_pr(self):
        """Return passenger rear door status."""
        return self.driving_safety_status.get("doorOpenStatusPassengerRear") == "1"

    @property
    def door_pos_df(self):
        """Return driver front door position."""
        return _as_int(self.driving_safety_status.get("doorPosDriver"))

    @property
    def door_pos_dr(self):
        """Return driver rear door position."""
        return _as_int(self.driving_safety_status.get("doorPosDriverRear"))

    @property
    def door_pos_pf(self):
        """Return passenger front door position."""
        return _as_int(self.driving_safety_status.get("doorPosPassenger"))

    @property
    def door_pos_pr(self):
        """Return passenger rear door position."""
        return _as_int(self.driving_safety_status.get("doorPosPassengerRear"))

    @property
    def window_fd(self):
        """Return driver front window status (True = open)."""
        return self.climate_status.get("winStatusDriver") == "1"

    @property
    def window_fp(self):
        """Return passenger front window status (True = open)."""
        return self.climate_status.get("winStatusPassenger") == "1"

    @property
    def window_rd(self):
        """Return driver rear window status (True = open)."""
        return self.climate_status.get("winStatusDriverRear") == "1"

    @property
    def window_rp(self):
        """Return passenger rear window status (True = open)."""
        return self.climate_status.get("winStatusPassengerRear") == "1"

    @property
    def window_pos_fd(self):
        """Return driver front window position."""
        return _as_int(self.climate_status.get("winPosDriver"))

    @property
    def window_pos_fp(self):
        """Return passenger front window position."""
        return _as_int(self.climate_status.get("winPosPassenger"))

    @property
    def window_pos_rd(self):
        """Return driver rear window position."""
        return _as_int(self.climate_status.get("winPosDriverRear"))

    @property
    def window_pos_rp(self):
        """Return passenger rear window position."""
        return _as_int(self.climate_status.get("winPosPassengerRear"))

    @property
    def electric_vehicle_status(self):
        """Return engine running status."""
        return self.additional_vehicle_status.get("electricVehicleStatus", {})

    @property
    def charge_level(self):
        """Return charge level."""
        return _round_float(self.electric_vehicle_status.get("chargeLevel"))

    @property
    def charging_status(self):
        """Return charging status."""
        status = _as_int(self.electric_vehicle_status.get("chargerState"))
        if status is None:
            return None
        return ChargingState[status] if 0 <= status < len(ChargingState) else "UNKNOWN"

    @property
    def is_charging(self):
        """Return True if a car is charging."""
        return self.charging_status in {"CHARGING", "DC_CHARGING"}

    @property
    def is_plugged_in(self):
        """Return True if the charge cable is connected."""
        return _as_bool(self.electric_vehicle_status.get("isPluggedIn"))

    @property
    def charge_lid_open(self):
        """Return True if either charge lid is open."""
        statuses = (
            self.electric_vehicle_status.get("chargeLidAcStatus"),
            self.electric_vehicle_status.get("chargeLidDcAcStatus"),
        )
        parsed = [_as_int(status) for status in statuses if status not in (None, "")]
        if not parsed:
            return None
        return any(status == 1 for status in parsed)

    @property
    def distance_to_empty_battery(self):
        """Return battery-only distance to empty."""
        return _round_float(
            self.electric_vehicle_status.get("distanceToEmptyOnBatteryOnly")
        )

    @property
    def time_to_fully_charged(self):
        """Return time to fully charged."""
        return _as_int(self.electric_vehicle_status.get("timeToFullyCharged"))

    @property
    def charge_voltage(self):
        """Return AC charge voltage."""
        return _round_float(self.electric_vehicle_status.get("chargeUAct"))

    @property
    def charge_current(self):
        """Return AC charge current."""
        return _round_float(self.electric_vehicle_status.get("chargeIAct"))

    @property
    def average_power_consumption(self):
        """Return average power consumption."""
        return _round_float(self.electric_vehicle_status.get("averPowerConsumption"))

    @property
    def odometer(self):
        """Return odometer."""
        return _round_float(self.maintenance_status.get("odometer"))

    @property
    def days_to_service(self):
        """Return days until service."""
        return _as_int(self.maintenance_status.get("daysToService"))

    @property
    def distance_to_service(self):
        """Return distance until service."""
        return _round_float(self.maintenance_status.get("distanceToService"))

    @property
    def low_voltage_battery_voltage(self):
        """Return low-voltage battery voltage."""
        main_battery_status = self.maintenance_status.get("mainBatteryStatus", {})
        return _round_float(main_battery_status.get("voltage"))

    @property
    def running_status(self):
        """Return running status."""
        return self.additional_vehicle_status.get("runningStatus", {})

    @property
    def average_speed(self):
        """Return average speed."""
        return _round_float(self.running_status.get("avgSpeed"))

    @property
    def trip_meter_2(self):
        """Return trip meter 2 distance."""
        return _round_float(self.running_status.get("tripMeter2"))

    @property
    def is_locked(self):
        """Return True if central locking is locked."""
        status = self.driving_safety_status.get("centralLockingStatus")
        if status is None:
            return None
        return status == "1"

    @property
    def is_unlocked(self):
        """Return True if central locking is unlocked."""
        locked = self.is_locked
        if locked is None:
            return None
        return not locked

    @property
    def trunk_open(self):
        """Return True if trunk is open."""
        status = self.driving_safety_status.get("trunkOpenStatus")
        if status is None:
            return None
        return status == "1"

    @property
    def engine_hood_open(self):
        """Return True if engine hood is open."""
        status = self.driving_safety_status.get("engineHoodOpenStatus")
        if status is None:
            return None
        return status == "1"

    @property
    def sunroof_open(self):
        """Return True if sunroof is open."""
        status = self.climate_status.get("sunroofOpenStatus")
        if status is None:
            return None
        return status == "1"

    @property
    def sunroof_position(self):
        """Return sunroof position."""
        return _as_int(self.climate_status.get("sunroofPos"))

    @property
    def rear_sunshade_open(self):
        """Return True if rear sunshade is open."""
        status = self.climate_status.get("sunCurtainRearOpenStatus")
        if status is None:
            return None
        return _as_bool(status)

    @property
    def rear_sunshade_position(self):
        """Return rear sunshade position."""
        return _as_int(self.climate_status.get("sunCurtainRearPos"))

    @property
    def defrost_on(self):
        """Return True if defrost is on."""
        status = self.climate_status.get("defrost")
        if status is None:
            return None
        return status == "1"

    @property
    def steering_wheel_heating_on(self):
        """Return True if steering wheel heating is on."""
        status = self.climate_status.get("steerWhlHeatingSts")
        if status is None:
            return None
        return status == "1"

    @property
    def driver_seat_heating(self):
        """Return driver seat heating level."""
        return _as_int(self.climate_status.get("drvHeatDetail"))

    @property
    def passenger_seat_heating(self):
        """Return passenger seat heating level."""
        return _as_int(self.climate_status.get("passHeatingDetail"))

    @property
    def driver_seat_ventilation(self):
        """Return driver seat ventilation level."""
        return _as_int(self.climate_status.get("drvVentDetail"))

    @property
    def passenger_seat_ventilation(self):
        """Return passenger seat ventilation level."""
        return _as_int(self.climate_status.get("passVentDetail"))

    @property
    def display_state(self):
        """Return a high-level display state for dashboards."""
        if self.is_charging:
            return "charging"
        if self.is_plugged_in:
            return "plugged_in"
        if self.engine_status or (self.speed is not None and self.speed > 0):
            return "driving"
        if self.trunk_open:
            return "trunk_open"
        if self.engine_hood_open:
            return "engine_hood_open"
        if self.rear_sunshade_open:
            return "rear_sunshade_open"
        # 真天窗判断:boolean true + position > 0 双重 reality check。
        # 某些 7X 配置 sunroofOpenStatus 是 stale 的恒为 true,但没真天窗时
        # sunroofPos 为 0/None,这样可以过滤掉这类误报,同时保留对真有天窗
        # 车型(高配 / 其他 zeekr 车型)的 sunroof_open 状态显示。
        if self.sunroof_open and (self.sunroof_position or 0) > 0:
            return "sunroof_open"
        if self.door_df or self.door_dr or self.door_pf or self.door_pr:
            return "door_open"
        if self.window_fd or self.window_fp or self.window_rd or self.window_rp:
            return "window_open"
        if self.is_unlocked:
            return "unlocked"
        return "parked"

    @property
    def display_state_attributes(self):
        """Return dashboard-friendly status attributes."""
        return {
            "model_code": self.model_code,
            "model_name": self.model_name,
            "is_charging": self.is_charging,
            "is_plugged_in": self.is_plugged_in,
            "charge_lid_open": self.charge_lid_open,
            "is_unlocked": self.is_unlocked,
            "door_driver_front": self.door_df,
            "door_driver_rear": self.door_dr,
            "door_passenger_front": self.door_pf,
            "door_passenger_rear": self.door_pr,
            "door_driver_front_position": self.door_pos_df,
            "door_driver_rear_position": self.door_pos_dr,
            "door_passenger_front_position": self.door_pos_pf,
            "door_passenger_rear_position": self.door_pos_pr,
            "window_driver_front": self.window_fd,
            "window_driver_rear": self.window_rd,
            "window_passenger_front": self.window_fp,
            "window_passenger_rear": self.window_rp,
            "window_driver_front_position": self.window_pos_fd,
            "window_driver_rear_position": self.window_pos_rd,
            "window_passenger_front_position": self.window_pos_fp,
            "window_passenger_rear_position": self.window_pos_rp,
            "trunk_open": self.trunk_open,
            "engine_hood_open": self.engine_hood_open,
            "sunroof_open": self.sunroof_open,
            "sunroof_position": self.sunroof_position,
            "rear_sunshade_open": self.rear_sunshade_open,
            "rear_sunshade_position": self.rear_sunshade_position,
            "battery_level": self.charge_level,
            "range_km": self.distance_to_empty_battery,
            "charging_status": self.charging_status,
            "speed": self.speed,
            "time_to_fully_charged": self.time_to_fully_charged,
            "charge_voltage": self.charge_voltage,
            "charge_current": self.charge_current,
            "average_power_consumption": self.average_power_consumption,
            "odometer": self.odometer,
            "days_to_service": self.days_to_service,
            "distance_to_service": self.distance_to_service,
        }
