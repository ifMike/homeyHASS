"""Support for Homey switches."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import CAPABILITY_TO_PLATFORM, CONF_USE_CAPABILITY_TITLES, DOMAIN
from .coordinator import HomeyDataUpdateCoordinator, HomeyLogicUpdateCoordinator
from .device_info import (
    build_entity_unique_id,
    get_capability_label,
    get_device_info,
    is_legacy_dim_cover,
)
from .button import is_maintenance_button

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Homey switches from a config entry."""
    coordinator: HomeyDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    logic_coordinator: HomeyLogicUpdateCoordinator | None = hass.data[DOMAIN][entry.entry_id].get("logic_coordinator")
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

    _LOGGER.info("Checking %d devices for switch capabilities", len(devices))

    for device_id, device in devices.items():
        capabilities = device.get("capabilitiesObj", {})
        driver_uri = device.get("driverUri")
        driver_id = device.get("driverId", "")
        device_class = device.get("class")
        device_name = device.get("name", "Unknown")
        
        # Check if this is a devicegroups group
        is_devicegroups_group = driver_id.startswith("homey:app:com.swttt.devicegroups:")
        if is_devicegroups_group:
            _LOGGER.debug(
                "Found devicegroups group in switch platform: %s (id: %s, class: %s, driverId: %s)",
                device_name,
                device_id,
                device_class,
                driver_id
            )
        
        # Check for onoff capabilities (both regular and sub-capabilities like onoff.output1)
        # Multi-channel devices (e.g., Shelly Plus 2 PM, Fibaro Double Switch) use sub-capabilities
        onoff_capabilities = []
        
        # Check for regular onoff capability
        if "onoff" in capabilities:
            onoff_capabilities.append("onoff")
        
        # Check for sub-capabilities (onoff.output1, onoff.output2, etc.)
        for cap_id in capabilities:
            if cap_id.startswith("onoff."):
                onoff_capabilities.append(cap_id)
        
        # Track additional boolean capabilities that should be switches
        extra_switch_capabilities = []
        for capability_id, cap_data in capabilities.items():
            # Skip standard onoff (already handled)
            if capability_id in onoff_capabilities or capability_id.startswith("onoff."):
                continue

            # Only settable boolean capabilities are eligible as switches
            if cap_data.get("type") != "boolean" or not cap_data.get("setable"):
                continue

            # Skip capabilities handled by other platforms
            mapped_platform = CAPABILITY_TO_PLATFORM.get(capability_id)
            if mapped_platform and mapped_platform != "switch":
                continue

            # Skip button-like capabilities
            is_button = (
                capability_id == "button"
                or capability_id.startswith("button.")
                or capability_id.endswith("_button")
                or capability_id.startswith("gardena_button.")
            )
            if is_button or is_maintenance_button(capability_id, cap_data):
                continue

            extra_switch_capabilities.append(capability_id)

        # Skip if no switchable capabilities found
        if not onoff_capabilities and not extra_switch_capabilities:
            continue
        
        # Skip if this device should be a light
        has_light_capabilities = (
            "dim" in capabilities
            or "light_hue" in capabilities
            or "light_temperature" in capabilities
            or any(
                cap_id == "lightScenes" or cap_id.startswith("lightScenes.")
                for cap_id in capabilities
            )
        )
        # Skip if this device should be a fan
        has_fan_capabilities = "fan_speed" in capabilities
        # Skip if this device should be a cover
        has_cover_capabilities = any(
            cap in capabilities for cap in ["windowcoverings_state", "windowcoverings_set", "garagedoor_closed"]
        ) or is_legacy_dim_cover(
            capabilities,
            device_class,
            driver_uri,
            driver_id=driver_id,
        )
        # Skip if this device should be a media player
        has_media_capabilities = any(
            cap in capabilities
            for cap in ["volume_set", "speaker_playing", "speaker_next"]
        )
        
        # Special handling for devicegroups groups: respect their class
        # If a group has class "socket" or "switch", treat it as a switch
        is_devicegroups_switch = (
            is_devicegroups_group 
            and device_class in ["socket", "switch"]
        )
            
            # Only create switch if it's not a specialized device type
        # Note: Having sensor capabilities (like measure_power) does NOT exclude switch creation
        # Devices can have both switch and sensor entities
        # Exception: devicegroups groups with class "socket" or "switch" should always be switches
        if is_devicegroups_switch or not (
                has_light_capabilities
                or has_fan_capabilities
                or has_cover_capabilities
                or has_media_capabilities
            ):
            # Create switch entity for each onoff capability
            # For multi-channel devices, this creates multiple switch entities
            for onoff_cap in onoff_capabilities:
                entities.append(
                    HomeySwitch(
                        coordinator,
                        device_id,
                        device,
                        api,
                        zones,
                        onoff_cap,
                        homey_id,
                        multi_homey,
                        use_titles,
                    )
                )
                _LOGGER.info(
                    "Created switch entity for device %s (%s) - capability: %s, driver: %s, class: %s",
                    device_id,
                    device.get("name", "Unknown"),
                    onoff_cap,
                    driver_uri or "unknown",
                    device_class or "unknown"
                )

            # Create switches for other settable boolean capabilities
            for capability_id in extra_switch_capabilities:
                entities.append(
                    HomeySwitch(
                        coordinator,
                        device_id,
                        device,
                        api,
                        zones,
                        capability_id,
                        homey_id,
                        multi_homey,
                        use_titles,
                    )
                )
                _LOGGER.info(
                    "Created switch entity for device %s (%s) - capability: %s, driver: %s, class: %s",
                    device_id,
                    device.get("name", "Unknown"),
                    capability_id,
                    driver_uri or "unknown",
                    device_class or "unknown"
                )
        else:
            _LOGGER.debug(
                "Skipping switch entity for device %s (%s) - has specialized capabilities (light=%s, fan=%s, cover=%s, media=%s)",
                device_id,
                device.get("name", "Unknown"),
                has_light_capabilities,
                has_fan_capabilities,
                has_cover_capabilities,
                has_media_capabilities
            )
    
    _LOGGER.info("Created %d switch entities", len(entities))

    # Add Homey Logic boolean variables (not device capabilities)
    if logic_coordinator:
        logic_variables = (
            logic_coordinator.data
            if logic_coordinator.data is not None
            else await api.get_logic_variables()
        )
        for variable_id, variable in logic_variables.items():
            if variable.get("type") == "boolean":
                entities.append(
                    HomeyLogicSwitch(
                        logic_coordinator,
                        variable_id,
                        variable,
                        api,
                        homey_id,
                        multi_homey,
                    )
                )

    async_add_entities(entities)


