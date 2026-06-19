"""Support for Homey covers."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.cover import CoverEntity, CoverEntityFeature
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import HomeyDataUpdateCoordinator
from .device_info import build_entity_unique_id, get_device_info

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Homey covers from a config entry."""
    coordinator: HomeyDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    api = hass.data[DOMAIN][entry.entry_id]["api"]
    zones = hass.data[DOMAIN][entry.entry_id].get("zones", {})
    multi_homey = hass.data[DOMAIN][entry.entry_id].get("multi_homey", False)
    homey_id = hass.data[DOMAIN][entry.entry_id].get("homey_id")

    entities = []
    # Use coordinator data if available (more up-to-date), otherwise fetch fresh
    devices = coordinator.data if coordinator.data else await api.get_devices()
    
    # Filter devices if device_filter is configured
    from . import filter_devices
    devices = filter_devices(devices, entry.data.get("device_filter"))

    for device_id, device in devices.items():
        capabilities = device.get("capabilitiesObj", {})
        driver_id = device.get("driverId", "")
        device_name = device.get("name", "Unknown")
        device_class = device.get("class", "")
        
        # Check if this is a devicegroups group
        is_devicegroups_group = driver_id.startswith("homey:app:com.swttt.devicegroups:")
        if is_devicegroups_group:
            _LOGGER.debug(
                "Found devicegroups group in cover platform: %s (id: %s, class: %s, driverId: %s, capabilities: %s)",
                device_name,
                device_id,
                device_class,
                driver_id,
                list(capabilities.keys())
            )
        
        # Special handling for devicegroups groups: respect their class
        # If a group has cover-related class, treat it as a cover
        is_devicegroups_cover = (
            is_devicegroups_group 
            and device_class in ["windowcoverings", "cover", "curtain", "blind", "shutter", "awning", "garagedoor"]
        )
        
        # Support windowcoverings_state, windowcoverings_set, and garagedoor_closed capabilities
        # Reference: https://apps.developer.homey.app/the-basics/devices/capabilities
        # Note: Some devices use windowcoverings_set instead of windowcoverings_state
        # Also support devicegroups groups with cover-related classes
        has_cover_capabilities = any(
            cap in capabilities for cap in ["windowcoverings_state", "windowcoverings_set", "garagedoor_closed"]
        )
        if has_cover_capabilities or is_devicegroups_cover:
            entities.append(HomeyCover(coordinator, device_id, device, api, zones, homey_id, multi_homey))
            if is_devicegroups_group:
                _LOGGER.info(
                    "Created cover entity for devicegroups group: %s (id: %s, has_cover_capabilities=%s)",
                    device_name,
                    device_id,
                    has_cover_capabilities
                )

    async_add_entities(entities)


