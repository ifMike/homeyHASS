"""Constants for the Homey integration."""
from __future__ import annotations

DOMAIN = "homey_hass"
UNIQUE_ID_PREFIX = "homey_hass_"

CONF_HOST = "host"
CONF_TOKEN = "token"
CONF_DEVICE_FILTER = "device_filter"
CONF_WORKING_ENDPOINT = "working_endpoint"  # Store which endpoint structure worked
CONF_POLL_INTERVAL = "poll_interval"
CONF_RECOVERY_COOLDOWN = "recovery_cooldown"
CONF_INVERT_LIGHT_TEMPERATURE = "invert_light_temperature"
CONF_EXPOSE_SETTABLE_TEXT = "expose_settable_text"
CONF_EXPOSE_READONLY_STRINGS = "expose_readonly_strings"
CONF_USE_CAPABILITY_TITLES = "use_capability_titles"
CONF_TEMPERATURE_UNIT_OVERRIDES = "temperature_unit_overrides"

DEFAULT_NAME = "Homey"
DEFAULT_POLL_INTERVAL = 10  # seconds (fallback when Socket.IO is down)
DEFAULT_RECOVERY_COOLDOWN = 300  # seconds
DEFAULT_INVERT_LIGHT_TEMPERATURE = True
DEFAULT_EXPOSE_SETTABLE_TEXT = False
DEFAULT_EXPOSE_READONLY_STRINGS = True
DEFAULT_USE_CAPABILITY_TITLES = False

# GitHub issue URL for reporting new/unknown capabilities
CAPABILITY_REPORT_ISSUE_URL = "https://github.com/ifMike/homeyHASS/issues/new"

# Services
SERVICE_TEST_CAPABILITY_REPORT = "test_capability_report"
SERVICE_SET_DEVICE_TEMPERATURE_UNIT = "set_device_temperature_unit"

# Homey API endpoints
# Try manager API structure first (based on Homey API documentation)
API_BASE_V1 = "/api/v1"
API_BASE_MANAGER = "/api/manager"
API_SYSTEM = f"{API_BASE_MANAGER}/system/info"  # Manager API structure
API_DEVICES = f"{API_BASE_MANAGER}/devices/device/"  # Manager API structure with trailing slash
API_DEVICES_NO_SLASH = f"{API_BASE_MANAGER}/devices/device"  # Without trailing slash
API_DEVICES_V1 = f"{API_BASE_V1}/device"  # Fallback v1 structure
API_CAPABILITIES = f"{API_BASE_MANAGER}/capabilities/capability"
API_FLOWS = f"{API_BASE_MANAGER}/flow/flow"  # Standard flows: singular "flow" not "flows"
API_ADVANCED_FLOWS = f"{API_BASE_MANAGER}/flow/advancedflow"  # Advanced flows endpoint
API_ZONES = f"{API_BASE_MANAGER}/zones/zone"  # Rooms/zones in Homey
API_SCENES = f"{API_BASE_MANAGER}/scene/scene"  # Scenes endpoint
API_MOODS = f"{API_BASE_MANAGER}/moods/mood"  # Moods endpoint (plural "moods" per API v3)
API_LOGIC_VARIABLES = f"{API_BASE_MANAGER}/logic/variable"  # Logic variables (number/string/boolean)

# Device capability mappings to HA platforms
CAPABILITY_TO_PLATFORM = {
    "button": "button",
    "onoff": "switch",
    "dim": "light",
    "light_hue": "light",
    "light_saturation": "light",
    "light_temperature": "light",
    "lightScenes": "light",
    "lightScenes.light": "light",
    "windowcoverings_state": "cover",
    "windowcoverings_tilt_up": "cover",
    "windowcoverings_tilt_down": "cover",
    "target_temperature": "climate",
    "measure_temperature": "sensor",
    "measure_humidity": "sensor",
    "measure_pressure": "sensor",
    "measure_power": "sensor",
    "measure_voltage": "sensor",
    "measure_current": "sensor",
    "measure_luminance": "sensor",
    "measure_co2": "sensor",
    "measure_co": "sensor",
    "measure_distance": "sensor",
    "alarm_motion": "binary_sensor",
    "alarm_contact": "binary_sensor",
    "alarm_tamper": "binary_sensor",
    "alarm_vibration": "binary_sensor",
    "alarm_occupancy": "binary_sensor",
    "alarm_presence": "binary_sensor",
    "alarm_smoke": "binary_sensor",
    "alarm_co": "binary_sensor",
    "alarm_co2": "binary_sensor",
    "alarm_water": "binary_sensor",
    "alarm_battery": "binary_sensor",
    "fan_speed": "fan",
    "locked": "lock",
    "volume_set": "media_player",
    "volume_mute": "media_player",
    "speaker_playing": "media_player",
    "speaker_next": "media_player",
    "speaker_prev": "media_player",
}

_GENERIC_SENSOR_CAPABILITIES = frozenset(
    {
        "accumulatedCost",
        "clean_time",
        "clean_area",
        "clean_last",
        "position_x",
        "position_y",
    }
)


def capability_base(cap_id: str) -> str:
    """Return the base capability id (part before the first dot)."""
    return cap_id.split(".")[0] if "." in cap_id else cap_id


def is_capability_supported(cap_id: str) -> bool:
    """Return True when the integration already handles this capability."""
    base = capability_base(cap_id)
    if base in CAPABILITY_TO_PLATFORM:
        return True
    if (
        cap_id.startswith(("measure_", "meter_", "alarm_"))
        or base.startswith(("measure_", "meter_", "alarm_"))
    ):
        return True
    if cap_id in _GENERIC_SENSOR_CAPABILITIES or base in _GENERIC_SENSOR_CAPABILITIES:
        return True
    capability_lower = cap_id.lower()
    if any(keyword in capability_lower for keyword in ("migrate", "reset", "identify")):
        return True
    return False

