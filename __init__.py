"""The Zeekr Vehicle Status integration."""

from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_ACCESS_TOKEN, CONF_SCAN_INTERVAL
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed, ConfigEntryNotReady
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.aiohttp_client import async_create_clientsession
from homeassistant.util import slugify

from .const import (
    CONF_DEVICE_ID,
    CONF_VEHICLE,
    DATA_LISTENER,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    PLATFORMS,
)
from .coordinator import ZeekrDataUpdateCoordinator
from .zeekr_api.controller import Controller
from .zeekr_api.exceptions import ZeekrAPIError, ZeekrAuthError

_LOGGER = logging.getLogger(__name__)


def _selected_vins(vehicle_filter, available_vins: set[str]) -> set[str]:
    """Return selected VINs, treating an empty filter as all vehicles."""
    if not vehicle_filter:
        return set(available_vins)
    return set(vehicle_filter)


async def async_setup_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> bool:
    """Set up Zeekr as config entry."""
    hass.data.setdefault(DOMAIN, {})
    config = config_entry.data
    options = config_entry.options
    mobile = config_entry.title

    if not hass.data[DOMAIN]:
        # TODO: 注册service
        # async_setup_services(hass)
        pass

    if mobile in hass.data[DOMAIN] and CONF_SCAN_INTERVAL in hass.data[DOMAIN][mobile]:
        scan_interval = hass.data[DOMAIN][mobile][CONF_SCAN_INTERVAL]
        hass.config_entries.async_update_entry(
            config_entry, options={CONF_SCAN_INTERVAL: scan_interval}
        )
        hass.data[DOMAIN].pop(mobile)

    session = async_create_clientsession(hass)
    device_id = config.get(CONF_DEVICE_ID, "")
    token = config.get(CONF_ACCESS_TOKEN, "")
    controller = Controller(session, device_id, token, mobile)
    try:
        await controller.auth_all_api()
        await controller.get_vehicles()
    except ZeekrAuthError as e:
        raise ConfigEntryAuthFailed from e
    except ZeekrAPIError as e:
        raise ConfigEntryNotReady from e

    vehicle_filter = options.get(CONF_VEHICLE, config.get(CONF_VEHICLE, []))
    cars = await controller.generate_car_objects(vehicle_filter)
    coordinators = {
        vin: ZeekrDataUpdateCoordinator(
            hass,
            config_entry,
            controller,
            vin,
            options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL),
        )
        for vin in cars
    }

    hass.data[DOMAIN][config_entry.entry_id] = {
        "controller": controller,
        "coordinators": coordinators,
        "cars": cars,
        DATA_LISTENER: [config_entry.add_update_listener(update_listener)],
    }
    await hass.config_entries.async_forward_entry_setups(config_entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(
        config_entry, PLATFORMS
    )
    if unload_ok:
        entry_data = hass.data[DOMAIN].pop(config_entry.entry_id, None)
        if entry_data:
            for listener in entry_data.get(DATA_LISTENER, []):
                listener()
        _LOGGER.debug("Unloaded entry for %s", config_entry.title)
    return unload_ok


async def update_listener(hass: HomeAssistant, config_entry: ConfigEntry):
    """Update when config_entry options update."""
    entry_data = hass.data[DOMAIN][config_entry.entry_id]

    current_cars = entry_data["cars"]
    current_vins = set(current_cars.keys())

    # 获取新的车辆过滤选项
    new_vehicle_filter = config_entry.options.get(
        CONF_VEHICLE,
        config_entry.data.get(CONF_VEHICLE, []),
    )
    new_vins = _selected_vins(new_vehicle_filter, current_vins)

    # 计算需要删除的车辆
    vins_to_remove = current_vins - new_vins

    # 如果有需要删除的车辆，先从实体注册表中删除对应的实体
    if vins_to_remove:
        entity_registry = er.async_get(hass)

        # unique_id is slugify("{vin} {type}") => "<slugified_vin>_<type>".
        # Match by startswith so VINs that contain underscores after
        # slugify don't get truncated by split("_")[0].
        slugified_vins_to_remove = {slugify(v) for v in vins_to_remove}

        # 获取所有属于这个配置条目的实体
        entities_to_remove = [
            entity_entry.entity_id
            for entity_entry in entity_registry.entities.values()
            if entity_entry.config_entry_id == config_entry.entry_id
            and entity_entry.unique_id
            and any(
                entity_entry.unique_id == sv
                or entity_entry.unique_id.startswith(sv + "_")
                for sv in slugified_vins_to_remove
            )
        ]

        # 从实体注册表中删除这些实体
        for entity_id in entities_to_remove:
            entity_registry.async_remove(entity_id)

        device_registry = dr.async_get(hass)

        # 获取所有属于这个配置条目的设备
        devices_to_remove = [
            device_entry.id
            for device_entry in device_registry.devices.values()
            if config_entry.entry_id in device_entry.config_entries
            and any(
                identifier[1] in vins_to_remove
                for identifier in device_entry.identifiers
            )
        ]

        # 从设备注册表中删除这些设备
        for device_id in devices_to_remove:
            device_registry.async_remove_device(device_id)

    await hass.config_entries.async_reload(config_entry.entry_id)
