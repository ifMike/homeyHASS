"""Helper functions for device info."""
from __future__ import annotations

import logging
from typing import Any

from .const import DOMAIN, UNIQUE_ID_PREFIX
def build_device_identifier(
    homey_id: str | None, device_id: str, multi_homey: bool = False
) -> tuple[str, str]:
    """Build a stable device registry identifier scoped to a Homey hub."""
    if multi_homey and homey_id:
        return (DOMAIN, f"{homey_id}:{device_id}")
    return (DOMAIN, device_id)


def build_entity_unique_id(
    homey_id: str | None,
    primary_id: str,
    suffix: str,
    multi_homey: bool = False,
) -> str:
    """Build a unique entity ID scoped to a Homey hub."""
    if multi_homey and homey_id:
        return f"{UNIQUE_ID_PREFIX}{homey_id}_{primary_id}_{suffix}"
    return f"{UNIQUE_ID_PREFIX}{primary_id}_{suffix}"


def extract_unique_id_primary(
    unique_id: str,
    suffix: str,
    *,
    homey_id: str | None = None,
    multi_homey: bool = False,
) -> str | None:
    """Extract the primary ID from a unique_id ending with _{suffix}."""
    if not unique_id.startswith(UNIQUE_ID_PREFIX):
        return None
    tail = f"_{suffix}"
    body = unique_id[len(UNIQUE_ID_PREFIX) :]
    if not body.endswith(tail):
        return None
    middle = body[: -len(tail)]
    if multi_homey and homey_id and middle.startswith(f"{homey_id}_"):
        middle = middle[len(homey_id) + 1 :]
    return middle or None


def extract_device_id(identifier: tuple[str, str]) -> str | None:
    """Extract device_id from a device registry identifier."""
    if len(identifier) < 2 or identifier[0] != DOMAIN:
        return None
    value = identifier[1]
    if ":" in value:
        return value.split(":", 1)[1]
    return value


def split_device_identifier(identifier: tuple[str, str]) -> tuple[str | None, str | None]:
    """Split a device registry identifier into (homey_id, device_id)."""
    if len(identifier) < 2 or identifier[0] != DOMAIN:
        return None, None
    value = identifier[1]
    if ":" in value:
        homey_id, device_id = value.split(":", 1)
        return homey_id, device_id
    return None, value

_LOGGER = logging.getLogger(__name__)

WINDOW_COVERING_DEVICE_CLASSES = frozenset({
    "windowcoverings",
    "cover",
    "curtain",
    "blind",
    "shutter",
    "awning",
    "garagedoor",
})

STANDARD_COVER_CAPABILITIES = frozenset({
    "windowcoverings_state",
    "windowcoverings_set",
    "garagedoor_closed",
    "windowcoverings_closed",
})

LIGHT_ONLY_CAPABILITIES = frozenset({
    "light_hue",
    "light_saturation",
    "light_temperature",
    "lightScenes",
})


def has_standard_cover_capabilities(capabilities: dict[str, Any]) -> bool:
    """Return True when the device exposes standard Homey cover capabilities."""
    return bool(set(capabilities.keys()) & STANDARD_COVER_CAPABILITIES)


def is_legacy_dim_cover(
    capabilities: dict[str, Any],
    device_class: str | None = None,
    driver_uri: str | None = None,
    *,
    driver_id: str | None = None,
) -> bool:
    """Return True when a window covering uses dim (0-1) instead of windowcoverings_*."""
    if has_standard_cover_capabilities(capabilities):
        return False
    if "dim" not in capabilities:
        return False
    if capabilities.get("dim", {}).get("setable") is False:
        return False

    caps = set(capabilities.keys())
    if caps & LIGHT_ONLY_CAPABILITIES or any(cap.startswith("lightScenes") for cap in caps):
        return False

    device_class_lower = (device_class or "").lower()
    if device_class_lower in WINDOW_COVERING_DEVICE_CLASSES:
        return True

    driver_lower = (driver_uri or "").lower()
    driver_id_lower = (driver_id or "").lower()
    if "fibaro" in driver_lower or "fibaro" in driver_id_lower:
        shutter_tokens = ("fgr", "fgw", "roller", "shutter", "blind")
        if any(token in driver_lower or token in driver_id_lower for token in shutter_tokens):
            return True

    return False


def should_create_cover_entity(
    capabilities: dict[str, Any],
    device_class: str | None,
    driver_uri: str | None = None,
    *,
    driver_id: str | None = None,
    is_devicegroups_group: bool = False,
) -> bool:
    """Return True when the integration should create a cover entity for this device."""
    if has_standard_cover_capabilities(capabilities):
        return True
    if (
        is_devicegroups_group
        and (device_class or "").lower() in WINDOW_COVERING_DEVICE_CLASSES
    ):
        return True
    return is_legacy_dim_cover(
        capabilities,
        device_class,
        driver_uri,
        driver_id=driver_id,
    )


