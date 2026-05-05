"""Constants for the Zeekr Vehicle Status integration."""

CONF_AUTH_TYPE = "auth_type"
CONF_MOBILE = "mobile"
CONF_VEHICLE = "vehicle"
CONF_DEVICE_ID = "device_id"
DEFAULT_SCAN_INTERVAL = 30
MIN_SCAN_INTERVAL = 10

DATA_LISTENER = "listener"
ATTRIBUTION = "Data provided by Zeekr"
DOMAIN = "zeekr_custom"
PERCENTAGE = "%"

PLATFORMS = [
    "sensor",
    "binary_sensor",
    # 以下平台暂不启用(本期 read-only,用户不需要 GPS):
    # "device_tracker", "lock", "climate", "cover", "switch",
    # "button", "select", "update", "number", "text",
]