class HomeySwitch(CoordinatorEntity, SwitchEntity):
    """Representation of a Homey switch."""

    def __init__(
        self,
        coordinator: HomeyDataUpdateCoordinator,
        device_id: str,
        device: dict[str, Any],
        api,
        zones: dict[str, dict[str, Any]] | None = None,
        onoff_capability: str = "onoff",
        homey_id: str | None = None,
        multi_homey: bool = False,
        use_titles: bool | None = None,
    ) -> None:
        """Initialize the switch.
        
        Args:
            coordinator: Data update coordinator
            device_id: Homey device ID
            device: Device data dictionary
            api: Homey API instance
            zones: Zones dictionary (optional)
            onoff_capability: The onoff capability ID (default: "onoff", can be "onoff.output1", etc.)
        """
        super().__init__(coordinator)
        self._device_id = device_id
        self._device = device
        self._api = api
        self._onoff_capability = onoff_capability
        self._homey_id = homey_id
        self._multi_homey = multi_homey
        
        # Create entity name based on capability
        device_name = device.get("name", "Unknown Switch")
        if onoff_capability == "onoff":
            self._attr_name = device_name
        elif onoff_capability.startswith("onoff."):
            # Extract channel name from capability (e.g., "onoff.output1" -> "Output 1")
            channel = onoff_capability.replace("onoff.", "").replace("_", " ").title()
            self._attr_name = f"{device_name} {channel}"
        else:
            capability_label = get_capability_label(
                onoff_capability,
                device.get("capabilitiesObj", {}).get(onoff_capability, {}),
                use_titles,
                legacy_uses_title=True,
            )
            self._attr_name = f"{device_name} {capability_label}"
        
        # Create unique ID based on capability
        if onoff_capability == "onoff":
            self._attr_unique_id = build_entity_unique_id(
                homey_id, device_id, "onoff", multi_homey
            )
        else:
            # Use capability ID in unique_id (e.g., "homey_{device_id}_onoff.output1")
            self._attr_unique_id = build_entity_unique_id(
                homey_id, device_id, onoff_capability, multi_homey
            )
        
        self._attr_device_info = get_device_info(
            self._homey_id, device_id, device, zones, self._multi_homey
        )

    @property
    def is_on(self) -> bool | None:
        """Return true if switch is on."""
        device_data = self.coordinator.data.get(self._device_id, self._device)
        if not device_data:
            return None
        
        capabilities = device_data.get("capabilitiesObj", {})
        onoff_cap = capabilities.get(self._onoff_capability)
        if not onoff_cap:
            return None
        
        return onoff_cap.get("value", False)

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the switch on."""
        await self._api.set_capability_value(self._device_id, self._onoff_capability, True)
        # Immediately refresh this device's state for instant UI feedback
        await self.coordinator.async_refresh_device(self._device_id)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the switch off."""
        await self._api.set_capability_value(self._device_id, self._onoff_capability, False)
        # Immediately refresh this device's state for instant UI feedback
        await self.coordinator.async_refresh_device(self._device_id)

    @property
    def available(self) -> bool:
        """Return if the switch is available."""
        device_data = self.coordinator.data.get(self._device_id)
        if device_data is None:
            device_data = self._device
        
        if not device_data:
            return False
        
        capabilities = device_data.get("capabilitiesObj", {})
        return self._onoff_capability in capabilities