def format_capability_label(capability_id: str) -> str:
    """Format a capability ID into a human-friendly label."""
    return capability_id.replace("_", " ").title()


def get_capability_label(
    capability_id: str,
    capability_data: dict[str, Any] | None,
    use_titles: bool | None,
    *,
    legacy_uses_title: bool,
) -> str:
    """Return a label for a capability, respecting title preference."""
    title = (capability_data or {}).get("title")
    fallback = format_capability_label(capability_id)
    if use_titles is True:
        return title or fallback
    if use_titles is False:
        return fallback
    # Legacy behavior: only use titles where they were already used before
    return title or fallback if legacy_uses_title else fallback

def get_device_type(capabilities: dict[str, Any], driver_uri: str | None = None, device_class: str | None = None) -> str:
    """Determine device type based on capabilities, driver URI, and optionally Homey device class.
    
    Priority order (control capabilities first, then sensors):
    1. Cover (windowcoverings_state)
    2. Light (dim, light_hue, light_temperature)
    3. Climate (target_temperature)
    4. Fan (fan_speed)
    5. Lock (locked)
    6. Media Player (volume_set, speaker_playing, etc.)
    7. Switch (onoff) - but only if not already classified above
    8. Sensor (measure_*, alarm_*) - only if no control capabilities
    
    Args:
        capabilities: Dictionary of device capabilities
        driver_uri: Optional driver URI (e.g., "philips.hue", "fibaro.fgwreu111") for device-specific detection
        device_class: Optional Homey device class (e.g., "light", "socket", "sensor") - very reliable indicator
    """
    caps = set(capabilities.keys())
    
    # Use Homey's device class if available - it's the most reliable indicator
    # Reference: https://apps.developer.homey.app/the-basics/devices/capabilities
    # Complete mapping of all Homey device classes to HA entity types
    if device_class:
        # Reference: https://apps-sdk-v3.developer.homey.app/tutorial-device-classes.html
        class_mapping = {
            # Core device classes
            "light": "light",
            "socket": "switch",  # Homey "socket" = switch/outlet in HA
            "switch": "switch",
            "sensor": "sensor",
            "thermostat": "climate",
            "heater": "climate",
            "speaker": "media_player",
            "tv": "media_player",
            "remote": "sensor",  # Remotes are typically sensors/binary sensors
            "button": "device",  # Virtual buttons, physical buttons - entities created by button platform
            "other": "device",
            # Window coverings
            "windowcoverings": "cover",  # Official Homey class for covers
            "cover": "cover",  # Alternative naming
            "garagedoor": "cover",
            "curtain": "cover",
            "blind": "cover",
            "shutter": "cover",
            "awning": "cover",
            # Additional classes
            "lock": "lock",
            "fan": "fan",
            "vacuumcleaner": "vacuum",
            "camera": "device",  # Cameras don't have a direct HA equivalent
            "doorbell": "binary_sensor",  # Doorbells are typically binary sensors
        }
        # Check if it's a cover first (standard or legacy dim-based window coverings)
        if has_standard_cover_capabilities(capabilities) or is_legacy_dim_cover(
            capabilities, device_class, driver_uri
        ):
            return "cover"
        # Map known classes
        if device_class in class_mapping:
            mapped_type = class_mapping[device_class]
            # Don't override if we have more specific capabilities
            if mapped_type == "switch" and any(cap in caps for cap in ["dim", "light_hue", "light_temperature"]):
                # Device class says "socket" but has light capabilities - treat as light
                return "light"
            return mapped_type
        # Unknown device class - log for debugging but continue with capability-based detection
        _LOGGER.debug("Unknown device class '%s' - using capability-based detection", device_class)
    
    # PRIORITY 1: Cover devices (standard or legacy dim-based window coverings)
    # This must come FIRST because covers can also have metering (measure_power)
    # Reference: https://apps.developer.homey.app/the-basics/devices/capabilities
    if has_standard_cover_capabilities(capabilities) or is_legacy_dim_cover(
        capabilities, device_class, driver_uri
    ):
        return "cover"
    
    # PRIORITY 2: Light devices
    # Check for light capabilities: dim, light_hue, light_saturation, light_temperature
    has_light_capabilities = any(
        cap in caps for cap in ["light_hue", "light_saturation", "light_temperature", "dim"]
    )
    if has_light_capabilities:
        return "light"
    
    # PRIORITY 3: Climate devices
    if "target_temperature" in caps:
        return "climate"
    
    # PRIORITY 4: Fan devices
    if "fan_speed" in caps:
        return "fan"
    
    # PRIORITY 5: Lock devices
    if "locked" in caps:
        return "lock"
    
    # PRIORITY 6: Media Player devices
    if any(cap in caps for cap in ["volume_set", "speaker_playing", "speaker_next"]):
        return "media_player"
    
    # PRIORITY 7: Switch devices (onoff capability)
    # IMPORTANT: This comes BEFORE sensors because devices with onoff + measure_power
    # should be classified as switches (with sensor entities), not sensors
    # Check for regular onoff capability OR sub-capabilities (onoff.output1, onoff.output2, etc.)
    if "onoff" in caps or any(cap.startswith("onoff.") for cap in caps):
        return "switch"
    
    # PRIORITY 8: Sensor devices (only if no control capabilities found)
    # Only classify as sensor if there are no control capabilities
    if any(cap.startswith("alarm_") for cap in caps):
        return "sensor"
    if any(cap.startswith("measure_") for cap in caps):
        return "sensor"
    
    # Device-specific detection based on driver URI
    # Some devices might not expose all capabilities correctly, so we can infer from driver
    if driver_uri:
        driver_lower = driver_uri.lower()
        
        # Philips Hue devices - should be lights if they have onoff
        # Even White & Ambiance bulbs should be lights (they have dim + light_temperature)
        if "philips" in driver_lower and "hue" in driver_lower:
            if "onoff" in caps:
                # Check if it has dim or temperature capabilities
                if "dim" in caps or "light_temperature" in caps:
                    return "light"
                # Even if just onoff, treat as light (might be missing capability exposure)
                return "light"
        
        # Fibaro switches/outlets - should be switches if they have onoff
        # Note: Roller shutters already handled above (windowcoverings_* or legacy dim)
        if "fibaro" in driver_lower:
            if is_legacy_dim_cover(capabilities, device_class, driver_uri):
                return "cover"
            if "onoff" in caps or any(cap.startswith("onoff.") for cap in caps):
                return "switch"
        
        # Shelly devices - should be switches if they have onoff
        if "shelly" in driver_lower:
            if "onoff" in caps or any(cap.startswith("onoff.") for cap in caps):
                return "switch"
        
        # Sunricher dimming devices - should be lights if they have onoff and dim
        if "sunricher" in driver_lower:
            if "onoff" in caps:
                if "dim" in caps:
                    return "light"
                # Even if dim not exposed, if it's a Sunricher dimmer, treat as light
                return "light"
    
    return "device"


