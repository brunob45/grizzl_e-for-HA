"""Current limit number for Grizzl-E Connect cloud entries."""
from homeassistant.components.number import NumberDeviceClass, NumberEntity, NumberMode
from homeassistant.const import UnitOfElectricCurrent
from homeassistant.helpers.entity import DeviceInfo, EntityCategory
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .cloud import GrizzleECloudEntity, is_cloud_entry, number
from .const import DOMAIN

# Used when the station payload doesn't say what the hardware supports.
DEFAULT_MIN_CURRENT = 6
DEFAULT_MAX_CURRENT = 48


async def async_setup_entry(hass, entry, async_add_entities):
    if entry.entry_id not in hass.data.get(DOMAIN, {}):
        return

    if not is_cloud_entry(entry):
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
        return
    
    coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    async_add_entities([GrizzleECurrentLimitNumber(coordinator)])


class GrizzleECurrentLimitNumber(GrizzleECloudEntity, NumberEntity):
    """Maximum charging current. Capped by the charger's DIP switch setting."""

    _attr_device_class = NumberDeviceClass.CURRENT
    _attr_native_unit_of_measurement = UnitOfElectricCurrent.AMPERE
    _attr_native_step = 1
    _attr_mode = NumberMode.BOX
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(self, coordinator):
        super().__init__(coordinator, "current_limit", "Current Limit")

    @property
    def _model(self):
        model = self.station.get("model")
        return model if isinstance(model, dict) else {}

    @property
    def native_value(self):
        smart = self.station.get("smartCharging")
        value = number(smart.get("currentLimit")) if isinstance(smart, dict) else None
        if value is None:
            value = number(self.station.get("dipSwitchCurrentLimit"))
        return value

    @property
    def native_min_value(self):
        return number(self._model.get("minCurrent")) or DEFAULT_MIN_CURRENT

    @property
    def native_max_value(self):
        limits = [
            value
            for value in (number(self._model.get("maxCurrent")), number(self.station.get("dipSwitchCurrentLimit")))
            if value
        ]
        maximum = min(limits) if limits else DEFAULT_MAX_CURRENT
        return max(maximum, self.native_min_value)

    async def async_set_native_value(self, value):
        await self.coordinator.async_command(
            self.coordinator.client.set_current_limit(self.coordinator.station_id, int(value))
        )

        
class GrizzlESetCurrent(CoordinatorEntity, NumberEntity):
    """The maximum charge current of a car charger."""

    """https://contributors.home-assistant.io/core/entities/number/"""

    _attr_has_entity_name = True
    _attr_translation_key = "max_charge_current"
    _attr_device_class = NumberDeviceClass.CURRENT
    _attr_entity_category = EntityCategory.CONFIG
    _attr_mode = NumberMode.SLIDER
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
        await device.async_page_event(f"currentSet={int(value)}")
        self.coordinator.data[self._key] = value
        self.async_write_ha_state()
