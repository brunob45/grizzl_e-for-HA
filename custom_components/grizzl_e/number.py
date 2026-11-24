import logging

from homeassistant.components.number import (
    NumberDeviceClass,
    NumberEntity,
    NumberMode,
)
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.const import EntityCategory, UnitOfElectricCurrent
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, entry, async_add_entities):
    # Get the device and coordinator from hass.data
    if DOMAIN not in hass.data or entry.entry_id not in hass.data[DOMAIN]:
        return

    device = hass.data[DOMAIN][entry.entry_id]["device"]
    coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]

    # Set device info on coordinator for binary sensors to access
    coordinator.device = device

    # Ensure we have fresh data
    if coordinator.data is None:
        await coordinator.async_config_entry_first_refresh()

    if all(
        [key in coordinator.data for key in ["minCurrent", "curDesign", "currentSet"]]
    ):
        async_add_entities([GrizzlESetCurrent(coordinator)])


class GrizzlESetCurrent(CoordinatorEntity, NumberEntity):
    """The maximum charge current of a car charger."""

    """https://contributors.home-assistant.io/core/entities/number/"""

    _attr_has_entity_name = True
    _attr_translation_key = "max_charge_current"
    _attr_device_class = NumberDeviceClass.CURRENT
    # _attr_entity_category = EntityCategory.CONFIG
    _attr_mode = NumberMode.SLIDER
    # _attr_native_min_value = 7
    # _attr_native_max_value = 48
    _attr_native_step = 1
    _attr_native_unit_of_measurement = UnitOfElectricCurrent.AMPERE

    @property
    def device_info(self) -> DeviceInfo:
        """Return the device info."""
        return self.coordinator.device.device_info

    def __init__(self, coordinator) -> None:
        """Initialize the number."""
        super().__init__(coordinator)
        self._attr_name = "Current Limit"
        self._key = "currentSet"
        self._attr_unique_id = f"{self.coordinator.config_entry.entry_id}_currentSet"
        self._attr_native_min_value = self.coordinator.data.get("minCurrent")
        self._attr_native_max_value = self.coordinator.data.get("curDesign")

    @property
    def native_value(self):
        if not self.coordinator.data:
            return None

        value = self.coordinator.data.get(self._key)

        # Handle None values
        if value is None:
            return None

        return int(value)

    async def async_set_native_value(self, value: float) -> None:
        """Set the maximum charge current."""
        device = self.coordinator.device
        await device.async_page_event(f"{self._key}={int(value)}")
        self.coordinator.data[self._key] = value
        self.async_write_ha_state()
