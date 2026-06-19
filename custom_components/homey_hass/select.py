"""Support for Homey select entities."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.select import SelectEntity, SelectEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import CONF_USE_CAPABILITY_TITLES, DOMAIN
from .coordinator import HomeyDataUpdateCoordinator
from .device_info import build_entity_unique_id, get_capability_label, get_device_info

_LOGGER = logging.getLogger(__name__)

# Capabilities that should be exposed as select entities
# These are mode/option selections
SELECT_CAPABILITIES = [
    # Add capabilities here that have options/modes
    # Example: "thermostat_mode" is handled by climate platform
    # "some_mode": {"options": ["option1", "option2", "option3"]},
    "operating_program",  # Heat pump operating program
]


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Homey select entities from a config entry."""
    coordinator: HomeyDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    api = hass.data[DOMAIN][entry.entry_id]["api"]
    zones = hass.data[DOMAIN][entry.entry_id].get("zones", {})
    multi_homey = hass.data[DOMAIN][entry.entry_id].get("multi_homey", False)
    homey_id = hass.data[DOMAIN][entry.entry_id].get("homey_id")

    entities = []
    use_titles = entry.options.get(
        CONF_USE_CAPABILITY_TITLES, entry.data.get(CONF_USE_CAPABILITY_TITLES)
    )
    devices = coordinator.data if coordinator.data else await api.get_devices()
    
    # Filter devices if device_filter is configured
    from . import filter_devices
    devices = filter_devices(devices, entry.data.get("device_filter"))

    for device_id, device in devices.items():
        capabilities = device.get("capabilitiesObj", {})
        
        # First, check explicitly listed select capabilities
        for capability_id in SELECT_CAPABILITIES:
            if capability_id in capabilities:
                cap_data = capabilities[capability_id]
                # Check if capability has options/values (enum type)
                if "values" in cap_data or "options" in cap_data or cap_data.get("type") == "enum":
                    entities.append(
                        HomeySelect(
                            coordinator,
                            device_id,
                            device,
                            capability_id,
                            cap_data,
                            api,
                            zones,
                            homey_id,
                            multi_homey,
                            use_titles,
                        )
                    )
        
        # Then, handle ALL enum-type capabilities generically (including unknown ones)
        # This ensures we support new enum capabilities automatically
        for capability_id, cap_data in capabilities.items():
            # Skip if already handled above
            if capability_id in SELECT_CAPABILITIES:
                continue
            
            # Check if this is an enum-type capability
            if cap_data.get("type") in ("enum", "string") and ("values" in cap_data or "options" in cap_data):
                # Skip internal Homey maintenance buttons
                capability_lower = capability_id.lower()
                if any(keyword in capability_lower for keyword in ["migrate", "reset", "identify"]):
                    _LOGGER.debug("Skipping internal Homey maintenance enum capability: %s", capability_id)
                    continue
                
                # Skip windowcoverings_state - it's handled by the cover platform, not select
                # windowcoverings_state can be enum-based (up/idle/down) but should be a cover entity, not select
                if capability_id == "windowcoverings_state":
                    _LOGGER.debug("Skipping windowcoverings_state enum capability - handled by cover platform: %s", device_id)
                    continue
                
                entities.append(
                    HomeySelect(
                        coordinator,
                        device_id,
                        device,
                        capability_id,
                        cap_data,
                        api,
                        zones,
                        homey_id,
                        multi_homey,
                        use_titles,
                    )
                )

    async_add_entities(entities)


class HomeySelect(CoordinatorEntity, SelectEntity):
    """Representation of a Homey select entity."""

    def __init__(
        self,
        coordinator: HomeyDataUpdateCoordinator,
        device_id: str,
        device: dict[str, Any],
        capability_id: str,
        capability_data: dict[str, Any],
        api,
        zones: dict[str, dict[str, Any]] | None = None,
        homey_id: str | None = None,
        multi_homey: bool = False,
        use_titles: bool | None = None,
    ) -> None:
        """Initialize the select entity."""
        super().__init__(coordinator)
        self._device_id = device_id
        self._device = device
        self._capability_id = capability_id
        self._capability_data = capability_data
        self._api = api
        self._homey_id = homey_id
        self._multi_homey = multi_homey
        
        device_name = device.get("name", "Unknown Device")
        capability_label = get_capability_label(
            capability_id, capability_data, use_titles, legacy_uses_title=True
        )
        self._attr_name = f"{device_name} {capability_label}"
        self._attr_unique_id = build_entity_unique_id(
            homey_id, device_id, capability_id, multi_homey
        )
        
        # Get options from capability data
        # Enum capabilities have "values" array with objects like {"id": "VERY_CHEAP", "title": "VERY_CHEAP"}
        # or simple string arrays
        options = capability_data.get("values") or capability_data.get("options", [])
        if isinstance(options, list):
            if len(options) > 0 and isinstance(options[0], dict):
                # Extract IDs from enum value objects
                self._attr_options = [str(opt.get("id", opt.get("title", opt))) for opt in options]
            else:
                # Simple string array
                self._attr_options = [str(opt) for opt in options]
        elif isinstance(options, dict):
            # If it's a dict, use the keys or values
            self._attr_options = [str(opt) for opt in options.keys()]
        else:
            self._attr_options = []
        
        self._attr_device_info = get_device_info(
            self._homey_id, device_id, device, zones, self._multi_homey
        )

    @property
    def current_option(self) -> str | None:
        """Return the currently selected option."""
        device_data = self.coordinator.data.get(self._device_id, self._device)
        capabilities = device_data.get("capabilitiesObj", {})
        value = capabilities.get(self._capability_id, {}).get("value")
        if value is not None:
            # For enum types, value might be a string (the ID) or an object
            if isinstance(value, dict):
                # If it's an object, extract the ID
                return str(value.get("id", value.get("title", value)))
            return str(value)
        return None

    async def async_select_option(self, option: str) -> None:
        """Change the selected option."""
        success = await self._api.set_capability_value(self._device_id, self._capability_id, option)
        if success:
            _LOGGER.debug("Successfully set %s to %s for device %s", self._capability_id, option, self._device_id)
            await self.coordinator.async_refresh_device(self._device_id)
        else:
            _LOGGER.error("Failed to set %s to %s for device %s", self._capability_id, option, self._device_id)
