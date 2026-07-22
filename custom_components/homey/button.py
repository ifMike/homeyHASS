"""Support for Homey flows and physical device buttons."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import CAPABILITY_TO_PLATFORM, DOMAIN, UNIQUE_ID_PREFIX, capability_base
from .coordinator import HomeyDataUpdateCoordinator
from .device_info import build_entity_unique_id, format_capability_label, get_device_info

_LOGGER = logging.getLogger(__name__)


def is_maintenance_button(capability_id: str, capability_obj: dict[str, Any]) -> bool:
    """Check if a button capability is a maintenance action.
    
    Reference: https://apps.developer.homey.app/the-basics/devices/capabilities#maintenance-actions
    
    Args:
        capability_id: The capability ID (e.g., "button.identify", "button.reset_meter")
        capability_obj: The capability object from capabilitiesObj
        
    Returns:
        True if this is a maintenance button that should be excluded
    """
    # Check maintenanceAction property first (most reliable)
    if capability_obj.get("maintenanceAction", False):
        return True
    
    # Fallback: Check capability name for maintenance keywords
    capability_lower = capability_id.lower()
    maintenance_keywords = [
        "migrate", "migration", "migrate_v3",
        "reset", "reset_meter",
        "identify",
        "calibrate", "calibration",
        "maintenance", "repair", "service",
    ]
    return any(keyword in capability_lower for keyword in maintenance_keywords)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Homey flow buttons and physical device buttons from a config entry."""
    coordinator: HomeyDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    api = hass.data[DOMAIN][entry.entry_id]["api"]
    zones = hass.data[DOMAIN][entry.entry_id].get("zones", {})
    multi_homey = hass.data[DOMAIN][entry.entry_id].get("multi_homey", False)
    homey_id = hass.data[DOMAIN][entry.entry_id].get("homey_id")
    
    # Clean up existing maintenance button entities from entity registry
    # This removes entities that were created before filtering was added
    from homeassistant.helpers import entity_registry as er
    entity_registry = er.async_get(hass)
    
    # Get devices to check capabilities
    devices = coordinator.data if coordinator.data else await api.get_devices()
    from . import filter_devices
    devices = filter_devices(devices, entry.data.get("device_filter"))
    
    # Get all button entities for this integration and remove maintenance buttons
    # This removes entities that were created before filtering was added
    maintenance_buttons_removed = 0
    maintenance_keywords = ["migrate", "migration", "identify", "reset", "calibrate"]
    
    for entity_entry in list(entity_registry.entities.values()):
        # Check if this is a button entity from our integration
        if entity_entry.platform == DOMAIN and entity_entry.domain == "button":
            unique_id = entity_entry.unique_id
            entity_id = entity_entry.entity_id
            
            # Simple check: if entity name or unique_id contains maintenance keywords, remove it
            entity_lower = entity_id.lower()
            unique_id_lower = (unique_id or "").lower()
            
            # Check entity name (e.g., "Hue ambiance spot 1 Migrate V3 Button")
            if any(keyword in entity_lower for keyword in maintenance_keywords):
                entity_registry.async_remove(entity_entry.entity_id)
                maintenance_buttons_removed += 1
                _LOGGER.info("Removed maintenance button entity by name: %s", entity_entry.entity_id)
                continue
            
            # Also check unique_id for maintenance button patterns
            # Format: "homey_{device_id}_{capability_id}"
            # Example: "homey_011cf5be-2522-45b5-b40f-0fdbfab64fb4_button.migrate_v3"
            if unique_id and unique_id.startswith(UNIQUE_ID_PREFIX) and "_button" in unique_id:
                # Check unique_id for maintenance keywords
                if any(keyword in unique_id_lower for keyword in maintenance_keywords):
                    entity_registry.async_remove(entity_entry.entity_id)
                    maintenance_buttons_removed += 1
                    _LOGGER.info("Removed maintenance button entity by unique_id: %s", entity_entry.entity_id)
                    continue
                
                # Also try to parse and check capability object
                try:
                    # Split at "_button" to separate device_id from capability_id
                    parts = unique_id.split("_button", 1)
                    if len(parts) == 2:
                        device_id_with_prefix = parts[0]
                        capability_suffix = parts[1]  # ".migrate_v3"
                        
                        # Extract device_id (remove integration prefix)
                        if device_id_with_prefix.startswith(UNIQUE_ID_PREFIX):
                            device_id = device_id_with_prefix[len(UNIQUE_ID_PREFIX):]
                            capability_id = f"button{capability_suffix}"  # "button.migrate_v3"
                            
                            # Check if device exists and capability is maintenance
                            if device_id in devices:
                                device = devices[device_id]
                                capabilities = device.get("capabilitiesObj", {})
                                capability_obj = capabilities.get(capability_id, {})
                                
                                if is_maintenance_button(capability_id, capability_obj):
                                    entity_registry.async_remove(entity_entry.entity_id)
                                    maintenance_buttons_removed += 1
                                    _LOGGER.info("Removed maintenance button entity by capability check: %s (%s)", entity_entry.entity_id, capability_id)
                except Exception as err:
                    _LOGGER.debug("Error checking entity %s for maintenance button: %s", unique_id, err)
                    continue
    
    if maintenance_buttons_removed > 0:
        _LOGGER.info("Cleaned up %d existing maintenance button entities", maintenance_buttons_removed)

    entities = []
    flow_buttons_count = 0
    device_buttons_count = 0
    
    # Add flow buttons
    flows = await api.get_flows()
    total_flows = len(flows)
    enabled_flows = 0
    disabled_flows = 0
    
    # Empty flows dict is OK - user just doesn't have flows configured or doesn't have permission
    # Permission errors are already logged by the API method
    if flows:
        _LOGGER.debug("Found %d flows from Homey", total_flows)
        for flow_id, flow in flows.items():
            flow_name = flow.get("name", "Unknown")
            flow_enabled = flow.get("enabled", False)
            if flow_enabled:
                enabled_flows += 1
                entities.append(HomeyFlowButton(coordinator, flow_id, flow, api, homey_id, multi_homey))
                flow_buttons_count += 1
                _LOGGER.debug("Added flow button: %s (enabled)", flow_name)
            else:
                disabled_flows += 1
                _LOGGER.debug("Skipping flow: %s (disabled)", flow_name)
        
        if enabled_flows == 0 and total_flows > 0:
            _LOGGER.warning(
                "Found %d flows in Homey, but none are enabled. Enable flows in Homey to use them in Home Assistant.",
                total_flows
            )
    else:
        _LOGGER.debug("No flows found from Homey API")
    
    # Add physical device buttons
    devices = coordinator.data if coordinator.data else await api.get_devices()
    from . import filter_devices
    devices = filter_devices(devices, entry.data.get("device_filter"))
    
    for device_id, device in devices.items():
        capabilities = device.get("capabilitiesObj", {})
        # Check for button capabilities:
        # - Standard: button, button.1, button.2, etc.
        # - Device-specific: gardena_button.park, gardena_button.start, etc.
        # Exclude internal Homey maintenance capabilities that shouldn't be exposed as buttons
        # Reference: https://apps.developer.homey.app/the-basics/devices/capabilities#maintenance-actions
        for capability_id in capabilities:
            capability_obj = capabilities.get(capability_id, {})
            
            # Check if this is a button capability
            is_button = (
                capability_id == "button" or 
                capability_id.startswith("button.") or
                capability_id.endswith("_button") or
                capability_id.endswith("_button.park") or
                capability_id.endswith("_button.start") or
                (capability_id.startswith("gardena_button.") and capability_obj.get("setable"))
                or CAPABILITY_TO_PLATFORM.get(capability_id) == "button"
                or CAPABILITY_TO_PLATFORM.get(capability_base(capability_id)) == "button"
            )
            
            if is_button:
                # Skip maintenance action buttons
                if is_maintenance_button(capability_id, capability_obj):
                    _LOGGER.debug("Skipping maintenance action button: %s", capability_id)
                    continue
                
                # Only add settable button capabilities
                if capability_obj.get("setable"):
                    entities.append(HomeyDeviceButton(coordinator, device_id, device, capability_id, api, zones, homey_id, multi_homey))
                    device_buttons_count += 1

    if entities:
        _LOGGER.info(
            "Created %d Homey button entities (%d flow buttons from %d total flows, %d device buttons)",
            len(entities), flow_buttons_count, total_flows, device_buttons_count
        )
    else:
        _LOGGER.info("No Homey button entities created (flows: %d total, %d enabled; device buttons: %d)", 
                     total_flows, enabled_flows, device_buttons_count)
    
    async_add_entities(entities)


