"""Support for Homey climate devices."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.climate import (
    ClimateEntity,
    ClimateEntityFeature,
    HVACMode,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import HomeyDataUpdateCoordinator
from .device_info import build_entity_unique_id, get_device_info
from .temperature import get_device_temperature_unit, resolve_temperature_unit

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Homey climate devices from a config entry."""
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
        device_class = device.get("class")
        device_name = device.get("name", "Unknown")
        
        # Check if this is a devicegroups group
        # Groups can have any class and are identified by driverId pattern: homey:app:com.swttt.devicegroups:*
        is_devicegroups_group = driver_id.startswith("homey:app:com.swttt.devicegroups:")
        
        # Special handling for devicegroups groups: respect their class
        # Groups can have class "heater" or "thermostat" but may not have target_temperature capability
        is_devicegroups_climate = (
            is_devicegroups_group 
            and device_class in ["heater", "thermostat"]
        )
        
        # Log devicegroups groups for debugging
        if is_devicegroups_group:
            _LOGGER.debug(
                "Found devicegroups group: %s (id: %s, class: %s, driverId: %s, capabilities: %s)",
                device_name,
                device_id,
                device_class,
                driver_id,
                list(capabilities.keys())
            )
        
        # Create climate entity if it has target_temperature OR is a devicegroups climate group
        if "target_temperature" in capabilities:
            entities.append(HomeyClimate(coordinator, device_id, device, api, zones, homey_id, multi_homey))
            _LOGGER.debug("Created climate entity for device %s (has target_temperature)", device_name)
        elif is_devicegroups_climate:
            entities.append(HomeyClimate(coordinator, device_id, device, api, zones, homey_id, multi_homey))
            _LOGGER.info(
                "Created climate entity for devicegroups group: %s (id: %s, class: %s) - note: no target_temperature capability",
                device_name,
                device_id,
                device_class
            )

    async_add_entities(entities)


