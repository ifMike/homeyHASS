"""Data update coordinator for Homey."""
from __future__ import annotations

import asyncio
import json
from datetime import timedelta
import logging
import time
from typing import Any
from urllib.parse import quote

from homeassistant.components import persistent_notification
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import (
    CAPABILITY_REPORT_ISSUE_URL,
    CAPABILITY_TO_PLATFORM,
    CONF_DEVICE_FILTER,
    DOMAIN,
    capability_base,
    is_capability_supported,
)
from .device_info import build_device_identifier, extract_device_id, split_device_identifier
from .homey_api import HomeyAPI

_LOGGER = logging.getLogger(__name__)


def _suggest_platform(cap_type: str, setable: bool | None, base_cap: str = "") -> str:
    """Suggest HA platform for an unknown capability."""
    if cap_type == "boolean":
        return "switch" if setable else "binary_sensor"
    if cap_type == "number":
        return "number" if setable else "sensor"
    if cap_type == "enum":
        return "select" if setable else "sensor"
    if cap_type == "string":
        return "text" if setable else "sensor"
    return "sensor"


class HomeyDataUpdateCoordinator(DataUpdateCoordinator[dict[str, dict[str, Any]]]):
    """Class to manage fetching Homey data."""

    def __init__(
        self,
        hass: HomeAssistant,
        api: HomeyAPI,
        zones: dict[str, dict[str, Any]] | None = None,
        update_interval: timedelta | None = None,
        recovery_cooldown: int | None = None,
        homey_id: str | None = None,
        multi_homey: bool = False,
        config_entry: ConfigEntry | None = None,
    ) -> None:
        """Initialize the coordinator."""
        if update_interval is None:
            # Polling interval: 5-10 seconds is a good balance between responsiveness and system load
            # Socket.IO provides instant updates for supported devices, but Homey may not send Socket.IO events
            # for device changes (affects all device types, not just Zigbee)
            # With 141 devices, polling every 1 second overwhelms the WebSocket API
            # Default to 5 seconds, but will adjust to 5-10 seconds when Socket.IO fails
            update_interval = timedelta(seconds=5)  # 5 seconds - reasonable for UI updates without overwhelming the system
            # Note: Socket.IO real-time updates are enabled if available
            # If Socket.IO fails or doesn't send events, polling will be used (5-10 seconds)
            # Changes made via Homey app will appear within 5-10 seconds via polling (or instantly via Socket.IO if supported)
        
        # Create a logger filter to suppress the "Finished fetching" DEBUG messages
        # The base DataUpdateCoordinator logs these every update, which is too verbose
        import logging
        
        class SuppressFinishedFetchingFilter(logging.Filter):
            """Filter to suppress 'Finished fetching' DEBUG messages."""
            def filter(self, record):
                return "Finished fetching" not in record.getMessage()
        
        # Get the logger and add filter
        coordinator_logger = logging.getLogger(__name__)
        coordinator_logger.addFilter(SuppressFinishedFetchingFilter())
        
        super().__init__(
            hass,
            coordinator_logger,
            name="Homey",
            update_interval=update_interval,
        )
        self.update_interval: timedelta | None = update_interval
        self.api = api
        self.hass = hass
        self.zones = zones or {}
        self.homey_id = homey_id
        self.multi_homey = multi_homey
        self.config_entry = config_entry
        self._previous_device_ids: set[str] = set()
        self._last_recovery_attempt: float = 0.0
        self._recovery_cooldown: int = recovery_cooldown or 300  # seconds
        self._last_no_devices_log: float = 0.0  # Rate limit "No devices" warnings
        self._last_polling_error_log: float = 0.0  # Rate limit polling error logs
        self._ERROR_LOG_INTERVAL: float = 300  # Log at WARNING/ERROR at most every 5 min
        self._fallback_poll_interval: int = (
            update_interval.seconds if update_interval else 10
        )
        self._known_capabilities: set[str] | None = None
        
        # Conditional batching: only batch when multiple updates arrive rapidly
        # Single updates process immediately for instant UI response
        self._pending_sio_updates: dict[str, dict[str, Any]] = {}
        self._sio_update_task: Any = None
        self._sio_batch_delay = 0.015  # 15ms delay for batched updates (only when multiple updates)

        # Register for real-time updates
        self.api.add_device_listener(self._on_device_update)

    async def _async_update_data(self) -> dict[str, dict[str, Any]]:
        """Fetch data from Homey.
        
        Note: This method always uses polling. If Socket.IO is connected, it will
        provide real-time updates via the listener system, but polling continues
        as a fallback to ensure data consistency.
        """
        update_start = time.time()
        try:
            # Refresh zones periodically (every 20 updates = ~100 seconds / ~1.7 minutes)
            if not hasattr(self, "_zone_update_count"):
                self._zone_update_count = 0
            
            self._zone_update_count += 1
            if self._zone_update_count >= 20:
                self.zones = await self.api.get_zones() or {}
                self._zone_update_count = 0
                _LOGGER.debug("Refreshed zones from Homey")
            
            # Periodically check Socket.IO status and adjust polling interval accordingly
            # When Socket.IO is connected, reduce polling frequency (use as safety net only)
            # When Socket.IO is disconnected, use normal polling frequency (5-10 seconds)
            if hasattr(self.api, '_sio_connected'):
                if not self.api._sio_connected:
                    # Socket.IO disconnected - use fallback polling interval (5-10 seconds)
                    # Use configured fallback to reduce API load while still being responsive
                    if self.update_interval != timedelta(seconds=self._fallback_poll_interval):
                        _LOGGER.debug(
                            "Socket.IO disconnected - switching to fallback polling (%d second interval)",
                            self._fallback_poll_interval,
                        )
                        self.update_interval = timedelta(seconds=self._fallback_poll_interval)
                    # Log status check only once per session (not every poll)
                    if not hasattr(self, "_sio_status_logged"):
                        _LOGGER.debug(
                            "Socket.IO status: DISCONNECTED - using fallback polling (%d second interval)",
                            self._fallback_poll_interval,
                        )
                        _LOGGER.debug("Reconnection attempts will continue in background")
                        self._sio_status_logged = True
                    # Trigger reconnection attempt (will happen in background)
                    self.api._start_sio_reconnect_task()
                else:
                    # Socket.IO is connected - reduce polling to safety net interval (60 seconds)
                    if self.update_interval != timedelta(seconds=60):
                        _LOGGER.debug("Socket.IO connected - reducing polling to safety net (60 second interval)")
                        self.update_interval = timedelta(seconds=60)
                        # Reset status logged flag so we log again if it disconnects
                        if hasattr(self, "_sio_status_logged"):
                            delattr(self, "_sio_status_logged")
                    # Socket.IO is connected - check if we've received any events
                    # Note: This is just informational - Socket.IO stays connected regardless
                    if not hasattr(self.api, "_sio_first_event_logged"):
                        # Connected but no events received yet - log this once after a longer delay
                        # Give user time to test (30 seconds = 6 polls at 5s interval, or 30s at 60s interval)
                        if not hasattr(self, "_sio_no_events_logged"):
                            # Wait a bit before logging (give it time to receive events and for user to test)
                            if not hasattr(self, "_sio_check_count"):
                                self._sio_check_count = 0
                            self._sio_check_count += 1
                            # Log after 30 seconds if still no events (informational only - Socket.IO stays connected)
                            # This is just to help diagnose if Homey isn't sending events
                            check_threshold = 6 if self.update_interval == timedelta(seconds=5) else 1  # 6 polls at 5s = 30s, or 1 poll at 60s = 60s
                            if self._sio_check_count >= check_threshold:
                                _LOGGER.debug("Socket.IO connected but no events received yet (this is normal - events arrive when devices change)")
                                _LOGGER.debug("To test: Change a device in Homey app and watch for events in logs")
                                _LOGGER.debug("Socket.IO connection remains active - polling continues as safety net")
                                self._sio_no_events_logged = True
                    else:
                        # Events are arriving - reset counters
                        if hasattr(self, "_sio_no_events_logged"):
                            delattr(self, "_sio_no_events_logged")
                        if hasattr(self, "_sio_check_count"):
                            delattr(self, "_sio_check_count")
                    # Reset status log flag if reconnected
                    if hasattr(self, "_sio_status_logged"):
                        self._sio_status_logged = False
            
            devices = await self.api.get_devices()
            
            # If we suddenly get no devices after previously having data,
            # try a one-time recovery (Homey reboot/network blip).
            if not devices and self._previous_device_ids:
                now = time.time()
                if self._should_attempt_recovery():
                    if now - self._last_no_devices_log >= self._ERROR_LOG_INTERVAL:
                        self._last_no_devices_log = now
                        _LOGGER.warning(
                            "No devices returned from Homey API - attempting automatic reconnect"
                        )
                    else:
                        _LOGGER.debug("No devices - attempting reconnect (rate limited)")
                    await self._attempt_api_recovery()
                    devices = await self.api.get_devices()
                if not devices:
                    if now - self._last_no_devices_log >= self._ERROR_LOG_INTERVAL:
                        self._last_no_devices_log = now
                        _LOGGER.warning(
                            "No devices returned from Homey API - keeping last known devices"
                        )
                    else:
                        _LOGGER.debug("No devices - keeping last known (rate limited)")
                    return self.data or {}
            
            # Detect newly seen capabilities and notify with a report link
            self._detect_new_capabilities(devices)

            # Update device registry for name/room changes
            await self._update_device_registry(devices)
            
            # Track current device IDs for deletion detection
            current_device_ids = set(devices.keys())
            deleted_device_ids = self._previous_device_ids - current_device_ids
            
            # Remove deleted devices from registry
            if deleted_device_ids:
                await self._remove_deleted_devices(deleted_device_ids)
            
            self._previous_device_ids = current_device_ids
            self._last_no_devices_log = 0.0  # Reset on success
            self._last_polling_error_log = 0.0  # Reset on success
            
            update_duration = time.time() - update_start
            # Only log debug info on errors or if update takes unusually long (>1 second)
            if update_duration > 1.0:
                _LOGGER.debug("Device update took %.2f seconds, fetched %d devices", update_duration, len(devices))
            
            return devices
        except Exception as err:
            if isinstance(err, ConfigEntryAuthFailed):
                raise
            now = time.time()
            if self._should_attempt_recovery():
                if now - self._last_polling_error_log >= self._ERROR_LOG_INTERVAL:
                    self._last_polling_error_log = now
                    _LOGGER.warning(
                        "Polling error from Homey API - attempting automatic reconnect: %s",
                        err,
                    )
                else:
                    _LOGGER.debug("Polling error - attempting reconnect (rate limited): %s", err)
                await self._attempt_api_recovery()
                try:
                    devices = await self.api.get_devices()
                    if devices:
                        await self._update_device_registry(devices)
                        current_device_ids = set(devices.keys())
                        deleted_device_ids = self._previous_device_ids - current_device_ids
                        if deleted_device_ids:
                            await self._remove_deleted_devices(deleted_device_ids)
                        self._previous_device_ids = current_device_ids
                        update_duration = time.time() - update_start
                        if update_duration > 1.0:
                            _LOGGER.debug(
                                "Device update took %.2f seconds, fetched %d devices",
                                update_duration,
                                len(devices),
                            )
                        return devices
                except ConfigEntryAuthFailed:
                    raise
                except Exception as recovery_err:
                    _LOGGER.debug(
                        "Polling recovery fetch failed: %s",
                        recovery_err,
                    )
            if now - self._last_polling_error_log >= self._ERROR_LOG_INTERVAL:
                self._last_polling_error_log = now
                _LOGGER.error("Polling failed - error communicating with Homey: %s", err)
            else:
                _LOGGER.debug("Polling failed (rate limited): %s", err)
            raise UpdateFailed(f"Error communicating with Homey: {err}") from err

    def _should_attempt_recovery(self) -> bool:
        """Check if enough time has passed to attempt API recovery."""
        now = time.time()
        if now - self._last_recovery_attempt < self._recovery_cooldown:
            return False
        self._last_recovery_attempt = now
        return True

    async def _attempt_api_recovery(self) -> None:
        """Attempt to re-establish API connection after errors."""
        recovered = False
        try:
            await self.api.disconnect()
        except Exception as err:
            _LOGGER.debug("Failed to disconnect Homey API cleanly: %s", err)
        try:
            await self.api.connect()
            recovered = await self.api.authenticate()
        except Exception as err:
            _LOGGER.debug("Homey API recovery attempt failed: %s", err)
        if recovered:
            _LOGGER.info("Homey API recovery successful - devices should repopulate shortly")

    def _detect_new_capabilities(self, devices: dict[str, dict[str, Any]]) -> None:
        """Detect newly seen capabilities and notify with a GitHub issue link."""
        current_caps: set[str] = set()
        caps_by_device: dict[str, set[str]] = {}

        for device_id, device in devices.items():
            capabilities = device.get("capabilitiesObj", {})
            if not capabilities:
                continue
            cap_ids = set(capabilities.keys())
            caps_by_device[device_id] = cap_ids
            current_caps.update(cap_ids)

        # Initialize baseline on first run to avoid noisy initial notification
        if self._known_capabilities is None:
            self._known_capabilities = current_caps
            return

        new_caps = current_caps - self._known_capabilities
        if not new_caps:
            return

        self._known_capabilities.update(new_caps)
        unknown_caps = {cap_id for cap_id in new_caps if not is_capability_supported(cap_id)}
        if not unknown_caps:
            return

        self._create_capability_notification(unknown_caps, devices, caps_by_device)

    def _create_capability_notification(
        self,
        new_caps: set[str],
        devices: dict[str, dict[str, Any]],
        caps_by_device: dict[str, set[str]],
    ) -> None:
        """Create a persistent notification and GitHub issue link for new capabilities."""
        device_lines: list[str] = []
        body_device_lines: list[str] = []
        for device_id, cap_ids in caps_by_device.items():
            diff = sorted(cap_ids & new_caps)
            if not diff:
                continue
            device = devices.get(device_id, {})
            device_name = device.get("name", "Unknown Device")
            device_class = device.get("class", "unknown")
            driver_uri = device.get("driverUri", "unknown")
            driver_id = device.get("driverId", "unknown")
            app_id = device.get("appId") or "unknown"
            zone_id = device.get("zone", "")
            manufacturer = model = "unknown"
            if driver_uri and driver_uri != "unknown":
                uri = str(driver_uri)
                # Handle homey:app:vendor.model format (e.g. homey:app:me.nanoleaf)
                if uri.startswith("homey:app:"):
                    app_part = uri[len("homey:app:") :].strip()
                    if not app_id or app_id == "unknown":
                        app_id = app_part or app_id
                    dot_parts = app_part.split(".")
                    if len(dot_parts) >= 2:
                        manufacturer = dot_parts[0] or "unknown"
                        model = dot_parts[-1] or "unknown"
                    elif app_part:
                        manufacturer = app_part
                else:
                    parts = uri.split(".")
                    if len(parts) >= 2:
                        manufacturer = parts[0] or "unknown"
                        model = parts[-1] or "unknown"
            capabilities_obj = device.get("capabilitiesObj", {})
            zone_name = ""
            if zone_id and self.zones:
                zone_name = self.zones.get(zone_id, {}).get("name", "")
            device_lines.append(f"- {device_name} ({device_id}): {', '.join(diff)}")
            capability_details: list[str] = []
            for cap_id in diff:
                cap_data = capabilities_obj.get(cap_id, {})
                cap_type = cap_data.get("type", "unknown")
                cap_title = cap_data.get("title")
                cap_setable = cap_data.get("setable")
                cap_getable = cap_data.get("getable")
                cap_units = cap_data.get("units")
                cap_value = cap_data.get("value")
                cap_options = cap_data.get("values") or cap_data.get("options")
                cap_min = cap_data.get("min")
                cap_max = cap_data.get("max")
                cap_step = cap_data.get("step")
                base_cap = capability_base(cap_id)
                known_platform = CAPABILITY_TO_PLATFORM.get(base_cap)
                suggested = _suggest_platform(cap_type, cap_setable, base_cap)
                raw_str = json.dumps(cap_data, default=str)
                raw_json = raw_str[:500] + ("..." if len(raw_str) > 500 else "")
                details = [
                    f"    - id: {cap_id}",
                    f"      type: {cap_type}",
                    f"      base: {base_cap}",
                    f"      known_mapping: {known_platform or 'none'}",
                    f"      suggested_platform: {suggested}",
                ]
                if cap_title is not None:
                    details.append(f"      title: {cap_title}")
                if cap_setable is not None:
                    details.append(f"      setable: {cap_setable}")
                if cap_getable is not None:
                    details.append(f"      getable: {cap_getable}")
                if cap_units:
                    details.append(f"      units: {cap_units}")
                if cap_value is not None:
                    details.append(f"      value: {cap_value}")
                if cap_min is not None:
                    details.append(f"      min: {cap_min}")
                if cap_max is not None:
                    details.append(f"      max: {cap_max}")
                if cap_step is not None:
                    details.append(f"      step: {cap_step}")
                if cap_options:
                    details.append(f"      options: {cap_options}")
                details.append(f"      raw: {raw_json}")
                capability_details.append("\n".join(details))
            body_device_lines.append(
                f"- {device_name}\n"
                f"  - id: {device_id}\n"
                f"  - class: {device_class}\n"
                f"  - driverUri: {driver_uri}\n"
                f"  - driverId: {driver_id}\n"
                f"  - appId: {app_id}\n"
                f"  - manufacturer: {manufacturer}\n"
                f"  - model: {model}\n"
                f"  - zone: {zone_id}\n"
                f"  - zone_name: {zone_name}\n"
                f"  - new capabilities:\n"
                f"{chr(10).join(capability_details)}"
            )

        if not device_lines:
            return

        issue_title = "New Homey capability detected"
        issue_labels = "enhancement"
        body_lines = [
            "## New Homey capability detected",
            "",
            f"New capabilities: {', '.join(sorted(new_caps))}",
            "",
            "### Devices",
            *body_device_lines[:5],
            "",
            "### Notes",
            "- Please describe which entities are missing or incorrect.",
            "- Include screenshots if possible.",
        ]
        issue_body = "\n".join(body_lines)
        issue_url = (
            f"{CAPABILITY_REPORT_ISSUE_URL}"
            f"?labels={quote(issue_labels)}&title={quote(issue_title)}&body={quote(issue_body)}"
        )

        message_lines = [
            "New Homey capabilities detected:",
            *device_lines[:10],
        ]
        if len(device_lines) > 10:
            message_lines.append(f"...and {len(device_lines) - 10} more device(s).")
        message_lines.append("")
        message_lines.append(f"[Report this on GitHub]({issue_url})")

        persistent_notification.async_create(
            self.hass,
            "\n".join(message_lines),
            title="Homey: New capabilities detected",
            notification_id=f"{DOMAIN}_new_capabilities",
        )

    def async_create_test_capability_notification(self) -> None:
        """Create a test notification for capability reporting."""
        devices = self.data or {}
        if not devices:
            persistent_notification.async_create(
                self.hass,
                "No devices available to build a test capability report.",
                title="Homey: Test capability report",
                notification_id=f"{DOMAIN}_test_capabilities",
            )
            return

        # Use the first device as a representative target for the test report
        device_id, device = next(iter(devices.items()))
        caps_by_device = {device_id: {"test_capability"}}
        new_caps = {"test_capability"}
        self._create_capability_notification(new_caps, {device_id: device}, caps_by_device)

    async def _assign_areas_to_devices(self) -> None:
        """Assign areas to devices based on Homey zones during initial setup."""
        if not self.data:
            return
        
        device_registry = dr.async_get(self.hass)
        from homeassistant.helpers import area_registry as ar
        area_registry = ar.async_get(self.hass)
        
        for device_id, device in self.data.items():
            device_entry = device_registry.async_get_device(
                identifiers={build_device_identifier(self.homey_id, device_id, self.multi_homey)}, connections=set()
            )
            
            if not device_entry:
                continue
            
            # Get zone/room information
            zone_id = device.get("zone")
            room_name = None
            if zone_id and self.zones:
                zone = self.zones.get(zone_id)
                if zone:
                    room_name = zone.get("name")
            
            # Assign area if room exists
            if room_name:
                # Find or create area
                area = area_registry.async_get_area_by_name(room_name)
                if area:
                    area_id = area.id
                else:
                    # Create new area
                    area = area_registry.async_create(room_name)
                    area_id = area.id
                
                # Assign area to device if not already assigned
                if device_entry.area_id != area_id:
                    device_registry.async_update_device(
                        device_entry.id,
                        area_id=area_id,
                    )
                    _LOGGER.debug("Assigned device %s to area: %s", device_entry.name, room_name)

    async def _update_device_registry(self, devices: dict[str, dict[str, Any]]) -> None:
        """Update device registry when device names or rooms change."""
        device_registry = dr.async_get(self.hass)
        
        for device_id, device in devices.items():
            device_entry = device_registry.async_get_device(
                identifiers={build_device_identifier(self.homey_id, device_id, self.multi_homey)}, connections=set()
            )
            
            if not device_entry:
                continue
            
            # Get updated device info
            device_name = device.get("name") or "Unknown Device"
            zone_id = device.get("zone")
            room_name = None
            if zone_id and self.zones:
                zone = self.zones.get(zone_id)
                if zone:
                    room_name = zone.get("name")
            
            # Update device name if changed
            if device_entry.name != device_name:
                device_registry.async_update_device(
                    device_entry.id,
                    name=device_name,
                )
                _LOGGER.debug("Updated device name: %s -> %s", device_entry.name, device_name)
            
            # Update device area ONLY if:
            # 1. Device has no area assigned (area_id is None), OR
            # 2. Current area name matches the Homey zone name (was set by integration, not manually changed)
            # This prevents overwriting user-assigned areas
            from homeassistant.helpers import area_registry as ar
            area_registry = ar.async_get(self.hass)
            
            current_area_id = device_entry.area_id
            current_area_name = None
            if current_area_id:
                current_area = area_registry.async_get_area(current_area_id)
                if current_area:
                    current_area_name = current_area.name
            
            # Only update area if device has no area OR current area matches Homey zone
            # This allows the integration to update areas when Homey zones change,
            # but preserves user manual area assignments
            should_update_area = False
            new_area_id = None
            
            if room_name:
                # Find or create area for Homey zone
                area = area_registry.async_get_area_by_name(room_name)
                if area:
                    new_area_id = area.id
                else:
                    # Create new area if it doesn't exist
                    area = area_registry.async_create(room_name)
                    new_area_id = area.id
                
                # Only update if:
                # - Device has no area assigned, OR
                # - Current area name matches the Homey zone name (integration-set area)
                if current_area_id is None:
                    should_update_area = True
                    _LOGGER.debug("Assigning initial area %s to device %s", room_name, device_entry.name)
                elif current_area_name == room_name:
                    # Area matches Homey zone - safe to update if zone changed
                    # (This handles zone renames in Homey)
                    if current_area_id != new_area_id:
                        should_update_area = True
                        _LOGGER.debug("Updating area for device %s: zone name matches, updating area ID", device_entry.name)
                else:
                    # Current area doesn't match Homey zone - user manually changed it
                    # Don't overwrite user's manual assignment
                    _LOGGER.debug(
                        "Skipping area update for device %s: current area '%s' doesn't match Homey zone '%s' (user-managed)",
                        device_entry.name, current_area_name, room_name
                    )
            elif current_area_id is not None:
                # Device has an area but Homey zone is None/empty
                # Don't remove user-assigned areas - only remove if it was integration-set
                # We can't reliably detect this, so we'll leave it as-is
                _LOGGER.debug(
                    "Device %s has area '%s' but no Homey zone - preserving user assignment",
                    device_entry.name, current_area_name
                )
            
            if should_update_area and new_area_id and current_area_id != new_area_id:
                device_registry.async_update_device(
                    device_entry.id,
                    area_id=new_area_id,
                )
                _LOGGER.debug("Updated device area: %s -> %s", current_area_id, new_area_id)

    async def _remove_deleted_devices(self, deleted_device_ids: set[str]) -> None:
        """Remove deleted devices from device registry."""
        device_registry = dr.async_get(self.hass)
        from homeassistant.helpers import entity_registry as er
        entity_registry = er.async_get(self.hass)
        
        for device_id in deleted_device_ids:
            device_entry = device_registry.async_get_device(
                identifiers={build_device_identifier(self.homey_id, device_id, self.multi_homey)}, connections=set()
            )
            
            if device_entry:
                # Remove all entities for this device
                entities = [
                    entry
                    for entry in entity_registry.entities.values()
                    if entry.device_id == device_entry.id
                ]
                for entity_entry in entities:
                    entity_registry.async_remove(entity_entry.entity_id)
                
                # Remove the device
                device_registry.async_remove_device(device_entry.id)
                _LOGGER.info("Removed deleted device: %s", device_id)
    
    async def _remove_unselected_devices(self, entry: Any) -> None:
        """Remove devices that are no longer in device_filter from device registry.
        
        This is called during setup to clean up devices that were removed from
        the device_filter via the options flow or manual deletion.
        """
        from homeassistant.config_entries import ConfigEntry
        
        if not isinstance(entry, ConfigEntry):
            return
        
        device_filter = entry.data.get(CONF_DEVICE_FILTER)
        
        # If device_filter is None, all devices are selected, so nothing to remove
        if device_filter is None:
            return
        
        device_filter_set = set(device_filter)
        device_registry = dr.async_get(self.hass)
        from homeassistant.helpers import entity_registry as er
        entity_registry = er.async_get(self.hass)
        
        # Get all devices for this integration
        # We need to check devices that belong to this config entry
        devices_to_remove = []
        
        # Virtual devices that should never be removed (not real devices from Homey)
        # "flows" is a virtual device for flow buttons
        # "logic" is a virtual device for Homey Logic variables
        virtual_devices = {"flows", "logic"}
        
        # Get all devices and check which ones belong to our integration
        for device_entry in device_registry.devices.values():
            # Check if this device belongs to our integration and this config entry
            for identifier in device_entry.identifiers:
                homey_id, extracted = split_device_identifier(identifier)
                if extracted and (
                    not self.multi_homey or self.homey_id is None or homey_id == self.homey_id
                ):
                    device_id = extracted
                    
                    # Skip virtual devices - they should never be removed
                    if device_id in virtual_devices:
                        break
                    
                    # Check if this device is associated with our config entry
                    # and if it's not in the filter
                    if device_id not in device_filter_set:
                        # Verify this device belongs to our config entry
                        # by checking if it's in the coordinator data or was previously tracked
                        if device_id not in (self.data or {}):
                            # Device not in current data, might be stale
                            # But only remove if it's definitely not in filter
                            devices_to_remove.append((device_entry.id, device_id))
                    break
        
        # Remove devices and their entities
        for device_entry_id, device_id in devices_to_remove:
            device_entry = device_registry.async_get(device_entry_id)
            if device_entry:
                # Verify this device still belongs to our integration
                still_ours = False
                for identifier in device_entry.identifiers:
                    homey_id, extracted = split_device_identifier(identifier)
                    if extracted and extracted == device_id and (
                        not self.multi_homey or self.homey_id is None or homey_id == self.homey_id
                    ):
                        still_ours = True
                        break
                
                if still_ours:
                    # Remove all entities for this device
                    entities = [
                        entry
                        for entry in entity_registry.entities.values()
                        if entry.device_id == device_entry_id
                    ]
                    for entity_entry in entities:
                        entity_registry.async_remove(entity_entry.entity_id)
                    
                    # Remove the device
                    device_registry.async_remove_device(device_entry_id)
                    _LOGGER.info("Removed unselected device from registry: %s", device_id)

    def _on_device_update(self, device_id: str, data: dict[str, Any]) -> None:
        """Handle device update from Socket.IO.
        
        This is called from Socket.IO callbacks which may run in a different thread.
        Uses conditional batching: single updates process immediately, multiple rapid updates are batched.
        Matches async_refresh_device behavior by using async tasks instead of synchronous callbacks.
        """
        if not self.hass.is_running:
            # Fallback: if HA isn't running yet, just update synchronously
            if self.data:
                if device_id in self.data:
                    self.data[device_id].update(data)
                else:
                    self.data[device_id] = data
                self.async_update_listeners()
            return
        
        # Store the latest update for this device (thread-safe dict access)
        self._pending_sio_updates[device_id] = data
        
        # Schedule task creation in the event loop thread (thread-safe)
        def schedule_update_task():
            """Schedule async task in the event loop thread."""
            # Check if there's already a pending batch task
            if self._sio_update_task and not self._sio_update_task.done():
                # Multiple updates arriving rapidly - cancel and reschedule with batching
                self._sio_update_task.cancel()
                self._sio_update_task = self.hass.async_create_task(
                    self._async_process_batched_sio_updates()
                )
            else:
                # Single update or first update - process immediately using async task
                # This matches async_refresh_device behavior (async context)
                if len(self._pending_sio_updates) == 1:
                    # Only one update, process immediately in async context
                    self._sio_update_task = self.hass.async_create_task(
                        self._async_process_sio_update_immediate()
                    )
                else:
                    # Multiple updates queued, batch them
                    self._sio_update_task = self.hass.async_create_task(
                        self._async_process_batched_sio_updates()
                    )
        
        # Schedule task creation in the event loop thread (thread-safe)
        self.hass.loop.call_soon_threadsafe(schedule_update_task)
    
    async def _async_process_sio_update_immediate(self) -> None:
        """Process Socket.IO update immediately in async context (matches async_refresh_device)."""
        if not self._pending_sio_updates or not self.data:
            return
        
        # Log Socket.IO update for debugging
        import time
        update_start = time.time()
        device_ids = list(self._pending_sio_updates.keys())
        
        # Update coordinator data with pending update
        # This matches exactly what async_refresh_device does
        for update_device_id, update_data in self._pending_sio_updates.items():
            if update_device_id in self.data:
                self.data[update_device_id].update(update_data)
            else:
                self.data[update_device_id] = update_data
        
        # Clear pending updates
        self._pending_sio_updates.clear()
        
        # Notify listeners immediately (same as async_refresh_device)
        # Being in async context ensures callbacks execute immediately
        self.async_update_listeners()
        
        # Log Socket.IO update timing
        update_duration = time.time() - update_start
        _LOGGER.debug(
            "Socket.IO update processed for device(s) %s in %.3f seconds - UI should update immediately",
            ", ".join(device_ids[:3]) + ("..." if len(device_ids) > 3 else ""),
            update_duration
        )
    
    async def _async_process_batched_sio_updates(self) -> None:
        """Process batched Socket.IO updates after a short delay (for rapid successive updates)."""
        try:
            # Wait a short delay to batch rapid updates
            await asyncio.sleep(self._sio_batch_delay)
            
            # Process all pending updates (same as immediate processing)
            if not self._pending_sio_updates or not self.data:
                return
            
            # Update coordinator data with all pending updates
            for update_device_id, update_data in self._pending_sio_updates.items():
                if update_device_id in self.data:
                    self.data[update_device_id].update(update_data)
                else:
                    self.data[update_device_id] = update_data
            
            # Clear pending updates
            self._pending_sio_updates.clear()
            
            # Notify listeners (in async context, callbacks execute immediately)
            self.async_update_listeners()
        except asyncio.CancelledError:
            # Task was cancelled - this is expected when new updates arrive
            # The next scheduled task will process the pending updates
            pass
    
    async def async_refresh_device(self, device_id: str) -> None:
        """Immediately refresh a specific device's state from Homey API.
        
        This is called after setting a capability value to get immediate feedback
        instead of waiting for the next polling interval.
        
        Note: This only works for changes made via Home Assistant. Changes made via
        the Homey app will only be detected during the next polling cycle (every 5 seconds).
        """
        refresh_start = time.time()
        try:
            device_data = await self.api.get_device(device_id)
            if device_data and self.data:
                # Update the device data in coordinator
                self.data[device_id] = device_data
                # Notify listeners immediately
                self.async_update_listeners()
                refresh_duration = time.time() - refresh_start
                _LOGGER.debug("Immediately refreshed device %s in %.2f seconds", device_id, refresh_duration)
        except Exception as err:
            _LOGGER.debug("Error refreshing device %s: %s", device_id, err)
            # Fall back to regular refresh request
            await self.async_request_refresh()


class HomeyLogicUpdateCoordinator(DataUpdateCoordinator[dict[str, dict[str, Any]]]):
    """Class to manage fetching Homey logic variables."""

    def __init__(
        self,
        hass: HomeAssistant,
        api: HomeyAPI,
        update_interval: timedelta | None = None,
    ) -> None:
        """Initialize the logic coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name="Homey Logic",
            update_interval=update_interval,
        )
        self.api = api

    async def _async_update_data(self) -> dict[str, dict[str, Any]]:
        """Fetch logic variables from Homey."""
        try:
            return await self.api.get_logic_variables()
        except Exception as err:
            _LOGGER.debug("Logic variables update failed: %s", err)
            raise UpdateFailed(f"Error communicating with Homey logic API: {err}") from err

