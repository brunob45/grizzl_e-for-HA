"""Device class for Grizzl-E EV Charger."""
import aiohttp
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DOMAIN, MANUFACTURER, MODEL

class GrizzleEDevice:
    """Grizzl-E device."""

    def __init__(self, coordinator: DataUpdateCoordinator, entry, session, timeout):
        """Initialize the device."""
        self.coordinator = coordinator
        self.entry = entry

        # HTTP client
        self.session = session
        self.timeout = timeout


    @property
    def device_info(self) -> DeviceInfo:
        """Return device information.

        Prefer dynamic data from the EVSE payload when available so the
        device registry shows accurate model and firmware.
        """
        data = getattr(self.coordinator, "data", None) or {}
        # Prefer payload model when present, fallback to static default
        model = str(data.get("model") or MODEL)
        # Use EVSE main firmware as device software version; trim whitespace
        sw_version = str(data.get("verFWMain") or "").strip() or None
        # Use serial if available for nicer identification in registry
        serial = data.get("serialNum") or data.get("stationId")
        serial = str(serial) if serial is not None else None

        return DeviceInfo(
            identifiers={(DOMAIN, self.entry.entry_id)},
            name=self.entry.title,
            manufacturer=MANUFACTURER,
            model=model,
            sw_version=sw_version,
            serial_number=serial,
            configuration_url=f"http://{self.entry.data['host']}",
        )

    async def async_page_event(self, data: str):
        """Send update."""
        host = self.entry.data["host"]
        username = self.entry.data["username"]
        password = self.entry.data["password"]

        url = f"http://{host}/pageEvent"
        try:
            async with self.session.post(
                url,
                auth=aiohttp.BasicAuth(username, password),
                timeout=self.timeout,
                data=data,
            ) as resp:
                if resp.status != 200:
                    raise UpdateFailed(f"Bad status {resp.status}")
                return
        except Exception as err:
            raise UpdateFailed(f"Error sending Grizzl-E page event: {err}")
