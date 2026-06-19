"""Support for Homey number entities."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.number import NumberEntity, NumberEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import CONF_USE_CAPABILITY_TITLES, DOMAIN
from .coordinator import HomeyDataUpdateCoordinator, HomeyLogicUpdateCoordinator
from .device_info import build_entity_unique_id, get_capability_label, get_device_info

_LOGGER = logging.getLogger(__name__)

# Capabilities that should be exposed as number entities
# These are numeric settings that users can control, not measurements
NUMBER_CAPABILITIES: list[str] = [
    # Add capabilities here that need numeric input but aren't sensors
    # Example: "dim" could be here, but it's already handled by light platform
    # "some_setting": {"min": 0, "max": 100, "step": 1, "unit": "%"},
]

# Patterns for capabilities that should be number entities
# These are sub-capabilities that need numeric control but aren't the main capability
NUMBER_CAPABILITY_PATTERNS = [
    "target_temperature.",  # target_temperature.normal, target_temperature.comfort, etc.
]


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Homey number entities from a config entry."""
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
    devices = coordinator.data if coordinator.data else await api.get_devices()
    
    # Filter devices if device_filter is configured
    from . import filter_devices
    devices = filter_devices(devices, entry.data.get("device_filter"))

    for device_id, device in devices.items():
        capabilities = device.get("capabilitiesObj", {})
        
        # Check explicitly listed number capabilities
        for capability_id in NUMBER_CAPABILITIES:
            if capability_id in capabilities:
                cap_data = capabilities[capability_id]
                # Only add if settable (user can control it)
                if cap_data.get("setable"):
                    entities.append(
                        HomeyNumber(
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
        
        # Check for pattern-based number capabilities (sub-capabilities)
        for capability_id, cap_data in capabilities.items():
            # Skip if already handled above
            if capability_id in NUMBER_CAPABILITIES:
                continue
            
            # Skip if not settable (can't control it)
            if not cap_data.get("setable"):
                continue
            
            # Skip if it's the base capability handled by another platform
            # (e.g., target_temperature is handled by climate platform)
            if capability_id == "target_temperature":
                continue
            
            # Check if this matches a pattern for number entities
            is_number_pattern = any(
                capability_id.startswith(pattern) for pattern in NUMBER_CAPABILITY_PATTERNS
            )
            
            # Also check if it's a numeric type capability that's settable
            # and not already handled by another platform
            is_numeric_settable = (
                cap_data.get("type") == "number" and
                cap_data.get("setable") and
                "." in capability_id  # Sub-capability (e.g., target_temperature.normal)
            )
            
            if is_number_pattern or is_numeric_settable:
                entities.append(
                    HomeyNumber(
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

    # Add Homey Logic number variables (not device capabilities)
    if logic_coordinator:
        logic_variables = (
            logic_coordinator.data
            if logic_coordinator.data is not None
            else await api.get_logic_variables()
        )
        for variable_id, variable in logic_variables.items():
            if variable.get("type") == "number":
                entities.append(
                    HomeyLogicNumber(
                        logic_coordinator,
                        variable_id,
                        variable,
                        api,
                        homey_id,
                        multi_homey,
                    )
                )

    async_add_entities(entities)


class HomeyNumber(CoordinatorEntity, NumberEntity):
    """Representation of a Homey number entity."""

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
        """Initialize the number entity."""
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
            capability_id, capability_data, use_titles, legacy_uses_title=False
        )
        self._attr_name = f"{device_name} {capability_label}"
        self._attr_unique_id = build_entity_unique_id(
            homey_id, device_id, capability_id, multi_homey
        )
        
        # Get min/max/step from capability data
        self._attr_native_min_value = capability_data.get("min", 0)
        self._attr_native_max_value = capability_data.get("max", 100)
        self._attr_native_step = capability_data.get("step", 1)
        
        # Get unit if available
        unit = capability_data.get("unit")
        if unit:
            self._attr_native_unit_of_measurement = unit
        
        self._attr_device_info = get_device_info(
            self._homey_id, device_id, device, zones, self._multi_homey
        )

    @property
    def native_value(self) -> float | None:
        """Return the current value."""
        device_data = self.coordinator.data.get(self._device_id, self._device)
        capabilities = device_data.get("capabilitiesObj", {})
        value = capabilities.get(self._capability_id, {}).get("value")
        if value is not None:
            try:
                return float(value)
            except (ValueError, TypeError):
                return None
        return None

    async def async_set_native_value(self, value: float) -> None:
        """Set the value."""
        success = await self._api.set_capability_value(self._device_id, self._capability_id, value)
        if success:
            _LOGGER.debug("Successfully set %s to %s for device %s", self._capability_id, value, self._device_id)
            await self.coordinator.async_refresh_device(self._device_id)
        else:
            _LOGGER.error("Failed to set %s to %s for device %s", self._capability_id, value, self._device_id)


class HomeyLogicNumber(CoordinatorEntity, NumberEntity):
    """Representation of a Homey logic number variable."""

    def __init__(
        self,
        coordinator: HomeyLogicUpdateCoordinator,
        variable_id: str,
        variable: dict[str, Any],
        api,
        homey_id: str | None = None,
        multi_homey: bool = False,
    ) -> None:
        """Initialize the logic number entity."""
        super().__init__(coordinator)
        self._variable_id = variable_id
        self._variable = variable
        self._api = api
        self._homey_id = homey_id
        self._multi_homey = multi_homey

        variable_name = variable.get("name", "Logic Number")
        self._attr_name = variable_name
        self._attr_unique_id = build_entity_unique_id(
            homey_id, "logic", f"number_{variable_id}", multi_homey
        )

        # Logic variables don't provide min/max metadata; use a wide, safe range.
        self._attr_native_min_value = -1_000_000_000.0
        self._attr_native_max_value = 1_000_000_000.0
        self._attr_native_step = 1.0

        # Adjust step for decimal values if the current value is a float
        value = variable.get("value")
        if isinstance(value, float) and not value.is_integer():
            self._attr_native_step = 0.01

        logic_identifier = f"{homey_id}:logic" if (multi_homey and homey_id) else "logic"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, logic_identifier)},
            "name": "Homey Logic",
            "manufacturer": "Athom",
            "model": "Homey",
        }

    @property
    def native_value(self) -> float | None:
        """Return the current number value."""
        variables = self.coordinator.data or {}
        variable = variables.get(self._variable_id, self._variable)
        value = variable.get("value")
        if value is None:
            return None
        try:
            return float(value)
        except (ValueError, TypeError):
            return None

    async def async_set_native_value(self, value: float) -> None:
        """Set the logic variable value."""
        success = await self._api.update_logic_variable(self._variable_id, value)
        if success:
            _LOGGER.debug(
                "Successfully updated logic variable %s to %s",
                self._variable_id,
                value,
            )
            await self.coordinator.async_request_refresh()
        else:
            _LOGGER.error(
                "Failed to update logic variable %s to %s",
                self._variable_id,
                value,
            )
