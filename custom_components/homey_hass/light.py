"""Support for Homey lights."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.light import (
    ATTR_BRIGHTNESS,
    ATTR_COLOR_TEMP_KELVIN,
    ATTR_EFFECT,
    ATTR_HS_COLOR,
    ColorMode,
    LightEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
import homeassistant.util.color as color_util

from .const import CONF_INVERT_LIGHT_TEMPERATURE, DOMAIN, DEFAULT_INVERT_LIGHT_TEMPERATURE
from .coordinator import HomeyDataUpdateCoordinator
from .device_info import build_entity_unique_id, get_device_info

_LOGGER = logging.getLogger(__name__)

# Module loaded - no need to log this on every restart


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Homey lights from a config entry."""
    _LOGGER.info("Setting up Homey lights platform")
    coordinator: HomeyDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    api = hass.data[DOMAIN][entry.entry_id]["api"]
    zones = hass.data[DOMAIN][entry.entry_id].get("zones", {})
    multi_homey = hass.data[DOMAIN][entry.entry_id].get("multi_homey", False)
    homey_id = hass.data[DOMAIN][entry.entry_id].get("homey_id")
    invert_temp = entry.options.get(
        CONF_INVERT_LIGHT_TEMPERATURE,
        entry.data.get(CONF_INVERT_LIGHT_TEMPERATURE, DEFAULT_INVERT_LIGHT_TEMPERATURE),
    )

    entities = []
    # Use coordinator data if available (more up-to-date), otherwise fetch fresh
    devices = coordinator.data if coordinator.data else await api.get_devices()
    
    # Filter devices if device_filter is configured
    from . import filter_devices
    devices = filter_devices(devices, entry.data.get("device_filter"))
    
    _LOGGER.info("Found %d devices to check for light capabilities", len(devices))

    for device_id, device in devices.items():
        capabilities = device.get("capabilitiesObj", {})
        driver_uri = device.get("driverUri", "").lower()
        driver_id = device.get("driverId", "")
        device_name = device.get("name", "Unknown")
        device_class = device.get("class", "")
        
        # Check if this is a devicegroups group
        is_devicegroups_group = driver_id.startswith("homey:app:com.swttt.devicegroups:")
        if is_devicegroups_group:
            _LOGGER.debug(
                "Found devicegroups group in light platform: %s (id: %s, class: %s, driverId: %s, capabilities: %s)",
                device_name,
                device_id,
                device_class,
                driver_id,
                list(capabilities.keys())
            )
        
        # Check if device has light-related capabilities
        # A device is a light if it has onoff AND at least one of: dim, light_hue, light_temperature
        # Note: light_hue requires light_saturation for full color support, but we check for light_hue alone
        # to catch devices that might have color capabilities even if saturation isn't exposed
        has_onoff = "onoff" in capabilities
        has_dim = "dim" in capabilities
        has_hue = "light_hue" in capabilities
        has_saturation = "light_saturation" in capabilities
        has_temp = "light_temperature" in capabilities
        has_scenes = any(
            cap_id == "lightScenes" or cap_id.startswith("lightScenes.")
            for cap_id in capabilities
        )
        
        # Device-specific detection: Some devices are known to be lights even if capabilities aren't fully exposed
        is_known_light_device = False
        if driver_uri:
            # Philips Hue devices - should be lights if they have onoff
            # White & Ambiance bulbs have: onoff + dim + light_temperature
            # White & Color Ambiance bulbs have: onoff + dim + light_hue + light_saturation
            if "philips" in driver_uri and "hue" in driver_uri:
                if has_onoff:
                    is_known_light_device = True
                    _LOGGER.debug(
                        "Detected Philips Hue device %s (%s) - treating as light (driver: %s, dim=%s, temp=%s, hue=%s)",
                        device_id, device_name, device.get("driverUri", "unknown"), has_dim, has_temp, has_hue
                    )
        
        # Also check for generic devices with dim capability (e.g., generic Zigbee dimmers)
        # Devices with class "socket" but having dim capability should be lights, not switches
        device_class = device.get("class", "").lower()
        is_generic_dimmable = (
            has_onoff and has_dim and 
            (device_class in ["socket", "other"] or not device_class)
        )
        
        # Sunricher dimming devices - should be lights if they have onoff
        # Even if dim isn't exposed, if it's a Sunricher dimmer, treat as light
        if driver_uri and "sunricher" in driver_uri:
            if has_onoff:
                is_known_light_device = True
                _LOGGER.debug(
                    "Detected Sunricher dimming device %s (%s) - treating as light (driver: %s, dim=%s)",
                    device_id, device_name, device.get("driverUri", "unknown"), has_dim
                )
        
        # Special handling for devicegroups groups: respect their class
        # If a group has class "light", treat it as a light even if capabilities are minimal
        is_devicegroups_light = (
            is_devicegroups_group 
            and device_class == "light" 
            and has_onoff
        )
        
        # Create light entity if:
        # 1. Has onoff AND (dim OR hue OR temp) - standard light detection
        #    This catches devices with class "socket" that have light capabilities (e.g., Philips Hue)
        # 2. OR is a known light device type (device-specific detection)
        # 3. OR is a generic dimmable device (onoff + dim, regardless of class)
        # 4. OR is a devicegroups group with class "light" (respect group class)
        # Note: Even if capabilities aren't fully exposed, we create the light entity
        # and let the entity class determine supported features based on available capabilities
        # 
        # IMPORTANT: Devices with class "socket" but having dim/color capabilities should be lights, not switches
        # The switch platform will skip them if has_light_capabilities is True
        is_light = (
            (has_onoff and (has_dim or has_hue or has_temp or has_scenes))
            or is_known_light_device 
            or is_generic_dimmable
            or is_devicegroups_light
        )
        
        if is_light:
            _LOGGER.debug(
                "Creating light entity for device %s (%s) - class=%s, onoff=%s, dim=%s, hue=%s, temp=%s",
                device_id, device_name, device_class or "none", has_onoff, has_dim, has_hue, has_temp,
            )
            entities.append(HomeyLight(coordinator, device_id, device, api, zones, invert_temp, homey_id, multi_homey))
        else:
            # Log why device was NOT detected as light (for debugging)
            if has_onoff:
                _LOGGER.debug(
                    "Device %s (%s) has onoff but not detected as light - class=%s, dim=%s, hue=%s, temp=%s",
                    device_id, device_name, device_class or "none", has_dim, has_hue, has_temp
                )

    _LOGGER.debug("Created %d Homey light entities", len(entities))
    async_add_entities(entities)


