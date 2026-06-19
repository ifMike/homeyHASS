"""Support for Homey locks."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.lock import LockEntity
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
    """Set up Homey locks from a config entry."""
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
        if "locked" in capabilities:
            entities.append(HomeyLock(coordinator, device_id, device, api, zones, homey_id, multi_homey))

    async_add_entities(entities)


class HomeyLock(CoordinatorEntity, LockEntity):
    """Representation of a Homey lock."""

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
        """Initialize the lock."""
        super().__init__(coordinator)
        self._device_id = device_id
        self._device = device
        self._api = api
        self._homey_id = homey_id
        self._multi_homey = multi_homey
        self._attr_name = device.get("name", "Unknown Lock")
        self._attr_unique_id = build_entity_unique_id(
            homey_id, device_id, "lock", multi_homey
        )

        self._attr_device_info = get_device_info(
            self._homey_id, device_id, device, zones, self._multi_homey
        )

    @property
    def is_locked(self) -> bool | None:
        """Return true if lock is locked."""
        device_data = self.coordinator.data.get(self._device_id, self._device)
        capabilities = device_data.get("capabilitiesObj", {})
        locked = capabilities.get("locked", {}).get("value")
        return bool(locked) if locked is not None else None

    async def async_lock(self, **kwargs: Any) -> None:
        """Lock the lock."""
        await self._api.set_capability_value(self._device_id, "locked", True)
        # Immediately refresh this device's state for instant UI feedback
        await self.coordinator.async_refresh_device(self._device_id)

    async def async_unlock(self, **kwargs: Any) -> None:
        """Unlock the lock."""
        await self._api.set_capability_value(self._device_id, "locked", False)
        # Immediately refresh this device's state for instant UI feedback
        await self.coordinator.async_refresh_device(self._device_id)

