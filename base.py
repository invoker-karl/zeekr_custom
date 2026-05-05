"""Support for Zeekr cars and energy sites."""

from homeassistant.core import callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import slugify

from .const import ATTRIBUTION, DOMAIN
from .coordinator import ZeekrDataUpdateCoordinator
from .zeekr_api.car import ZeekrCar


class ZeekrBaseEntity(CoordinatorEntity[ZeekrDataUpdateCoordinator]):
    """Representation of a Zeekr device."""

    type: str
    _attr_attribution = ATTRIBUTION
    _attr_has_entity_name = True
    _enabled_by_default: bool = True
    _memorized_unique_id: str | None = None

    def __init__(
        self, base_unique_id: str, coordinator: ZeekrDataUpdateCoordinator
    ) -> None:
        """Initialise the Zeekr device."""
        if not getattr(self, "type", None):
            raise RuntimeError(
                f"{type(self).__name__} must define class attribute 'type' "
                f"or set self.type before calling super().__init__"
            )
        super().__init__(coordinator)
        self._attr_unique_id = slugify(f"{base_unique_id} {self.type}")
        self._attr_entity_registry_enabled_default = self._enabled_by_default


class ZeekrCarEntity(ZeekrBaseEntity):
    """Representation of a Zeekr car device."""

    def __init__(
        self,
        car: ZeekrCar,
        coordinator: ZeekrDataUpdateCoordinator,
    ) -> None:
        """Initialise the Zeekr car device."""
        vin = car.vin
        super().__init__(vin, coordinator)
        self._car = car
        display_name = car.display_name
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, car.vin)},  # 设备唯一标识符
            name=display_name,  # 展示名称
            manufacturer="Zeekr",  # 品牌
            model=car.model_code,  # 车辆型号
            sw_version=car.os_version,  # 软件版本
        )
        self._last_update_success: bool | None = None
        self.last_update_time: float | None = None

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        super()._handle_coordinator_update()

    async def update_controller(
        self,
    ) -> None:
        """Get the latest data from Zeekr."""
        await self.coordinator.controller.update(self._car.vin)
        await self.coordinator.async_refresh()