class HomeyClimate(CoordinatorEntity, ClimateEntity):
    """Representation of a Homey climate device."""

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
        """Initialize the climate device."""
        super().__init__(coordinator)
        self._device_id = device_id
        self._device = device
        self._api = api
        self._homey_id = homey_id
        self._multi_homey = multi_homey
        self._attr_name = device.get("name", "Unknown Climate")
        self._attr_unique_id = build_entity_unique_id(
            homey_id, device_id, "climate", multi_homey
        )
        capabilities = device.get("capabilitiesObj", {})
        target_temp_cap = capabilities.get("target_temperature", {})
        measure_temp_cap = capabilities.get("measure_temperature", {})
        entry = coordinator.config_entry
        if entry:
            self._homey_temperature_unit = get_device_temperature_unit(
                entry, device_id, target_temp_cap, measure_temp_cap
            )
        else:
            self._homey_temperature_unit = resolve_temperature_unit(
                target_temp_cap, measure_temp_cap
            )
        self._attr_temperature_unit = self._homey_temperature_unit
        supported_features = ClimateEntityFeature.TARGET_TEMPERATURE
        
        # Add humidity support if available
        if "target_humidity" in capabilities:
            supported_features |= ClimateEntityFeature.TARGET_HUMIDITY
        
        # Check for on/off capabilities (onoff, etc.)
        # Only use settable on/off capabilities for turn_on/turn_off actions
        # Note: thermofloor_onoff is read-only (status indicator), not a control
        self._onoff_capability = None
        if "onoff" in capabilities:
            onoff_cap = capabilities.get("onoff", {})
            # Only use if it's settable
            if onoff_cap.get("setable", False):
                self._onoff_capability = "onoff"
                supported_features |= ClimateEntityFeature.TURN_ON | ClimateEntityFeature.TURN_OFF
        else:
            # Check for any *_onoff capability that is settable
            for cap_id in capabilities:
                if cap_id.endswith("_onoff") and capabilities[cap_id].get("type") == "boolean":
                    cap_data = capabilities[cap_id]
                    # Only use if it's settable (not read-only status indicators)
                    if cap_data.get("setable", False):
                        self._onoff_capability = cap_id
                        supported_features |= ClimateEntityFeature.TURN_ON | ClimateEntityFeature.TURN_OFF
                        break
        
        # If no settable on/off capability, we can still support turn_on/turn_off via HVAC mode changes
        # This handles devices like ThermoFloor that use mode for control (thermofloor_mode)
        if not self._onoff_capability:
            # We'll determine hvac_modes first, then add TURN_ON/TURN_OFF if appropriate
            pass
        
        self._attr_supported_features = supported_features
        hvac_modes = []
        
        # Check for custom thermostat mode capabilities (e.g., thermofloor_mode)
        # These are enum capabilities with mode values
        custom_mode_cap = None
        for cap_id in capabilities:
            if cap_id.endswith("_mode") and cap_id != "thermostat_mode" and capabilities[cap_id].get("type") == "enum":
                custom_mode_cap = cap_id
                break
        
        # Check for standard thermostat mode capabilities
        has_mode_off = "thermostat_mode_off" in capabilities
        has_mode_heat = "thermostat_mode_heat" in capabilities
        has_mode_cool = "thermostat_mode_cool" in capabilities
        has_mode_auto = "thermostat_mode_auto" in capabilities
        has_mode = "thermostat_mode" in capabilities
        
        # Handle custom mode capabilities (e.g., thermofloor_mode)
        if custom_mode_cap:
            mode_cap_data = capabilities[custom_mode_cap]
            mode_values = mode_cap_data.get("values", [])
            # Map custom mode values to HVAC modes
            # Example: thermofloor_mode has ["Heat", "Energy Save Heat", "Off", "Cool"]
            for mode_value in mode_values:
                mode_id = mode_value.get("id", mode_value.get("title", mode_value)) if isinstance(mode_value, dict) else str(mode_value)
                if mode_id is None:
                    continue
                mode_id_lower = str(mode_id).lower()
                if "off" in mode_id_lower or mode_id_lower == "off":
                    if HVACMode.OFF not in hvac_modes:
                        hvac_modes.append(HVACMode.OFF)
                elif "heat" in mode_id_lower or mode_id_lower == "heat":
                    if HVACMode.HEAT not in hvac_modes:
                        hvac_modes.append(HVACMode.HEAT)
                elif "cool" in mode_id_lower or mode_id_lower == "cool":
                    if HVACMode.COOL not in hvac_modes:
                        hvac_modes.append(HVACMode.COOL)
                elif "auto" in mode_id_lower or "energy" in mode_id_lower or "save" in mode_id_lower:
                    # Energy Save mode maps to AUTO or HEAT_COOL
                    if HVACMode.AUTO not in hvac_modes:
                        hvac_modes.append(HVACMode.AUTO)
            # Store custom mode capability for later use
            self._custom_mode_capability = custom_mode_cap
        # If we have standard mode capabilities, use them
        elif has_mode_off or has_mode_heat or has_mode_cool or has_mode_auto or has_mode:
            if has_mode_off or has_mode:
                hvac_modes.append(HVACMode.OFF)
            if has_mode_heat or has_mode:
                hvac_modes.append(HVACMode.HEAT)
            if has_mode_cool or has_mode:
                hvac_modes.append(HVACMode.COOL)
            if has_mode_auto or has_mode:
                hvac_modes.append(HVACMode.AUTO)
            # If we have multiple modes but not AUTO, add HEAT_COOL as fallback
            if not has_mode_auto and (has_mode_heat and has_mode_cool):
                hvac_modes.append(HVACMode.HEAT_COOL)
            self._custom_mode_capability = None
        else:
            # Fallback to original behavior: HEAT_COOL mode
            hvac_modes = [HVACMode.HEAT_COOL]
            if "onoff" in capabilities:
                hvac_modes.append(HVACMode.OFF)
            self._custom_mode_capability = None
        
        # Ensure we have at least one mode
        if not hvac_modes:
            hvac_modes = [HVACMode.HEAT_COOL]
        
        self._attr_hvac_modes = hvac_modes
        
        # If no settable on/off capability but we have HVAC modes, support turn_on/turn_off via mode changes
        # This handles devices like ThermoFloor that use mode for control (thermofloor_mode)
        if not self._onoff_capability and hvac_modes:
            # Only add TURN_ON/TURN_OFF if we have OFF mode and at least one non-OFF mode
            has_off_mode = HVACMode.OFF in hvac_modes
            has_non_off_mode = any(mode != HVACMode.OFF for mode in hvac_modes)
            if has_off_mode and has_non_off_mode:
                self._attr_supported_features |= ClimateEntityFeature.TURN_ON | ClimateEntityFeature.TURN_OFF
        
        # Get current mode from device
        current_mode = None
        if hasattr(self, "_custom_mode_capability") and self._custom_mode_capability:
            mode_cap_data = capabilities.get(self._custom_mode_capability, {})
            mode_value = mode_cap_data.get("value")
            if mode_value:
                mode_id = mode_value.get("id", mode_value.get("title", mode_value)) if isinstance(mode_value, dict) else str(mode_value)
                if mode_id is None:
                    return HVACMode.HEAT_COOL
                mode_id_lower = str(mode_id).lower()
                if "off" in mode_id_lower or mode_id_lower == "off":
                    current_mode = HVACMode.OFF
                elif "heat" in mode_id_lower and "energy" in mode_id_lower:
                    current_mode = HVACMode.AUTO  # Energy Save Heat = AUTO
                elif "heat" in mode_id_lower:
                    current_mode = HVACMode.HEAT
                elif "cool" in mode_id_lower:
                    current_mode = HVACMode.COOL
                elif "auto" in mode_id_lower:
                    current_mode = HVACMode.AUTO
        elif "thermostat_mode" in capabilities:
            mode_value = capabilities.get("thermostat_mode", {}).get("value")
            if mode_value:
                mode_mapping = {
                    "off": HVACMode.OFF,
                    "heat": HVACMode.HEAT,
                    "cool": HVACMode.COOL,
                    "auto": HVACMode.AUTO,
                }
                current_mode = mode_mapping.get(str(mode_value).lower())
        
        # Set initial mode - use current mode if available, otherwise prefer AUTO, then HEAT_COOL, then first mode
        if current_mode and current_mode in hvac_modes:
            self._attr_hvac_mode = current_mode
        elif HVACMode.AUTO in hvac_modes:
            self._attr_hvac_mode = HVACMode.AUTO
        elif HVACMode.HEAT_COOL in hvac_modes:
            self._attr_hvac_mode = HVACMode.HEAT_COOL
        else:
            self._attr_hvac_mode = hvac_modes[0] if hvac_modes else HVACMode.HEAT_COOL

        # Min/max/step use Homey's native unit (same as temperature_unit above).
        if "min" in target_temp_cap:
            self._attr_min_temp = target_temp_cap["min"]
        else:
            # Default to reasonable range if not provided by Homey
            self._attr_min_temp = 5.0  # 5°C minimum
        
        if "max" in target_temp_cap:
            self._attr_max_temp = target_temp_cap["max"]
        else:
            # Default to reasonable range if not provided by Homey
            self._attr_max_temp = 35.0  # 35°C maximum
        
        # Also set temperature step if available (for slider precision)
        if "step" in target_temp_cap:
            self._attr_target_temperature_step = target_temp_cap["step"]
        else:
            # Default to 0.5°C steps
            self._attr_target_temperature_step = 0.5

        self._attr_device_info = get_device_info(
            self._homey_id, device_id, device, zones, self._multi_homey
        )

    @property
    def current_temperature(self) -> float | None:
        """Return the current temperature."""
        device_data = self.coordinator.data.get(self._device_id, self._device)
        capabilities = device_data.get("capabilitiesObj", {})
        temp = capabilities.get("measure_temperature", {}).get("value")
        return float(temp) if temp is not None else None

    @property
    def target_temperature(self) -> float | None:
        """Return the target temperature."""
        device_data = self.coordinator.data.get(self._device_id, self._device)
        capabilities = device_data.get("capabilitiesObj", {})
        temp = capabilities.get("target_temperature", {}).get("value")
        return float(temp) if temp is not None else None

    @property
    def current_humidity(self) -> int | None:
        """Return the current humidity."""
        device_data = self.coordinator.data.get(self._device_id, self._device)
        capabilities = device_data.get("capabilitiesObj", {})
        humidity_cap = capabilities.get("measure_humidity", {})
        humidity = humidity_cap.get("value")
        if humidity is not None:
            try:
                humidity_float = float(humidity)
                # Check capability max to determine if normalized (0-1) or percentage (0-100)
                # If max <= 1, it's normalized and needs conversion
                cap_max = humidity_cap.get("max", 100)
                if cap_max <= 1.0:
                    # Normalized value (0-1), convert to percentage (0-100)
                    humidity_float = humidity_float * 100.0
                return int(humidity_float)
            except (ValueError, TypeError):
                return None
        return None

    @property
    def target_humidity(self) -> int | None:
        """Return the target humidity."""
        device_data = self.coordinator.data.get(self._device_id, self._device)
        capabilities = device_data.get("capabilitiesObj", {})
        humidity_cap = capabilities.get("target_humidity", {})
        humidity = humidity_cap.get("value")
        if humidity is not None:
            try:
                humidity_float = float(humidity)
                # Check capability max to determine if normalized (0-1) or percentage (0-100)
                # If max <= 1, it's normalized and needs conversion
                cap_max = humidity_cap.get("max", 100)
                if cap_max <= 1.0:
                    # Normalized value (0-1), convert to percentage (0-100)
                    humidity_float = humidity_float * 100.0
                return int(humidity_float)
            except (ValueError, TypeError):
                return None
        return None

    async def async_set_temperature(self, **kwargs: Any) -> None:
        """Set new target temperature."""
        temperature = None
        
        # Handle different temperature parameter formats
        if "temperature" in kwargs:
            temperature = kwargs["temperature"]
        elif "target_temperature_high" in kwargs and "target_temperature_low" in kwargs:
            # For HEAT_COOL mode, Home Assistant may pass high/low values
            # Use the high value (or average) since Homey typically uses a single target
            high = kwargs.get("target_temperature_high")
            low = kwargs.get("target_temperature_low")
            if high is not None and low is not None:
                # Use average for HEAT_COOL mode, or just high if that makes more sense
                temperature = (float(high) + float(low)) / 2.0
                _LOGGER.debug(
                    "HEAT_COOL mode: using average of high=%s and low=%s -> %s for device %s",
                    high, low, temperature, self._device_id
                )
        elif "target_temperature_high" in kwargs:
            temperature = kwargs["target_temperature_high"]
        elif "target_temperature_low" in kwargs:
            temperature = kwargs["target_temperature_low"]
        
        if temperature is None:
            _LOGGER.warning(
                "No temperature parameter found in kwargs: %s for device %s",
                list(kwargs.keys()), self._device_id
            )
            return
        
        # Ensure temperature is numeric
        try:
            if not isinstance(temperature, (int, float)):
                temperature = float(temperature)
        except (ValueError, TypeError):
            _LOGGER.error(
                "Invalid temperature value: %s for device %s",
                temperature, self._device_id
            )
            return
        
        _LOGGER.debug(
            "Setting target temperature to %s for device %s (%s)",
            temperature, self._device_id, self._attr_name
        )
        
        # Set the capability value and check if it succeeded
        success = await self._api.set_capability_value(
            self._device_id, "target_temperature", temperature
        )
        
        if success:
            _LOGGER.info(
                "Successfully set target temperature to %s %s for device %s (%s)",
                temperature,
                self._homey_temperature_unit,
                self._device_id,
                self._attr_name,
            )
            # Immediately refresh this device's state for instant UI feedback
            await self.coordinator.async_refresh_device(self._device_id)
        else:
            _LOGGER.error(
                "Failed to set target temperature to %s %s for device %s (%s). "
                "Check API permissions (homey.device.control) and device capabilities.",
                temperature,
                self._homey_temperature_unit,
                self._device_id,
                self._attr_name,
            )

    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        """Set new target hvac mode."""
        device_data = self.coordinator.data.get(self._device_id, self._device)
        capabilities = device_data.get("capabilitiesObj", {})
        
        # Check if we have a custom mode capability (e.g., thermofloor_mode)
        if hasattr(self, "_custom_mode_capability") and self._custom_mode_capability:
            mode_cap = capabilities.get(self._custom_mode_capability, {})
            mode_values = mode_cap.get("values", [])
            # Map HVACMode to custom mode values
            target_modes = []
            if hvac_mode == HVACMode.OFF:
                target_modes = ["off", "Off"]
            elif hvac_mode == HVACMode.HEAT:
                target_modes = ["heat", "Heat"]
            elif hvac_mode == HVACMode.COOL:
                target_modes = ["cool", "Cool"]
            elif hvac_mode == HVACMode.AUTO:
                target_modes = ["auto", "Auto", "Energy Save Heat", "Energy Save"]
            elif hvac_mode == HVACMode.HEAT_COOL:
                target_modes = ["auto", "Auto"]
            
            # Find matching mode value
            for mode_value_obj in mode_values:
                mode_id = mode_value_obj.get("id", mode_value_obj.get("title", mode_value_obj)) if isinstance(mode_value_obj, dict) else str(mode_value_obj)
                if mode_id is None:
                    continue
                mode_id_str = str(mode_id)
                if mode_id_str in target_modes or mode_id_str.lower() in [m.lower() for m in target_modes]:
                    await self._api.set_capability_value(self._device_id, self._custom_mode_capability, mode_id)
                    await self.coordinator.async_refresh_device(self._device_id)
                    return
        # Check if device has thermostat_mode capability
        elif "thermostat_mode" in capabilities:
            # Map HVACMode to Homey thermostat mode values
            mode_mapping = {
                HVACMode.OFF: "off",
                HVACMode.HEAT: "heat",
                HVACMode.COOL: "cool",
                HVACMode.AUTO: "auto",
                HVACMode.HEAT_COOL: "auto",  # Fallback to auto if HEAT_COOL not supported
            }
            mode_value = mode_mapping.get(hvac_mode)
            if mode_value:
                await self._api.set_capability_value(self._device_id, "thermostat_mode", mode_value)
        elif hvac_mode == HVACMode.OFF:
            # Fallback to onoff capability if thermostat_mode not available
            if "onoff" in capabilities:
                await self._api.set_capability_value(self._device_id, "onoff", False)
        else:
            # Turn on if not OFF mode
            if "onoff" in capabilities:
                await self._api.set_capability_value(self._device_id, "onoff", True)
        
        # Immediately refresh this device's state for instant UI feedback
        await self.coordinator.async_refresh_device(self._device_id)
    
    @property
    def hvac_mode(self) -> HVACMode:
        """Return the current HVAC mode."""
        device_data = self.coordinator.data.get(self._device_id, self._device)
        capabilities = device_data.get("capabilitiesObj", {})
        
        # Check if we have a custom mode capability (e.g., thermofloor_mode)
        if hasattr(self, "_custom_mode_capability") and self._custom_mode_capability:
            mode_cap_data = capabilities.get(self._custom_mode_capability, {})
            mode_value = mode_cap_data.get("value")
            if mode_value:
                mode_id = mode_value.get("id", mode_value.get("title", mode_value)) if isinstance(mode_value, dict) else str(mode_value)
                if mode_id is None:
                    return HVACMode.HEAT_COOL
                mode_id_lower = str(mode_id).lower()
                if "off" in mode_id_lower or mode_id_lower == "off":
                    return HVACMode.OFF
                elif "heat" in mode_id_lower and "energy" in mode_id_lower:
                    return HVACMode.AUTO  # Energy Save Heat = AUTO
                elif "heat" in mode_id_lower:
                    return HVACMode.HEAT
                elif "cool" in mode_id_lower:
                    return HVACMode.COOL
                elif "auto" in mode_id_lower:
                    return HVACMode.AUTO
        
        # Check if device has thermostat_mode capability
        if "thermostat_mode" in capabilities:
            mode_value = capabilities.get("thermostat_mode", {}).get("value")
            if mode_value:
                mode_mapping = {
                    "off": HVACMode.OFF,
                    "heat": HVACMode.HEAT,
                    "cool": HVACMode.COOL,
                    "auto": HVACMode.AUTO,
                }
                return mode_mapping.get(str(mode_value).lower(), HVACMode.HEAT_COOL)
        
        # Fallback: check onoff capability
        if "onoff" in capabilities:
            is_on = capabilities.get("onoff", {}).get("value", False)
            return HVACMode.OFF if not is_on else HVACMode.HEAT_COOL
        
        return self._attr_hvac_mode

    async def async_turn_on(self) -> None:
        """Turn the climate device on."""
        if hasattr(self, "_onoff_capability") and self._onoff_capability:
            await self._api.set_capability_value(self._device_id, self._onoff_capability, True)
            await self.coordinator.async_refresh_device(self._device_id)
        else:
            # Fallback: set HVAC mode to first non-OFF mode
            if self._attr_hvac_modes:
                for mode in self._attr_hvac_modes:
                    if mode != HVACMode.OFF:
                        await self.async_set_hvac_mode(mode)
                        return

    async def async_turn_off(self) -> None:
        """Turn the climate device off."""
        if hasattr(self, "_onoff_capability") and self._onoff_capability:
            await self._api.set_capability_value(self._device_id, self._onoff_capability, False)
            await self.coordinator.async_refresh_device(self._device_id)
        else:
            # Fallback: set HVAC mode to OFF
            if HVACMode.OFF in self._attr_hvac_modes:
                await self.async_set_hvac_mode(HVACMode.OFF)

    async def async_set_humidity(self, humidity: int) -> None:
        """Set new target humidity."""
        capabilities = self._device.get("capabilitiesObj", {})
        humidity_cap = capabilities.get("target_humidity", {})
        if humidity_cap:
            try:
                # Check capability max to determine if normalized (0-1) or percentage (0-100)
                # If max <= 1, it's normalized and needs conversion
                cap_max = humidity_cap.get("max", 100)
                if cap_max <= 1.0:
                    # Homey uses normalized 0-1, convert from percentage (0-100)
                    humidity_value = float(humidity) / 100.0
                else:
                    # Homey uses percentage 0-100, use as-is
                    humidity_value = float(humidity)
                
                success = await self._api.set_capability_value(
                    self._device_id, "target_humidity", humidity_value
                )
                if success:
                    _LOGGER.debug("Successfully set target humidity to %s for device %s", humidity, self._device_id)
                    await self.coordinator.async_refresh_device(self._device_id)
                else:
                    _LOGGER.error(
                        "Failed to set target humidity to %s for device %s. Check API permissions and device capabilities.",
                        humidity,
                        self._device_id,
                    )
            except (ValueError, TypeError) as err:
                _LOGGER.error("Invalid humidity value: %s (%s)", humidity, err)