def get_device_info(
    homey_id: str | None,
    device_id: str,
    device: dict[str, Any],
    zones: dict[str, dict[str, Any]] | None = None,
    multi_homey: bool = False,
) -> dict[str, Any]:
    """Get device info with room and type information.
    
    All entities from the same device MUST use identical device_info
    to ensure they're grouped under one device in Home Assistant.
    """
    capabilities = device.get("capabilitiesObj", {})
    driver_uri = device.get("driverUri")
    device_class = device.get("class")
    device_type = get_device_type(capabilities, driver_uri, device_class)
    
    # Get room/zone information
    zone_id = device.get("zone")
    room_name = None
    if zone_id and zones:
        zone = zones.get(zone_id)
        if zone:
            room_name = zone.get("name")
    
    # Extract manufacturer and model from driverUri
    driver_uri = device.get("driverUri", "")
    manufacturer = "Unknown"
    model = "Unknown"
    if driver_uri:
        parts = driver_uri.split(".")
        if len(parts) >= 2:
            manufacturer = parts[0] or "Unknown"
            model = parts[-1] or "Unknown"
    
    # Build device info - MUST be identical for all entities from same device
    # The identifiers tuple is the key that Home Assistant uses to group entities
    device_info: dict[str, Any] = {
        "identifiers": {build_device_identifier(homey_id, device_id, multi_homey)},  # Scoped by Homey hub
        "name": device.get("name") or "Unknown Device",  # Use consistent None handling
        "manufacturer": manufacturer,
        "model": model,
        "suggested_area": room_name,  # This will create/use areas in Home Assistant
    }
    
    # Ensure all fields are consistent (no None values that could cause issues)
    if not device_info["name"]:
        device_info["name"] = "Unknown Device"
    
    return device_info


def get_entity_name_with_type(device: dict[str, Any], entity_type: str) -> str:
    """Get entity name with device type prefix for better searchability."""
    device_name = device.get("name", "Unknown")
    capabilities = device.get("capabilitiesObj", {})
    driver_uri = device.get("driverUri")
    device_class = device.get("class")
    device_type = get_device_type(capabilities, driver_uri, device_class)
    
    # Add type prefix if it's helpful
    type_labels = {
        "light": "💡",
        "switch": "🔌",
        "sensor": "📊",
        "climate": "🌡️",
        "fan": "🌀",
        "cover": "🪟",
        "lock": "🔒",
        "media_player": "🔊",
    }
    
    # For now, just return the device name - Home Assistant's area organization will help
    return device_name

