"""Support for Homey vacuum cleaners."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.vacuum import (
    StateVacuumEntity,
    VacuumActivity,
    VacuumEntityFeature,
)
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
    """Set up Homey vacuums from a config entry."""
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
        # Check if device is a vacuum cleaner
        device_class = device.get("class")
        capabilities = device.get("capabilitiesObj", {})
        
        # Support devices with class "vacuumcleaner" or devices with vacuum-specific capabilities
        if device_class == "vacuumcleaner" or any(
            cap in capabilities
            for cap in ["is_cleaning", "clean_full", "pause_clean", "dock"]
        ):
            entities.append(HomeyVacuum(coordinator, device_id, device, api, zones, homey_id, multi_homey))

    async_add_entities(entities)


class HomeyVacuum(CoordinatorEntity, StateVacuumEntity):
    """Representation of a Homey vacuum cleaner."""

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
        """Initialize the vacuum."""
        super().__init__(coordinator)
        self._device_id = device_id
        self._device = device
        self._api = api
        self._homey_id = homey_id
        self._multi_homey = multi_homey
        self._attr_name = device.get("name", "Unknown Vacuum")
        self._attr_unique_id = build_entity_unique_id(
            homey_id, device_id, "vacuum", multi_homey
        )

        capabilities = device.get("capabilitiesObj", {})
        
        # Determine supported features based on available capabilities
        supported_features = VacuumEntityFeature.STATE | VacuumEntityFeature.BATTERY
        
        if "clean_full" in capabilities and capabilities.get("clean_full", {}).get("setable"):
            supported_features |= VacuumEntityFeature.TURN_ON | VacuumEntityFeature.START
        
        if "pause_clean" in capabilities and capabilities.get("pause_clean", {}).get("setable"):
            supported_features |= VacuumEntityFeature.PAUSE
        
        if "dock" in capabilities and capabilities.get("dock", {}).get("setable"):
            supported_features |= VacuumEntityFeature.RETURN_HOME
        
        if "suction_power" in capabilities:
            supported_features |= VacuumEntityFeature.FAN_SPEED
        
        self._attr_supported_features = supported_features
        self._attr_device_info = get_device_info(
            self._homey_id, device_id, device, zones, self._multi_homey
        )

    @property
    def activity(self) -> VacuumActivity | None:
        """Return the activity of the vacuum."""
        device_data = self.coordinator.data.get(self._device_id, self._device)
        capabilities = device_data.get("capabilitiesObj", {})
        
        # Check for error states first
        if capabilities.get("alarm_problem", {}).get("value"):
            return VacuumActivity.ERROR
        if capabilities.get("alarm_stuck", {}).get("value"):
            return VacuumActivity.ERROR
        if capabilities.get("alarm_battery", {}).get("value"):
            return VacuumActivity.ERROR
        
        # Check if docked
        docked = capabilities.get("dock", {}).get("value")
        if docked is True:
            return VacuumActivity.DOCKED
        
        # Check if cleaning
        is_cleaning = capabilities.get("is_cleaning", {}).get("value")
        if is_cleaning is True:
            return VacuumActivity.CLEANING
        
        # Check if paused (pause_clean is True means paused)
        pause_clean = capabilities.get("pause_clean", {}).get("value")
        if pause_clean is True:
            return VacuumActivity.PAUSED
        
        # Check battery charging state to determine if returning
        charging_state = capabilities.get("battery_charging_state", {}).get("value")
        if charging_state == "charging" and docked is False:
            return VacuumActivity.RETURNING
        
        # Default to idle
        return VacuumActivity.IDLE

    @property
    def battery_level(self) -> int | None:
        """Return the battery level of the vacuum."""
        device_data = self.coordinator.data.get(self._device_id, self._device)
        capabilities = device_data.get("capabilitiesObj", {})
        battery = capabilities.get("measure_battery", {}).get("value")
        if battery is not None:
            try:
                return int(float(battery))
            except (ValueError, TypeError):
                return None
        return None

    @property
    def fan_speed(self) -> str | None:
        """Return the current fan speed."""
        device_data = self.coordinator.data.get(self._device_id, self._device)
        capabilities = device_data.get("capabilitiesObj", {})
        suction_power = capabilities.get("suction_power", {})
        
        if not suction_power:
            return None
        
        value = suction_power.get("value")
        if value is None:
            return None
        
        # Get the title from the enum value
        values = suction_power.get("values", [])
        if isinstance(values, list) and len(values) > 0:
            for val in values:
                if isinstance(val, dict):
                    val_id = val.get("id")
                    val_title = val.get("title", val_id)
                    if str(val_id) == str(value):
                        return val_title
                elif str(val) == str(value):
                    return str(val)
        
        # Fallback: return the value as string
        return str(value)

    @property
    def fan_speed_list(self) -> list[str]:
        """Return the list of available fan speeds."""
        device_data = self.coordinator.data.get(self._device_id, self._device)
        capabilities = device_data.get("capabilitiesObj", {})
        suction_power = capabilities.get("suction_power", {})
        
        if not suction_power:
            return []
        
        values = suction_power.get("values", [])
        if not isinstance(values, list):
            return []
        
        fan_speeds = []
        for val in values:
            if isinstance(val, dict):
                title = val.get("title", val.get("id", ""))
                if title:
                    fan_speeds.append(title)
            else:
                fan_speeds.append(str(val))
        
        return fan_speeds

    async def async_start(self) -> None:
        """Start or resume the cleaning task."""
        capabilities = self._device.get("capabilitiesObj", {})
        
        # Try clean_full first (start full clean)
        if "clean_full" in capabilities:
            clean_full_cap = capabilities.get("clean_full", {})
            if clean_full_cap.get("setable"):
                await self._api.set_capability_value(self._device_id, "clean_full", True)
                await self.coordinator.async_refresh_device(self._device_id)
                return
        
        # Fallback: try pause_clean (set to False to resume)
        if "pause_clean" in capabilities:
            pause_cap = capabilities.get("pause_clean", {})
            if pause_cap.get("setable"):
                await self._api.set_capability_value(self._device_id, "pause_clean", False)
                await self.coordinator.async_refresh_device(self._device_id)
                return
        
        _LOGGER.warning("Device %s does not support starting cleaning", self._device_id)

    async def async_pause(self) -> None:
        """Pause the cleaning task."""
        capabilities = self._device.get("capabilitiesObj", {})
        
        if "pause_clean" in capabilities:
            pause_cap = capabilities.get("pause_clean", {})
            if pause_cap.get("setable"):
                await self._api.set_capability_value(self._device_id, "pause_clean", True)
                await self.coordinator.async_refresh_device(self._device_id)
                return
        
        _LOGGER.warning("Device %s does not support pausing", self._device_id)

    async def async_return_to_base(self, **kwargs: Any) -> None:
        """Return the vacuum to the dock."""
        capabilities = self._device.get("capabilitiesObj", {})
        
        if "dock" in capabilities:
            dock_cap = capabilities.get("dock", {})
            if dock_cap.get("setable"):
                await self._api.set_capability_value(self._device_id, "dock", True)
                await self.coordinator.async_refresh_device(self._device_id)
                return
        
        _LOGGER.warning("Device %s does not support returning to dock", self._device_id)

    async def async_set_fan_speed(self, fan_speed: str, **kwargs: Any) -> None:
        """Set the fan speed."""
        capabilities = self._device.get("capabilitiesObj", {})
        
        if "suction_power" not in capabilities:
            _LOGGER.warning("Device %s does not support fan speed control", self._device_id)
            return
        
        suction_power_cap = capabilities.get("suction_power", {})
        if not suction_power_cap.get("setable"):
            _LOGGER.warning("Device %s fan speed is not settable", self._device_id)
            return
        
        # Find the value ID that matches the fan_speed title
        values = suction_power_cap.get("values", [])
        value_id = None
        
        for val in values:
            if isinstance(val, dict):
                val_title = val.get("title", "")
                val_id = val.get("id", "")
                if val_title == fan_speed or str(val_id) == fan_speed:
                    value_id = val_id
                    break
            elif str(val) == fan_speed:
                value_id = val
                break
        
        if value_id is None:
            _LOGGER.warning("Invalid fan speed '%s' for device %s", fan_speed, self._device_id)
            return
        
        await self._api.set_capability_value(self._device_id, "suction_power", value_id)
        await self.coordinator.async_refresh_device(self._device_id)

    @property
    def available(self) -> bool:
        """Return if the vacuum is available."""
        device_data = self.coordinator.data.get(self._device_id)
        if device_data is None:
            device_data = self._device
        
        if not device_data:
            return False
        
        # Check if device has vacuum capabilities
        capabilities = device_data.get("capabilitiesObj", {})
        return any(
            cap in capabilities
            for cap in ["is_cleaning", "clean_full", "pause_clean", "dock"]
        )