class HomeyLight(CoordinatorEntity, LightEntity):
    """Representation of a Homey light."""

    def __init__(
        self,
        coordinator: HomeyDataUpdateCoordinator,
        device_id: str,
        device: dict[str, Any],
        api,
        zones: dict[str, dict[str, Any]] | None = None,
        invert_temp: bool = True,
        homey_id: str | None = None,
        multi_homey: bool = False,
    ) -> None:
        """Initialize the light."""
        super().__init__(coordinator)
        self._device_id = device_id
        self._device = device
        self._api = api
        self._invert_temp = invert_temp
        self._homey_id = homey_id
        self._multi_homey = multi_homey
        self._attr_name = device.get("name", "Unknown Light")
        self._attr_unique_id = build_entity_unique_id(
            homey_id, device_id, "light", multi_homey
        )

        capabilities = device.get("capabilitiesObj", {})
        # Determine supported color modes
        color_modes = set()
        has_dim = "dim" in capabilities
        # Check for hue and saturation - both are needed for full HS color support
        # Some devices might have hue without saturation, but we'll treat that as HS mode anyway
        has_hue = "light_hue" in capabilities
        has_saturation = "light_saturation" in capabilities
        has_hs = has_hue and has_saturation
        has_temp = "light_temperature" in capabilities
        self._scene_capability = next(
            (
                cap_id
                for cap_id in ("lightScenes.light", "lightScenes")
                if cap_id in capabilities
            ),
            None,
        )
        has_light_mode = "light_mode" in capabilities
        self._has_light_mode = has_light_mode
        
        # Log all capabilities found for debugging
        _LOGGER.debug(
            "Device %s (%s) light capabilities: dim=%s, hue=%s, saturation=%s, temp=%s",
            device_id,
            device.get("name", "Unknown"),
            has_dim,
            has_hue,
            has_saturation,
            has_temp
        )
        
        # Determine color modes based on available capabilities
        # Expose both HS and COLOR_TEMP when available so HA can switch modes.
        if has_temp:
            color_modes.add(ColorMode.COLOR_TEMP)
        if has_hs or has_hue:
            # Use HS if full HS support or hue-only devices (saturation may be implicit)
            color_modes.add(ColorMode.HS)

        if color_modes:
            _LOGGER.debug(
                "Device %s (%s) supports color modes: %s",
                device_id,
                device.get("name", "Unknown"),
                color_modes,
            )
        elif has_dim:
            # Only dimming available (dimmable lights without color or temperature)
            color_modes.add(ColorMode.BRIGHTNESS)
            _LOGGER.debug(
                "Device %s (%s) supports BRIGHTNESS mode only",
                device_id,
                device.get("name", "Unknown"),
            )
        else:
            # Just on/off - this can happen for known light devices where capabilities aren't fully exposed
            # We still create a light entity but with limited functionality
            _LOGGER.debug(
                "Device %s (%s) created as light but has no dim/hue/temp capabilities - using ONOFF mode only",
                device_id,
                device.get("name", "Unknown")
            )
            color_modes.add(ColorMode.ONOFF)

        self._attr_supported_color_modes = color_modes
        if ColorMode.HS in color_modes and ColorMode.COLOR_TEMP in color_modes:
            light_mode_value = capabilities.get("light_mode", {}).get("value")
            if light_mode_value == "temperature":
                self._attr_color_mode = ColorMode.COLOR_TEMP
            else:
                self._attr_color_mode = ColorMode.HS
        else:
            self._attr_color_mode = next(iter(color_modes)) if color_modes else ColorMode.ONOFF
        
        _LOGGER.debug(
            "Light %s (%s) initialized - dim=%s, hs=%s, temp=%s - color_modes=%s",
            device_id, device.get("name", "Unknown"), has_dim, has_hs, has_temp, color_modes,
        )
        
        # Set color temperature range in Kelvin (required for COLOR_TEMP mode)
        if ColorMode.COLOR_TEMP in color_modes:
            temp_cap = capabilities.get("light_temperature", {})
            temp_min = temp_cap.get("min", 0)
            temp_max = temp_cap.get("max", 1)
            
            # Check if temperature is normalized (0-1) or in Kelvin
            # If min=0 and max=1, it's normalized - convert to Kelvin range
            # Typical range: 0 = 2000K (warm), 1 = 6500K (cool)
            if temp_min == 0 and temp_max == 1:
                # Normalized range - convert to Kelvin
                self._attr_min_color_temp_kelvin = 2000  # Warm white
                self._attr_max_color_temp_kelvin = 6500  # Cool white
                _LOGGER.debug(
                    "Device %s (%s) has normalized light_temperature (0-1), converting to Kelvin range 2000-6500K",
                    device_id, device.get("name", "Unknown")
                )
            else:
                # Already in Kelvin (or different range)
                self._attr_min_color_temp_kelvin = int(temp_min)
                self._attr_max_color_temp_kelvin = int(temp_max)
                _LOGGER.debug(
                    "Device %s (%s) has light_temperature in Kelvin range %d-%dK",
                    device_id, device.get("name", "Unknown"), 
                    self._attr_min_color_temp_kelvin, self._attr_max_color_temp_kelvin
                )

        self._attr_device_info = get_device_info(
            self._homey_id, device_id, device, zones, self._multi_homey
        )

    async def async_added_to_hass(self) -> None:
        """When entity is added to Home Assistant, ensure we have fresh data."""
        await super().async_added_to_hass()
        # Trigger a refresh to ensure we have the latest device state
        # This helps fix stale color values on initial load
        if self.coordinator.data and self._device_id in self.coordinator.data:
            # Coordinator has data, but refresh this specific device to ensure it's current
            await self.coordinator.async_refresh_device(self._device_id)
        elif not self.coordinator.data:
            # Coordinator doesn't have data yet, request a refresh
            await self.coordinator.async_request_refresh()

    @property
    def is_on(self) -> bool:
        """Return true if light is on."""
        device_data = self.coordinator.data.get(self._device_id, self._device)
        capabilities = device_data.get("capabilitiesObj", {})
        return capabilities.get("onoff", {}).get("value", False)

    @property
    def supported_color_modes(self) -> set[ColorMode]:
        """Return the supported color modes."""
        # Removed excessive logging - only log on first query or if needed for debugging
        return self._attr_supported_color_modes
    
    @property
    def color_mode(self) -> ColorMode:
        """Return the current color mode."""
        # Removed excessive logging - only log on first query or if needed for debugging
        return self._attr_color_mode

    @property
    def brightness(self) -> int | None:
        """Return the brightness of the light."""
        device_data = self.coordinator.data.get(self._device_id, self._device)
        capabilities = device_data.get("capabilitiesObj", {})
        dim_value = capabilities.get("dim", {}).get("value", 0)
        if dim_value is not None:
            try:
                return int(float(dim_value) * 255)
            except (ValueError, TypeError):
                return None
        return None

    @property
    def hs_color(self) -> tuple[float, float] | None:
        """Return the hue and saturation color value."""
        # Always prefer coordinator data (most up-to-date)
        # Only fall back to self._device if coordinator data is not available
        if self.coordinator.data and self._device_id in self.coordinator.data:
            device_data = self.coordinator.data[self._device_id]
        else:
            # Coordinator data not available yet - use initial device data
            # This should rarely happen as coordinator should be populated before entities are created
            device_data = self._device
        
        capabilities = device_data.get("capabilitiesObj", {})
        hue_normalized = capabilities.get("light_hue", {}).get("value")
        saturation_normalized = capabilities.get("light_saturation", {}).get("value")
        
        if hue_normalized is not None and saturation_normalized is not None:
            # Homey returns normalized values (0-1), convert to Home Assistant format (hue 0-360, sat 0-100)
            hue = hue_normalized * 360.0
            saturation = saturation_normalized * 100.0
            
            # Log color values for debugging (only when they change to avoid spam)
            if not hasattr(self, "_last_logged_color"):
                self._last_logged_color = None
            
            current_color = (round(hue, 1), round(saturation, 1))
            if self._last_logged_color != current_color:
                _LOGGER.debug(
                    "Light %s (%s) color read: hue_norm=%.4f (HA=%.2f°), sat_norm=%.4f (HA=%.2f%%) [from %s]",
                    self._device_id, self._attr_name,
                    hue_normalized, hue, saturation_normalized, saturation,
                    "coordinator" if (self.coordinator.data and self._device_id in self.coordinator.data) else "initial_data"
                )
                self._last_logged_color = current_color
            
            return (hue, saturation)
        
        return None

    @property
    def color_temp_kelvin(self) -> int | None:
        """Return the color temperature in Kelvin."""
        device_data = self.coordinator.data.get(self._device_id, self._device)
        capabilities = device_data.get("capabilitiesObj", {})
        temp_cap = capabilities.get("light_temperature", {})
        temp = temp_cap.get("value")
        if temp is not None:
            temp_min = temp_cap.get("min", 0)
            temp_max = temp_cap.get("max", 1)
            
            # Check if temperature is normalized (0-1) or in Kelvin
            if temp_min == 0 and temp_max == 1:
                # Normalized value - convert to Kelvin
                # 0 = 2000K (warm), 1 = 6500K (cool)
                if self._invert_temp:
                    kelvin = int(6500 - (temp * (6500 - 2000)))
                else:
                    kelvin = int(2000 + (temp * (6500 - 2000)))
                return kelvin
            else:
                # Already in Kelvin
                return int(temp)
        return None

    @property
    def effect(self) -> str | None:
        """Return the active light scene/effect, if exposed by Homey."""
        if not self._scene_capability:
            return None
        device_data = self.coordinator.data.get(self._device_id, self._device)
        capabilities = device_data.get("capabilitiesObj", {})
        value = capabilities.get(self._scene_capability, {}).get("value")
        return str(value) if value is not None else None

    @property
    def effect_list(self) -> list[str] | None:
        """Return available light scenes/effects from Homey capability options."""
        if not self._scene_capability:
            return None
        device_data = self.coordinator.data.get(self._device_id, self._device)
        capabilities = device_data.get("capabilitiesObj", {})
        cap_data = capabilities.get(self._scene_capability, {})
        options = cap_data.get("values") or cap_data.get("options")
        if not isinstance(options, list):
            return None
        if options and isinstance(options[0], dict):
            return [
                str(opt.get("id", opt.get("title")))
                for opt in options
                if opt.get("id") is not None or opt.get("title") is not None
            ]
        return [str(opt) for opt in options]

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the light on."""
        _LOGGER.debug("Turning on light %s (%s) with args: %s", self._attr_name, self._device_id, list(kwargs.keys()))
        
        capabilities_to_set: dict[str, Any] = {}

        if ATTR_BRIGHTNESS in kwargs:
            brightness = kwargs[ATTR_BRIGHTNESS]
            # Ensure brightness is numeric
            try:
                brightness = int(brightness) if not isinstance(brightness, (int, float)) else brightness
                capabilities_to_set["dim"] = brightness / 255.0
            except (ValueError, TypeError):
                _LOGGER.warning("Invalid brightness value: %s", brightness)
                # Skip brightness setting if invalid

        if ATTR_HS_COLOR in kwargs:
            hs_color = kwargs[ATTR_HS_COLOR]
            try:
                hue = float(hs_color[0])
                saturation = float(hs_color[1])
                
                # Home Assistant uses hue 0-360 and saturation 0-100
                # Homey API uses normalized values: hue 0-1 and saturation 0-1
                # Ensure values are within valid ranges
                hue = max(0, min(360, hue))  # Clamp to 0-360
                saturation = max(0, min(100, saturation))  # Clamp to 0-100
                
                # Convert to Homey's normalized format (0-1)
                hue_normalized = hue / 360.0
                saturation_normalized = saturation / 100.0
                
                # Log color conversion for debugging
                _LOGGER.debug(
                    "Setting color for light %s (%s): HA hue=%.2f, sat=%.2f -> Homey hue=%.4f, sat=%.4f",
                    self._device_id, self._attr_name, hue, saturation, hue_normalized, saturation_normalized
                )
                
                capabilities_to_set["light_hue"] = hue_normalized
                capabilities_to_set["light_saturation"] = saturation_normalized
            except (ValueError, TypeError, IndexError) as err:
                _LOGGER.warning("Invalid HS color value: %s (%s)", hs_color, err)
                # Skip color setting if invalid

        if ATTR_COLOR_TEMP_KELVIN in kwargs:
            kelvin = kwargs[ATTR_COLOR_TEMP_KELVIN]
            try:
                kelvin = int(kelvin) if not isinstance(kelvin, (int, float)) else kelvin
                
                # Check if device uses normalized temperature (0-1) or Kelvin
                device_data = self.coordinator.data.get(self._device_id, self._device)
                capabilities = device_data.get("capabilitiesObj", {})
                temp_cap = capabilities.get("light_temperature", {})
                temp_min = temp_cap.get("min", 0)
                temp_max = temp_cap.get("max", 1)
                
                if temp_min == 0 and temp_max == 1:
                    # Device uses normalized range - convert Kelvin to 0-1
                    # Clamp to valid range
                    kelvin = max(2000, min(6500, kelvin))
                    # Convert: 0 = 2000K, 1 = 6500K
                    if self._invert_temp:
                        normalized = (6500 - kelvin) / (6500 - 2000)
                    else:
                        normalized = (kelvin - 2000) / (6500 - 2000)
                    capabilities_to_set["light_temperature"] = normalized
                    _LOGGER.debug(
                        "Converting color temp %dK to normalized %.4f for device %s",
                        kelvin, normalized, self._device_id
                    )
                else:
                    # Device uses Kelvin directly
                    capabilities_to_set["light_temperature"] = kelvin
            except (ValueError, TypeError):
                _LOGGER.warning("Invalid color temperature value: %s", kelvin)
                # Skip temperature setting if invalid

        if ATTR_EFFECT in kwargs and self._scene_capability:
            effect = kwargs[ATTR_EFFECT]
            if effect is not None:
                capabilities_to_set[self._scene_capability] = str(effect)
        
        # If color temp is being set, remove color (HS) capabilities as they're mutually exclusive
        if "light_temperature" in capabilities_to_set:
            capabilities_to_set.pop("light_hue", None)
            capabilities_to_set.pop("light_saturation", None)
        
        # If color (HS) is being set, remove color temp as they're mutually exclusive
        if "light_hue" in capabilities_to_set or "light_saturation" in capabilities_to_set:
            capabilities_to_set.pop("light_temperature", None)

        # Set light_mode if supported and we're changing color/temperature
        if self._has_light_mode:
            device_data = self.coordinator.data.get(self._device_id, self._device)
            light_mode_cap = device_data.get("capabilitiesObj", {}).get("light_mode", {})
            if light_mode_cap.get("setable", True):
                if "light_temperature" in capabilities_to_set:
                    capabilities_to_set["light_mode"] = "temperature"
                elif "light_hue" in capabilities_to_set or "light_saturation" in capabilities_to_set:
                    capabilities_to_set["light_mode"] = "color"

        # Always turn on if not already on - this must happen first
        # Also ensure brightness is set if color is being set (some devices need brightness > 0 for color to show)
        if not self.is_on:
            success = await self._api.set_capability_value(self._device_id, "onoff", True)
            if not success:
                _LOGGER.error("Failed to turn on light %s", self._device_id)
                return
        
        # If setting color but no brightness specified, ensure minimum brightness for color visibility
        if ("light_hue" in capabilities_to_set or "light_saturation" in capabilities_to_set) and "dim" not in capabilities_to_set:
            current_brightness = self.brightness
            if current_brightness is None or current_brightness == 0:
                # Set minimum brightness so color is visible
                capabilities_to_set["dim"] = 0.1  # 10% brightness minimum
                _LOGGER.info("Setting minimum brightness (10%%) for color visibility on light %s (%s)", self._device_id, self._attr_name)

        # Set color capabilities first (hue and saturation together)
        # Some devices require both to be set for color changes to work
        # IMPORTANT: Set saturation BEFORE hue, as some devices need saturation set first
        if "light_hue" in capabilities_to_set and "light_saturation" in capabilities_to_set:
            # Set saturation first, then hue
            sat_success = await self._api.set_capability_value(
                self._device_id, "light_saturation", capabilities_to_set["light_saturation"]
            )
            hue_success = await self._api.set_capability_value(
                self._device_id, "light_hue", capabilities_to_set["light_hue"]
            )
            
            if not sat_success:
                _LOGGER.error(
                    "Failed to set saturation %.2f for light %s",
                    capabilities_to_set["light_saturation"], self._device_id
                )
            if not hue_success:
                _LOGGER.error(
                    "Failed to set hue %.2f for light %s",
                    capabilities_to_set["light_hue"], self._device_id
                )
            
            if sat_success and hue_success:
                _LOGGER.info(
                    "Successfully set color: hue=%.2f, saturation=%.2f for light %s (%s)",
                    capabilities_to_set["light_hue"],
                    capabilities_to_set["light_saturation"],
                    self._device_id,
                    self._attr_name
                )
            else:
                _LOGGER.warning(
                    "Color setting partially failed for light %s (%s): hue_success=%s, sat_success=%s",
                    self._device_id, self._attr_name, hue_success, sat_success
                )
            
            # Remove from dict so we don't set them again
            del capabilities_to_set["light_hue"]
            del capabilities_to_set["light_saturation"]

        # Set other capabilities (brightness, color temp, etc.)
        for capability, value in capabilities_to_set.items():
            success = await self._api.set_capability_value(self._device_id, capability, value)
            if not success:
                # Check if capability exists in device
                device_data = self.coordinator.data.get(self._device_id, self._device)
                capabilities = device_data.get("capabilitiesObj", {})
                if capability not in capabilities:
                    _LOGGER.error(
                        "Failed to set capability %s for light %s (%s) - capability not found in device. Available capabilities: %s",
                        capability, self._device_id, self._attr_name, list(capabilities.keys())
                    )
                else:
                    _LOGGER.error(
                        "Failed to set capability %s=%s for light %s (%s) - API call failed. Check device logs and ensure capability is writable.",
                        capability, value, self._device_id, self._attr_name
                    )

        # Immediately refresh this device's state for instant UI feedback
        await self.coordinator.async_refresh_device(self._device_id)
        
        # Log the actual device state after refresh to verify it changed
        device_data = self.coordinator.data.get(self._device_id, self._device)
        capabilities = device_data.get("capabilitiesObj", {})
        current_hue_normalized = capabilities.get("light_hue", {}).get("value")
        current_sat_normalized = capabilities.get("light_saturation", {}).get("value")
        current_dim = capabilities.get("dim", {}).get("value")
        current_onoff = capabilities.get("onoff", {}).get("value")
        
        # Log device state after color change for debugging
        if ATTR_HS_COLOR in kwargs:
            current_hue_ha = current_hue_normalized * 360.0 if current_hue_normalized is not None else None
            current_sat_ha = current_sat_normalized * 100.0 if current_sat_normalized is not None else None
            _LOGGER.debug(
                "After refresh - Device %s (%s) reports: hue_norm=%.4f (HA=%.2f°), sat_norm=%.4f (HA=%.2f%%)",
                self._device_id, self._attr_name,
                current_hue_normalized or 0, current_hue_ha or 0,
                current_sat_normalized or 0, current_sat_ha or 0
            )

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the light off."""
        _LOGGER.debug("Turning off light %s (%s)", self._attr_name, self._device_id)
        
        success = await self._api.set_capability_value(self._device_id, "onoff", False)
        if not success:
            _LOGGER.error("Failed to turn off light %s (%s)", self._device_id, self._attr_name)
        
        # Immediately refresh this device's state for instant UI feedback
        await self.coordinator.async_refresh_device(self._device_id)