class HomeyCover(CoordinatorEntity, CoverEntity):
    """Representation of a Homey cover."""

    def __init__(
        self,
        coordinator: HomeyDataUpdateCoordinator,
        device_id: str,
        device: dict[str, Any],
        api,
        zones: dict[str, dict[str, Any]] | None = None,
        homey_id: str | None = None,
        multi_homey: bool = False,
    ) -> None:
        """Initialize the cover."""
        super().__init__(coordinator)
        self._device_id = device_id
        self._device = device
        self._api = api
        self._homey_id = homey_id
        self._multi_homey = multi_homey
        self._attr_name = device.get("name", "Unknown Cover")
        self._attr_unique_id = build_entity_unique_id(
            homey_id, device_id, "cover", multi_homey
        )

        capabilities = device.get("capabilitiesObj", {})
        
        # Check if device uses windowcoverings_state, windowcoverings_set, or garagedoor_closed
        # Some devices use windowcoverings_set instead of windowcoverings_state
        self._windowcoverings_state_cap = "windowcoverings_state" if "windowcoverings_state" in capabilities else None
        self._windowcoverings_set_cap = "windowcoverings_set" if "windowcoverings_set" in capabilities else None
        self._has_windowcoverings = self._windowcoverings_state_cap or self._windowcoverings_set_cap
        self._has_garagedoor = "garagedoor_closed" in capabilities
        # Determine which capability to use for position control
        self._position_cap = self._windowcoverings_set_cap or self._windowcoverings_state_cap
        self._state_capability_data = (
            capabilities.get(self._windowcoverings_state_cap, {}) if self._windowcoverings_state_cap else {}
        )
        
        # Check if windowcoverings_state is enum-based (up/idle/down) or numeric (0-1)
        # windowcoverings_set supports numeric position; windowcoverings_state can be enum or numeric
        self._supports_position = False
        self._is_enum_based = False

        if self._windowcoverings_state_cap:
            state_cap = self._state_capability_data
            # Check if it's an enum type (has "values" array)
            if state_cap.get("type") == "enum" or state_cap.get("values"):
                self._is_enum_based = True
                _LOGGER.debug(
                    "Device %s uses windowcoverings_state (enum) - enum-based control",
                    device_id
                )
            else:
                _LOGGER.debug(
                    "Device %s uses windowcoverings_state (numeric) - supports position control",
                    device_id
                )

        if self._windowcoverings_set_cap:
            # windowcoverings_set always supports numeric position
            self._supports_position = True
            _LOGGER.debug(
                "Device %s uses windowcoverings_set (numeric) - supports position control",
                device_id
            )
        elif self._windowcoverings_state_cap and not self._is_enum_based:
            # Numeric windowcoverings_state supports position
            self._supports_position = True
        
        supported_features = CoverEntityFeature.OPEN | CoverEntityFeature.CLOSE | CoverEntityFeature.STOP
        
        # Only add position feature if device supports numeric position
        # Home Assistant uses SET_POSITION (POSITION doesn't exist in some versions)
        if self._has_windowcoverings and self._supports_position:
            position_feature = (
                getattr(CoverEntityFeature, "SET_POSITION", None)
                or getattr(CoverEntityFeature, "POSITION", None)
            )
            if position_feature is not None:
                supported_features |= position_feature

        if "windowcoverings_tilt_up" in capabilities and "windowcoverings_tilt_down" in capabilities:
            supported_features |= CoverEntityFeature.SET_TILT_POSITION | CoverEntityFeature.OPEN_TILT | CoverEntityFeature.CLOSE_TILT

        self._attr_supported_features = supported_features

        self._attr_device_info = get_device_info(
            self._homey_id, device_id, device, zones, self._multi_homey
        )

    async def _set_enum_cover_state(self, state: str) -> bool:
        """Set enum-based windowcoverings_state if supported."""
        if not self._windowcoverings_state_cap:
            return False
        if not self._is_enum_based:
            return False
        if not self._state_capability_data.get("setable", False):
            return False
        _LOGGER.debug(
            "Setting enum cover state %s to '%s' for device %s",
            self._windowcoverings_state_cap,
            state,
            self._device_id,
        )
        return await self._api.set_capability_value(
            self._device_id, self._windowcoverings_state_cap, state
        )

    @property
    def current_cover_position(self) -> int | None:
        """Return current position of cover."""
        device_data = self.coordinator.data.get(self._device_id, self._device)
        if not device_data:
            return None
        
        capabilities = device_data.get("capabilitiesObj", {})
        if not capabilities:
            return None
        
        # Handle windowcoverings_state, windowcoverings_set, and garagedoor_closed
        if self._has_windowcoverings:
            # Prefer windowcoverings_set for position if available
            position_cap = capabilities.get(self._windowcoverings_set_cap) if self._windowcoverings_set_cap else None
            if position_cap and position_cap.get("value") is not None:
                try:
                    position_value = float(position_cap.get("value"))
                    return int(position_value * 100)
                except (ValueError, TypeError):
                    _LOGGER.warning(
                        "Invalid %s value for device %s: %s",
                        self._windowcoverings_set_cap,
                        self._device_id,
                        position_cap.get("value"),
                    )

            state_cap = capabilities.get(self._windowcoverings_state_cap) if self._windowcoverings_state_cap else None
            if not state_cap:
                return None
            
            state = state_cap.get("value")
            if state is None:
                return None
            
            # Handle enum-based windowcoverings_state (up/idle/down)
            if state_cap.get("type") == "enum" or state_cap.get("values"):
                # Map enum states to positions: "up" = 100%, "down" = 0%, "idle" = 50%
                if state == "up":
                    return 100
                elif state == "down":
                    return 0
                elif state == "idle":
                    return None
                else:
                    # Unknown enum value, return None
                    return None
            
            # Handle numeric position (0-1 range)
            try:
                # Convert state (0-1) to percentage (0-100)
                # windowcoverings_set uses 0-1 range, numeric windowcoverings_state also uses 0-1
                state_float = float(state)
                return int(state_float * 100)
            except (ValueError, TypeError):
                _LOGGER.warning("Invalid %s value for device %s: %s", self._windowcoverings_cap, self._device_id, state)
                return None
        elif self._has_garagedoor:
            # Garage door: closed = True means closed (position 0), False means open (position 100)
            garagedoor_cap = capabilities.get("garagedoor_closed")
            if not garagedoor_cap:
                return None
            
            is_closed = garagedoor_cap.get("value")
            if is_closed is None:
                return None
            
            # Convert boolean to position: True (closed) = 0%, False (open) = 100%
            return 0 if is_closed else 100
        
        return None

    @property
    def is_closed(self) -> bool | None:
        """Return if the cover is closed."""
        position = self.current_cover_position
        if position is None:
            return None
        return position == 0
    
    @property
    def available(self) -> bool:
        """Return if the cover is available."""
        # Entity is available if device exists in coordinator data
        # Position can be None initially, but device should still be available
        device_data = self.coordinator.data.get(self._device_id)
        if device_data is None:
            # Fall back to initial device data
            device_data = self._device
        
        if not device_data:
            return False
        
        # Check if device has cover capabilities
        capabilities = device_data.get("capabilitiesObj", {})
        return any(cap in capabilities for cap in ["windowcoverings_state", "windowcoverings_set", "garagedoor_closed"])

    async def async_open_cover(self, **kwargs: Any) -> None:
        """Open the cover."""
        if self._has_windowcoverings:
            if self._is_enum_based:
                # Prefer enum-based state if supported
                if await self._set_enum_cover_state("up"):
                    await self.coordinator.async_refresh_device(self._device_id)
                    return
            if self._position_cap:
                # Numeric: use 1.0 for open (100%)
                _LOGGER.debug(
                    "Opening cover %s using numeric value 1.0 (capability: %s)",
                    self._device_id,
                    self._position_cap,
                )
                await self._api.set_capability_value(
                    self._device_id, self._position_cap, 1.0
                )
        elif self._has_garagedoor:
            _LOGGER.debug("Opening garage door %s", self._device_id)
            await self._api.set_capability_value(self._device_id, "garagedoor_closed", False)
        else:
            _LOGGER.warning("Device %s does not support opening cover", self._device_id)
            return
        # Immediately refresh this device's state for instant UI feedback
        await self.coordinator.async_refresh_device(self._device_id)

    async def async_close_cover(self, **kwargs: Any) -> None:
        """Close the cover."""
        if self._has_windowcoverings:
            if self._is_enum_based:
                # Prefer enum-based state if supported
                if await self._set_enum_cover_state("down"):
                    await self.coordinator.async_refresh_device(self._device_id)
                    return
            if self._position_cap:
                # Numeric: use 0.0 for close (0%)
                _LOGGER.debug(
                    "Closing cover %s using numeric value 0.0 (capability: %s)",
                    self._device_id,
                    self._position_cap,
                )
                await self._api.set_capability_value(
                    self._device_id, self._position_cap, 0.0
                )
        elif self._has_garagedoor:
            _LOGGER.debug("Closing garage door %s", self._device_id)
            await self._api.set_capability_value(self._device_id, "garagedoor_closed", True)
        else:
            _LOGGER.warning("Device %s does not support closing cover", self._device_id)
            return
        # Immediately refresh this device's state for instant UI feedback
        await self.coordinator.async_refresh_device(self._device_id)

    async def async_stop_cover(self, **kwargs: Any) -> None:
        """Stop the cover."""
        position = None
        if self._has_windowcoverings:
            if self._is_enum_based:
                # Prefer enum-based state if supported
                if await self._set_enum_cover_state("idle"):
                    await self.coordinator.async_refresh_device(self._device_id)
                    return
            if self._position_cap:
                # Numeric: get current position and set it again to stop
                position = self.current_cover_position
                if position is not None:
                    await self._api.set_capability_value(
                        self._device_id, self._position_cap, position / 100.0
                    )
        elif self._has_garagedoor:
            # Some garage doors support stop by re-sending current state
            _LOGGER.debug("Stop requested for garage door %s - no-op", self._device_id)
        # Immediately refresh this device's state for instant UI feedback
        await self.coordinator.async_refresh_device(self._device_id)

    async def async_set_cover_position(self, **kwargs: Any) -> None:
        """Move the cover to a specific position."""
        if not self._supports_position:
            _LOGGER.warning("Device %s does not support setting cover position", self._device_id)
            return
        
        position = kwargs.get("position", 0)
        if self._has_windowcoverings:
            # Only numeric windowcoverings support position setting
            await self._api.set_capability_value(
                self._device_id, self._position_cap, position / 100.0
            )
        elif self._has_garagedoor:
            # Garage doors are binary - convert position to boolean
            # Position > 50% = open (False), <= 50% = closed (True)
            await self._api.set_capability_value(
                self._device_id, "garagedoor_closed", position <= 50
        )
        # Immediately refresh this device's state for instant UI feedback
        await self.coordinator.async_refresh_device(self._device_id)

