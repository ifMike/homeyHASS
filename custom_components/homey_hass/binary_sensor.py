"""Support for Homey binary sensors."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import CONF_USE_CAPABILITY_TITLES, DOMAIN
from .coordinator import HomeyDataUpdateCoordinator
from .device_info import build_entity_unique_id, get_device_info

_LOGGER = logging.getLogger(__name__)

# Mapping of Homey alarm capabilities to HA binary sensor device classes
CAPABILITY_TO_DEVICE_CLASS = {
    "alarm_motion": BinarySensorDeviceClass.MOTION,
    "alarm_contact": BinarySensorDeviceClass.DOOR,
    "alarm_tamper": BinarySensorDeviceClass.TAMPER,
    "alarm_vibration": BinarySensorDeviceClass.VIBRATION,
    "alarm_occupancy": BinarySensorDeviceClass.OCCUPANCY,
    "alarm_presence": BinarySensorDeviceClass.PRESENCE,
    "alarm_smoke": BinarySensorDeviceClass.SMOKE,
    "alarm_co": BinarySensorDeviceClass.CO,
    "alarm_co2": None,  # CO2 device class not available in all HA versions
    "alarm_water": BinarySensorDeviceClass.MOISTURE,
    "alarm_battery": BinarySensorDeviceClass.BATTERY,
    # Additional binary sensor capabilities
    "alarm_gas": BinarySensorDeviceClass.GAS,
    "alarm_fire": BinarySensorDeviceClass.SMOKE,  # Use SMOKE as closest match
    "alarm_panic": None,  # Generic binary sensor
    "alarm_burglar": None,  # Generic binary sensor
    "alarm_generic": None,  # Generic binary sensor
    "alarm_maintenance": None,  # Generic binary sensor
    "button": None,  # Generic binary sensor (BinarySensorDeviceClass.BUTTON may not be available in all versions)
    "vibration": None,  # Generic binary sensor
    # Thermostat-specific binary sensors
    "thermofloor_onoff": BinarySensorDeviceClass.RUNNING,  # Heating active/idle
    # Vacuum-specific binary sensors
    "water_box_attached": None,  # Generic binary sensor
    "mop_attached": None,  # Generic binary sensor
    "mop_dry_status": None,  # Generic binary sensor
    # Heat pump / HVAC status flags
    "compressor_active": BinarySensorDeviceClass.RUNNING,
    "circulation_pump": BinarySensorDeviceClass.RUNNING,
    "hot_water": BinarySensorDeviceClass.RUNNING,
}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Homey binary sensors from a config entry."""
    coordinator: HomeyDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    api = hass.data[DOMAIN][entry.entry_id]["api"]
    zones = hass.data[DOMAIN][entry.entry_id].get("zones", {})
    multi_homey = hass.data[DOMAIN][entry.entry_id].get("multi_homey", False)
    homey_id = hass.data[DOMAIN][entry.entry_id].get("homey_id")

    entities = []
    use_titles = entry.options.get(
        CONF_USE_CAPABILITY_TITLES, entry.data.get(CONF_USE_CAPABILITY_TITLES)
    )
    # Use coordinator data if available (more up-to-date), otherwise fetch fresh
    devices = coordinator.data if coordinator.data else await api.get_devices()
    
    # Filter devices if device_filter is configured
    from . import filter_devices
    devices = filter_devices(devices, entry.data.get("device_filter"))

    for device_id, device in devices.items():
        capabilities = device.get("capabilitiesObj", {})
        
        # First, handle explicitly mapped capabilities
        for capability_id in CAPABILITY_TO_DEVICE_CLASS:
            if capability_id in capabilities:
                cap_data = capabilities.get(capability_id, {})
                # Skip settable boolean capabilities - they should be switches
                if cap_data.get("setable"):
                    continue
                entities.append(
                    HomeyBinarySensor(
                        coordinator,
                        device_id,
                        device,
                        capability_id,
                        api,
                        zones,
                        homey_id,
                        multi_homey,
                        use_titles,
                    )
                )

        # Then, handle ALL boolean capabilities generically (including unknown ones)
        # This ensures we support new device types and capabilities automatically
        # Reference: https://apps.developer.homey.app/the-basics/devices/capabilities#sub-capabilities-using-the-same-capability-more-than-once
        for capability_id, cap_data in capabilities.items():
            # Skip if already handled above
            if capability_id in CAPABILITY_TO_DEVICE_CLASS:
                continue
            
            # Check if this is a boolean-type capability
            is_boolean = cap_data.get("type") == "boolean"
            
            # Skip if not boolean
            if not is_boolean:
                continue
            
            # Skip settable boolean capabilities that are buttons (handled by button platform)
            # and other settable booleans (handled by switch platform)
            if cap_data.get("setable"):
                # Check if it's a button capability (button, gardena_button.*, etc.)
                is_button = (
                    capability_id == "button" or
                    capability_id.startswith("button.") or
                    capability_id.endswith("_button") or
                    capability_id.startswith("gardena_button.")
                )
                if is_button:
                    continue
                # Skip settable booleans; they are handled by switch platform
                continue
            
            # Skip internal Homey maintenance capabilities
            capability_lower = capability_id.lower()
            if any(keyword in capability_lower for keyword in ["migrate", "reset", "identify"]):
                _LOGGER.debug("Skipping internal Homey maintenance capability: %s", capability_id)
                continue
            
            # Create binary sensor for this boolean capability
                entities.append(
                    HomeyBinarySensor(
                        coordinator,
                        device_id,
                        device,
                        capability_id,
                        api,
                        zones,
                        homey_id,
                        multi_homey,
                        use_titles,
                    )
                )

    async_add_entities(entities)