class HomeyLogicSwitch(CoordinatorEntity, SwitchEntity):
    """Representation of a Homey logic boolean variable."""

    def __init__(
        self,
        coordinator: HomeyLogicUpdateCoordinator,
        variable_id: str,
        variable: dict[str, Any],
        api,
        homey_id: str | None = None,
        multi_homey: bool = False,
    ) -> None:
        """Initialize the logic switch entity."""
        super().__init__(coordinator)
        self._variable_id = variable_id
        self._variable = variable
        self._api = api
        self._homey_id = homey_id
        self._multi_homey = multi_homey

        variable_name = variable.get("name", "Logic Boolean")
        self._attr_name = variable_name
        self._attr_unique_id = build_entity_unique_id(
            homey_id, "logic", f"boolean_{variable_id}", multi_homey
        )

        logic_identifier = f"{homey_id}:logic" if (multi_homey and homey_id) else "logic"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, logic_identifier)},
            "name": "Homey Logic",
            "manufacturer": "Athom",
            "model": "Homey",
        }

    @property
    def is_on(self) -> bool | None:
        """Return true if the variable is on."""
        variables = self.coordinator.data or {}
        variable = variables.get(self._variable_id, self._variable)
        value = variable.get("value")
        if value is None:
            return None
        return bool(value)

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the logic boolean on."""
        success = await self._api.update_logic_variable(self._variable_id, True)
        if success:
            await self.coordinator.async_request_refresh()
        else:
            _LOGGER.error("Failed to set logic variable %s to True", self._variable_id)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the logic boolean off."""
        success = await self._api.update_logic_variable(self._variable_id, False)
        if success:
            await self.coordinator.async_request_refresh()
        else:
            _LOGGER.error("Failed to set logic variable %s to False", self._variable_id)
