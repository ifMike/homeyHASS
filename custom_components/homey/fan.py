"""Support for Homey fans."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.fan import FanEntity, FanEntityFeature
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
    """Set up Homey fans from a config entry."""
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
                "Found devicegroups group in fan platform: %s (id: %s, class: %s, driverId: %s, capabilities: %s)",
                device_name,
                device_id,
                device_class,
                driver_id,
                list(capabilities.keys())
            )
        
        # Special handling for devicegroups groups: respect their class
        # If a group has class "fan", treat it as a fan even if capabilities are minimal
        is_devicegroups_fan = (
            is_devicegroups_group 
            and device_class == "fan" 
            and "onoff" in capabilities  # At minimum, fans should have onoff
        )
        
        # Create fan entity if:
        # 1. Has fan_speed capability (standard detection)
        # 2. OR is a devicegroups group with class "fan" (respect group class)
        # Note: Groups with class "fan" but no fan_speed will still create a fan entity
        # The entity will handle missing capabilities gracefully
        if "fan_speed" in capabilities or is_devicegroups_fan:
            entities.append(HomeyFan(coordinator, device_id, device, api, zones, homey_id, multi_homey))
            if is_devicegroups_group:
                _LOGGER.info(
                    "Created fan entity for devicegroups group: %s (id: %s, has_fan_speed=%s)",
                    device_name,
                    device_id,
                    "fan_speed" in capabilities
                )

    async_add_entities(entities)


class HomeyFan(CoordinatorEntity, FanEntity):
    """Representation of a Homey fan."""

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
        """Initialize the fan."""
        super().__init__(coordinator)
        self._device_id = device_id
        self._device = device
        self._api = api
        self._homey_id = homey_id
        self._multi_homey = multi_homey
        self._attr_name = device.get("name", "Unknown Fan")
        self._attr_unique_id = build_entity_unique_id(
            homey_id, device_id, "fan", multi_homey
        )

        capabilities = device.get("capabilitiesObj", {})
        supported_features = FanEntityFeature.SET_SPEED if "fan_speed" in capabilities else 0
        # Note: Fans don't have ON_OFF feature - they're always on/off by default
        # The onoff capability is handled via is_on property and turn_on/turn_off methods

        self._attr_supported_features = supported_features

        self._attr_device_info = get_device_info(
            self._homey_id, device_id, device, zones, self._multi_homey
        )

    @property
    def is_on(self) -> bool:
        """Return true if fan is on."""
        device_data = self.coordinator.data.get(self._device_id, self._device)
        capabilities = device_data.get("capabilitiesObj", {})
        if "onoff" in capabilities:
            return capabilities.get("onoff", {}).get("value", False)
        # If no onoff capability, check if speed > 0
        speed = capabilities.get("fan_speed", {}).get("value", 0)
        return speed > 0

    @property
    def percentage(self) -> int | None:
        """Return the current speed percentage."""
        device_data = self.coordinator.data.get(self._device_id, self._device)
        capabilities = device_data.get("capabilitiesObj", {})
        speed = capabilities.get("fan_speed", {}).get("value")
        if speed is not None:
            try:
                return int(float(speed) * 100)
            except (ValueError, TypeError):
                return None
        return None

    async def async_turn_on(
        self,
        percentage: int | None = None,
        preset_mode: str | None = None,
        **kwargs: Any,
    ) -> None:
        """Turn on the fan."""
        if "onoff" in self._device.get("capabilitiesObj", {}):
            await self._api.set_capability_value(self._device_id, "onoff", True)

        if percentage is not None and "fan_speed" in self._device.get("capabilitiesObj", {}):
            await self._api.set_capability_value(
                self._device_id, "fan_speed", percentage / 100.0
            )

        # Immediately refresh this device's state for instant UI feedback
        await self.coordinator.async_refresh_device(self._device_id)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn off the fan."""
        if "onoff" in self._device.get("capabilitiesObj", {}):
            await self._api.set_capability_value(self._device_id, "onoff", False)
        elif "fan_speed" in self._device.get("capabilitiesObj", {}):
            await self._api.set_capability_value(self._device_id, "fan_speed", 0.0)

        # Immediately refresh this device's state for instant UI feedback
        await self.coordinator.async_refresh_device(self._device_id)

    async def async_set_percentage(self, percentage: int) -> None:
        """Set the speed percentage of the fan."""
        if "fan_speed" in self._device.get("capabilitiesObj", {}):
            await self._api.set_capability_value(
                self._device_id, "fan_speed", percentage / 100.0
            )
            # Immediately refresh this device's state for instant UI feedback
            await self.coordinator.async_refresh_device(self._device_id)