class HomeyBinarySensor(CoordinatorEntity, BinarySensorEntity):
    """Representation of a Homey binary sensor."""

    def __init__(
        self,
        coordinator: HomeyDataUpdateCoordinator,
        device_id: str,
        device: dict[str, Any],
        capability_id: str,
        api,
        zones: dict[str, dict[str, Any]] | None = None,
        homey_id: str | None = None,
        multi_homey: bool = False,
        use_titles: bool | None = None,
    ) -> None:
        """Initialize the binary sensor."""
        super().__init__(coordinator)
        self._device_id = device_id
        self._device = device
        self._capability_id = capability_id
        self._api = api
        self._homey_id = homey_id
        self._multi_homey = multi_homey

        # Handle sub-capabilities (e.g., alarm_motion.outside)
        base_capability = capability_id.split(".")[0] if "." in capability_id else capability_id
        capability_data = device.get("capabilitiesObj", {}).get(capability_id, {})

        # Generate entity name - handle sub-capabilities
        if use_titles is True and capability_data.get("title"):
            self._attr_name = f"{device.get('name', 'Unknown')} {capability_data.get('title')}"
        elif "." in capability_id:
            # Sub-capability: "alarm_motion.outside" -> "Outside Motion"
            parts = capability_id.split(".")
            base_name = parts[0].replace("alarm_", "").replace("_", " ").title()
            sub_name = parts[1].replace("_", " ").title()
            self._attr_name = f"{device.get('name', 'Unknown')} {sub_name} {base_name}"
        else:
            # Regular capability
            self._attr_name = f"{device.get('name', 'Unknown')} {capability_id.replace('alarm_', '').replace('_', ' ').title()}"
        
        self._attr_unique_id = build_entity_unique_id(
            homey_id, device_id, capability_id, multi_homey
        )
        self._attr_device_class = CAPABILITY_TO_DEVICE_CLASS.get(base_capability)

        self._attr_device_info = get_device_info(
            self._homey_id, device_id, device, zones, self._multi_homey
        )

    @property
    def is_on(self) -> bool:
        """Return true if the binary sensor is on."""
        device_data = self.coordinator.data.get(self._device_id, self._device)
        if not device_data:
            return False
        
        capabilities = device_data.get("capabilitiesObj", {})
        if not capabilities:
            return False
        
        capability = capabilities.get(self._capability_id)
        if not capability:
            return False
        
        value = capability.get("value")
        
        # Handle different value formats
        if value is None:
            return False
        
        # Handle boolean values
        if isinstance(value, bool):
            return value
        
        # Handle string values ("true", "false", "1", "0")
        if isinstance(value, str):
            value_lower = value.lower().strip()
            if value_lower in ("true", "1", "on", "yes"):
                return True
            if value_lower in ("false", "0", "off", "no", ""):
                return False
            # Try to parse as number
            try:
                return bool(int(value))
            except (ValueError, TypeError):
                _LOGGER.warning("Unknown binary sensor value format for %s.%s: %s", self._device_id, self._capability_id, value)
                return False
        
        # Handle numeric values (0/1)
        try:
            return bool(int(value))
        except (ValueError, TypeError):
            return bool(value)

