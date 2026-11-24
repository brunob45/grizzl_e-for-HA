import logging
from typing import Any

from homeassistant.components.switch import (
    SwitchDeviceClass,
    SwitchEntity,
)
from homeassistant.helpers.entity import DeviceInfo
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

    if all([key in coordinator.data for key in ["evseEnabled"]]):
        async_add_entities([GrizzleEEnableSwitch(coordinator)])


class GrizzleEEnableSwitch(CoordinatorEntity, SwitchEntity):
    """Enable switch for Grizzl-E charger."""

    """https://contributors.home-assistant.io/core/entities/switch/"""

    _attr_has_entity_name = True
    _attr_device_class = SwitchDeviceClass.SWITCH

    @property
    def device_info(self) -> DeviceInfo:
        """Return the device info."""
        return self.coordinator.device.device_info

    def __init__(self, coordinator):
        super().__init__(coordinator)
        self._attr_name = "EVSE Enabled"
        self._key = "evseEnabled"
        self._attr_unique_id = f"{self.coordinator.config_entry.entry_id}_evseEnabled"

    @property
    def is_on(self):
        if not self.coordinator.data:
            return None
        val = self.coordinator.data.get(self._key)
        if isinstance(val, (int, float)):
            return val == 0  # 1 means off
        return bool(val)

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the outlet on."""
        device = self.coordinator.device
        await device.async_page_event("evseEnabled=0")  # 0 means on
        self.coordinator.data[self._key] = True
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the outlet off."""
        device = self.coordinator.device
        await device.async_page_event("evseEnabled=1")  # 1 means off
        self.coordinator.data[self._key] = False
        self.async_write_ha_state()