class HomeyFlowButton(CoordinatorEntity, ButtonEntity):
    """Representation of a Homey flow as a Home Assistant button."""

    def __init__(
        self,
        coordinator: HomeyDataUpdateCoordinator,
        flow_id: str,
        flow: dict[str, Any],
        api,
        homey_id: str | None = None,
        multi_homey: bool = False,
    ) -> None:
        """Initialize the button."""
        super().__init__(coordinator)
        self._flow_id = flow_id
        self._flow = flow
        self._api = api
        self._homey_id = homey_id
        self._multi_homey = multi_homey
        self._attr_name = flow.get("name", "Unknown Flow")
        self._attr_unique_id = build_entity_unique_id(
            homey_id, flow_id, "flow", multi_homey
        )
        self._attr_icon = "mdi:play-circle-outline"

        flows_identifier = f"{homey_id}:flows" if (multi_homey and homey_id) else "flows"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, flows_identifier)},
            "name": "Homey Flows",
            "manufacturer": "Athom",
            "model": "Homey",
        }

    async def async_press(self) -> None:
        """Handle the button press - trigger the Homey flow."""
        success = await self._api.trigger_flow(self._flow_id)
        if not success:
            _LOGGER.error("Failed to trigger Homey flow: %s", self._attr_name)


class HomeyDeviceButton(CoordinatorEntity, ButtonEntity):
    """Representation of a physical device button."""

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
    ) -> None:
        """Initialize the device button."""
        super().__init__(coordinator)
        self._device_id = device_id
        self._device = device
        self._capability_id = capability_id
        self._api = api
        self._homey_id = homey_id
        self._multi_homey = multi_homey
        
        # Create button name
        device_name = device.get("name", "Unknown Device")
        capability_obj = device.get("capabilitiesObj", {}).get(capability_id, {})
        if capability_id == "button":
            button_name = f"{device_name} Button"
        elif capability_id.startswith("button."):
            # Extract button number (e.g., "button.1" -> "1")
            button_num = capability_id.replace("button.", "")
            button_name = f"{device_name} Button {button_num}"
        else:
            label = capability_obj.get("title") or format_capability_label(capability_id)
            button_name = f"{device_name} {label}"
        
        self._attr_name = button_name
        self._attr_unique_id = build_entity_unique_id(
            homey_id, device_id, capability_id, multi_homey
        )
        self._attr_icon = "mdi:gesture-tap-button"
        
        self._attr_device_info = get_device_info(
            self._homey_id, device_id, device, zones, self._multi_homey
        )

    async def async_press(self) -> None:
        """Handle the button press - trigger the button capability."""
        # Set button capability to True to trigger the button press
        success = await self._api.set_capability_value(self._device_id, self._capability_id, True)
        if not success:
            _LOGGER.error("Failed to trigger button %s on device %s", self._capability_id, self._device_id)
        else:
            # Immediately refresh device state
            await self.coordinator.async_refresh_device(self._device_id)

