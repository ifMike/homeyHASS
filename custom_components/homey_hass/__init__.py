"""The Homey integration."""
from __future__ import annotations

import logging
from datetime import timedelta
from pathlib import Path
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from homeassistant.components import persistent_notification
from homeassistant.helpers import selector
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.update_coordinator import UpdateFailed
import voluptuous as vol

from .const import (
    CONF_HOST,
    CONF_DEVICE_FILTER,
    CONF_POLL_INTERVAL,
    CONF_RECOVERY_COOLDOWN,
    SERVICE_TEST_CAPABILITY_REPORT,
    SERVICE_SET_DEVICE_TEMPERATURE_UNIT,
    CONF_TEMPERATURE_UNIT_OVERRIDES,
    DOMAIN,
    UNIQUE_ID_PREFIX,
    DEFAULT_POLL_INTERVAL,
    DEFAULT_RECOVERY_COOLDOWN,
)
from .coordinator import HomeyDataUpdateCoordinator, HomeyLogicUpdateCoordinator
from .device_info import build_device_identifier, extract_device_id, extract_unique_id_primary
from .homey_api import HomeyAPI

_LOGGER = logging.getLogger(__name__)

# Module loaded

def _check_installation_conflict() -> None:
    """Check for conflicting installation methods and warn if detected.
    
    This detects if there's a manual installation conflicting with HACS,
    or vice versa, and logs a warning to help users troubleshoot.
    """
    try:
        # Get the path to this integration's directory
        integration_dir = Path(__file__).parent.resolve()
        
        # Check for HACS metadata file (HACS creates .hacs.json in custom_components/)
        # Path structure: config/custom_components/homey_hass/__init__.py
        # So custom_components is parent.parent
        custom_components_dir = integration_dir.parent
        hacs_json = custom_components_dir / ".hacs.json"
        hacs_installed = hacs_json.exists()
        
        # Check for git directory in custom_components (indicates manual git clone of entire repo)
        # Path: config/custom_components/.git
        git_dir = custom_components_dir / ".git"
        manual_git = git_dir.exists()
        
        # Check for git directory in integration folder itself (another manual install pattern)
        integration_git = integration_dir / ".git"
        integration_has_git = integration_git.exists()
        
        if hacs_installed and (manual_git or integration_has_git):
            _LOGGER.warning(
                "⚠️  Installation conflict detected: You appear to have both HACS and manual installation. "
                "This can cause update issues. Please remove the manual installation folder "
                "(%s) and restart Home Assistant, then update via HACS.",
                integration_dir
            )
        elif hacs_installed:
            _LOGGER.debug("HACS installation detected - updates should be managed via HACS")
        elif manual_git or integration_has_git:
            _LOGGER.debug("Manual installation detected - updates should be done manually")
    except Exception as err:
        # Don't let installation check break the integration
        _LOGGER.debug("Could not check installation method: %s", err)

# Run check on module load
_check_installation_conflict()


def filter_devices(devices: dict[str, dict[str, Any]], device_filter: list[str] | None) -> dict[str, dict[str, Any]]:
    """Filter devices based on device_filter configuration."""
    if device_filter:
        return {did: dev for did, dev in devices.items() if did in device_filter}
    return devices

PLATFORMS: list[Platform] = [
    Platform.LIGHT,
    Platform.SWITCH,
    Platform.COVER,
    Platform.CLIMATE,
    Platform.SENSOR,
    Platform.BINARY_SENSOR,
    Platform.FAN,
    Platform.LOCK,
    Platform.MEDIA_PLAYER,
    Platform.BUTTON,  # For Homey flows and device buttons
    Platform.NUMBER,
    Platform.SELECT,
    Platform.TEXT,
    Platform.SCENE,
    Platform.VACUUM,
]


async def async_remove_config_entry_device(
    hass: HomeAssistant, config_entry: ConfigEntry, device_entry: dr.DeviceEntry
) -> bool:
    """Handle removal of a device from the device registry.
    
    This allows users to manually delete devices from the Devices page.
    When a device is deleted, we remove it from the device_filter.
    """
    device_registry = dr.async_get(hass)
    
    # Find the device_id from the device entry identifiers
    device_id = None
    for identifier in device_entry.identifiers:
        extracted = extract_device_id(identifier)
        if extracted:
            device_id = extracted
            break
    
    if not device_id:
        _LOGGER.warning("Could not find device_id for device %s", device_entry.id)
        return False
    
    # Get current device filter
    current_filter = config_entry.data.get(CONF_DEVICE_FILTER)
    
    # If device_filter is None, it means all devices are selected
    # In that case, we need to get all devices and create a filter excluding this one
    if current_filter is None:
        # Get all devices from coordinator or API
        if config_entry.entry_id in hass.data.get(DOMAIN, {}):
            coordinator = hass.data[DOMAIN][config_entry.entry_id].get("coordinator")
            api = hass.data[DOMAIN][config_entry.entry_id].get("api")
            
            # Try to get devices from coordinator first (most up-to-date)
            if coordinator and coordinator.data:
                all_device_ids = set(coordinator.data.keys())
            elif api:
                # Fallback to API if coordinator doesn't have data yet
                try:
                    devices = await api.get_devices()
                    all_device_ids = set(devices.keys())
                except Exception:
                    _LOGGER.warning("Could not fetch devices to update filter")
                    all_device_ids = set()
            else:
                all_device_ids = set()
            
            # Remove the device being deleted
            all_device_ids.discard(device_id)
            new_filter = list(all_device_ids) if all_device_ids else []
        else:
            # Integration not loaded - fetch devices from API directly
            try:
                api = HomeyAPI(
                    host=config_entry.data["host"],
                    token=config_entry.data["token"],
                    preferred_endpoint=config_entry.data.get("working_endpoint"),
                )
                await api.connect()
                devices = await api.get_devices()
                all_device_ids = set(devices.keys())
                all_device_ids.discard(device_id)
                new_filter = list(all_device_ids) if all_device_ids else []
                await api.disconnect()
            except Exception as err:
                _LOGGER.warning("Could not fetch devices to update filter: %s", err)
                # Can't determine all devices, create filter with just this device excluded
                # This will be corrected on next reload
                new_filter = []
    else:
        # Remove device_id from filter
        new_filter = [did for did in current_filter if did != device_id]
    
    # Update config entry with new filter
    new_data = {**config_entry.data}
    new_data[CONF_DEVICE_FILTER] = new_filter if new_filter else None
    
    hass.config_entries.async_update_entry(config_entry, data=new_data)
    
    _LOGGER.info("Removed device %s from device filter", device_id)
    
    # Return True to indicate we handled the removal
    # Home Assistant will then remove the device and entities
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Homey from a config entry."""
    hass.data.setdefault(DOMAIN, {})

    # Initialize Homey API client
    api = HomeyAPI(
        host=entry.data["host"],
        token=entry.data["token"],
        preferred_endpoint=entry.data.get("working_endpoint"),  # Use endpoint that worked in config flow
    )

    try:
        await api.connect()
        # Authentication already validated in config flow, but verify we can get devices
        # If system endpoint fails, try devices endpoint as fallback
        auth_result = await api.authenticate()
        if not auth_result:
            _LOGGER.warning("System endpoint authentication failed, but continuing since config flow validated connection")
            # Try to get devices to verify connection works
            devices = await api.get_devices()
            if not devices:
                _LOGGER.error("Cannot access Homey API - no devices endpoint accessible")
                return False
    except Exception as err:
        _LOGGER.error("Failed to connect to Homey: %s", err, exc_info=True)
        return False

    # Fetch zones (rooms) for device organization
    zones = await api.get_zones()
    homey_id = api.homey_id or entry.data.get("host")
    if api.homey_id is None:
        _LOGGER.warning(
            "Homey ID not available yet; falling back to host for device scoping (%s). "
            "If this host changes later, devices may need rescoping.",
            entry.data.get("host"),
        )
        persistent_notification.async_create(
            hass,
            "Homey ID not available yet; using host for device scoping. "
            "Once Homey ID is available, devices will be rescoped automatically.",
            title="Homey: Pending device rescope",
            notification_id=f"{DOMAIN}_pending_rescope",
        )

    # Abort setup if another entry points to the same Homey - prevents duplicate entities
    for other_entry in hass.config_entries.async_entries(DOMAIN):
        if other_entry.entry_id == entry.entry_id:
            continue
        other_homey_id = other_entry.data.get("homey_id") or other_entry.data.get(CONF_HOST)
        if other_homey_id == homey_id:
            _LOGGER.error(
                "Cannot set up Homey: entry %s already targets the same hub (%s). "
                "Remove the duplicate from Settings → Devices & Services.",
                other_entry.entry_id,
                homey_id,
            )
            persistent_notification.async_create(
                hass,
                f"Homey integration cannot load: you have two entries for the same hub. "
                f"Go to Settings → Devices & Services → Homey and remove the duplicate entry.",
                title="Homey: Remove duplicate hub entry",
                notification_id=f"{DOMAIN}_duplicate_hub_{entry.entry_id}",
            )
            await api.disconnect()
            return False
        if other_entry.data.get(CONF_HOST) == entry.data.get(CONF_HOST):
            _LOGGER.error(
                "Cannot set up Homey: entry %s uses the same host (%s). "
                "Remove the duplicate from Settings → Devices & Services.",
                other_entry.entry_id,
                entry.data.get(CONF_HOST),
            )
            persistent_notification.async_create(
                hass,
                f"Homey integration cannot load: you have two entries for the same host. "
                f"Go to Settings → Devices & Services → Homey and remove the duplicate entry.",
                title="Homey: Remove duplicate hub entry",
                notification_id=f"{DOMAIN}_duplicate_host_{entry.entry_id}",
            )
            await api.disconnect()
            return False

    # Enable multi-homey mode only when more than one hub is configured
    entries = hass.config_entries.async_entries(DOMAIN)
    multi_hub = len(entries) > 1

    if multi_hub:
        hass.data[DOMAIN]["multi_homey_enabled"] = True
        # Only run migration + notifications if not already done (persisted in entry data)
        migration_already_done = any(e.data.get("multi_homey_enabled") for e in entries)
        if not migration_already_done:
            await _async_enable_multi_homey(hass)
    
    # Create coordinator (pass zones so it can update device registry)
    poll_interval = entry.options.get(CONF_POLL_INTERVAL, DEFAULT_POLL_INTERVAL)
    recovery_cooldown = entry.options.get(CONF_RECOVERY_COOLDOWN, DEFAULT_RECOVERY_COOLDOWN)
    coordinator = HomeyDataUpdateCoordinator(
        hass,
        api,
        zones,
        update_interval=timedelta(seconds=poll_interval),
        recovery_cooldown=recovery_cooldown,
        homey_id=homey_id,
        multi_homey=hass.data[DOMAIN].get("multi_homey_enabled", False),
        config_entry=entry,
    )
    await coordinator.async_config_entry_first_refresh()

    # Create logic variables coordinator (non-fatal if unavailable or permissions missing)
    logic_coordinator = HomeyLogicUpdateCoordinator(
        hass,
        api,
        update_interval=timedelta(seconds=poll_interval),
    )
    try:
        await logic_coordinator.async_config_entry_first_refresh()
    except UpdateFailed as err:
        _LOGGER.debug("Logic variables unavailable during setup: %s", err)

    # Persist resolved homey_id for future migrations
    if entry.data.get("homey_id") != homey_id:
        hass.config_entries.async_update_entry(
            entry, data={**entry.data, "homey_id": homey_id}
        )

    hass.data[DOMAIN][entry.entry_id] = {
        "api": api,
        "coordinator": coordinator,
        "logic_coordinator": logic_coordinator,
        "zones": coordinator.zones,  # Use zones from coordinator (will be updated periodically)
        "homey_id": api.homey_id or entry.data.get("host"),
        "multi_homey": hass.data[DOMAIN].get("multi_homey_enabled", False),
    }

    # Register service to trigger test capability report (once per hass)
    if not hass.data[DOMAIN].get("services_registered"):
        async def async_test_capability_report(call) -> None:
            """Create a test notification for capability reporting."""
            entry_id = call.data.get("entry_id")
            entry_data = None

            if entry_id:
                entry_data = hass.data[DOMAIN].get(entry_id)
            else:
                # Use the first available entry
                if hass.data[DOMAIN]:
                    for data_key, data_value in hass.data[DOMAIN].items():
                        if isinstance(data_value, dict) and "coordinator" in data_value:
                            entry_data = data_value
                            break

            if not entry_data:
                _LOGGER.error("No Homey entry available to run test capability report")
                return

            coordinator_instance = entry_data.get("coordinator")
            if not coordinator_instance:
                _LOGGER.error("Homey coordinator not available for test capability report")
                return

            coordinator_instance.async_create_test_capability_notification()

        hass.services.async_register(
            DOMAIN,
            SERVICE_TEST_CAPABILITY_REPORT,
            async_test_capability_report,
            schema=vol.Schema({vol.Optional("entry_id"): cv.string}),
        )

        async def async_rename_entities_to_titles(call) -> None:
            """Rename Homey entity display names to capability titles."""
            entry_id = call.data.get("entry_id")
            entry_data = None

            if entry_id:
                entry_data = hass.data[DOMAIN].get(entry_id)
            else:
                # Use the first available entry
                if hass.data[DOMAIN]:
                    for data_key, data_value in hass.data[DOMAIN].items():
                        if isinstance(data_value, dict) and "coordinator" in data_value:
                            entry_data = data_value
                            entry_id = data_key
                            break

            if not entry_data or not entry_id:
                _LOGGER.error("No Homey entry available to rename entities")
                return

            coordinator_instance = entry_data.get("coordinator")
            if not coordinator_instance:
                _LOGGER.error("Homey coordinator not available for renaming entities")
                return

            devices = coordinator_instance.data or {}
            entity_registry = er.async_get(hass)
            device_registry = dr.async_get(hass)
            homey_id = entry_data.get("homey_id")
            multi_homey = entry_data.get("multi_homey", False)

            updated = 0
            for entity_entry in entity_registry.entities.values():
                if entity_entry.platform != DOMAIN:
                    continue
                if entity_entry.config_entry_id != entry_id:
                    continue
                if not entity_entry.unique_id or not entity_entry.device_id:
                    continue

                device_entry = device_registry.async_get(entity_entry.device_id)
                if not device_entry:
                    continue

                device_id = None
                for identifier in device_entry.identifiers:
                    device_id = extract_device_id(identifier)
                    if device_id:
                        break

                if not device_id:
                    continue

                device = devices.get(device_id)
                if not device:
                    continue

                prefix = (
                    f"{UNIQUE_ID_PREFIX}{homey_id}_{device_id}_"
                    if (multi_homey and homey_id)
                    else f"{UNIQUE_ID_PREFIX}{device_id}_"
                )
                if not entity_entry.unique_id.startswith(prefix):
                    continue

                capability_id = entity_entry.unique_id[len(prefix):]
                if capability_id == "onoff":
                    continue

                capability_data = device.get("capabilitiesObj", {}).get(capability_id, {})
                title = capability_data.get("title")
                if not title:
                    continue

                new_name = f"{device.get('name', 'Unknown')} {title}"
                if entity_entry.name == new_name or entity_entry.original_name == new_name:
                    continue

                entity_registry.async_update_entity(entity_entry.entity_id, name=new_name)
                updated += 1

            _LOGGER.info("Renamed %d Homey entities to capability titles", updated)

        hass.services.async_register(
            DOMAIN,
            "rename_entities_to_titles",
            async_rename_entities_to_titles,
            schema=vol.Schema({vol.Optional("entry_id"): cv.string}),
        )

        async def async_set_device_temperature_unit(call) -> None:
            """Override temperature unit for a device (Homey metadata wrong/missing)."""
            device_id = call.data["device_id"]
            unit = call.data["unit"]
            entry_id = call.data.get("entry_id")
            target_entry = None

            if entry_id:
                target_entry = hass.config_entries.async_get_entry(entry_id)
            else:
                for candidate in hass.config_entries.async_entries(DOMAIN):
                    overrides = candidate.options.get(
                        CONF_TEMPERATURE_UNIT_OVERRIDES, {}
                    )
                    if device_id in overrides or target_entry is None:
                        target_entry = candidate
                if len(hass.config_entries.async_entries(DOMAIN)) == 1:
                    target_entry = hass.config_entries.async_entries(DOMAIN)[0]

            if not target_entry:
                _LOGGER.error(
                    "No Homey config entry found for temperature unit override"
                )
                return

            overrides = dict(
                target_entry.options.get(CONF_TEMPERATURE_UNIT_OVERRIDES, {})
            )
            if str(unit).strip().lower() in ("auto", "automatic", "homey"):
                overrides.pop(device_id, None)
            else:
                overrides[device_id] = str(unit).strip().lower()

            hass.config_entries.async_update_entry(
                target_entry,
                options={
                    **target_entry.options,
                    CONF_TEMPERATURE_UNIT_OVERRIDES: overrides,
                },
            )
            await hass.config_entries.async_reload(target_entry.entry_id)
            _LOGGER.info(
                "Updated temperature unit override for device %s to %s",
                device_id,
                unit,
            )

        hass.services.async_register(
            DOMAIN,
            SERVICE_SET_DEVICE_TEMPERATURE_UNIT,
            async_set_device_temperature_unit,
            schema=vol.Schema(
                {
                    vol.Required("device_id"): cv.string,
                    vol.Required("unit"): cv.string,
                    vol.Optional("entry_id"): cv.string,
                }
            ),
        )
        hass.data[DOMAIN]["services_registered"] = True

    # Forward the setup to the platforms
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Refresh zones and assign areas to devices based on Homey zones (after entities are created)
    coordinator.zones = await api.get_zones() or {}
    await coordinator._assign_areas_to_devices()
    
    # Remove devices that are no longer in device_filter
    await coordinator._remove_unselected_devices(entry)

    # Register service to trigger flows
    async def async_trigger_flow(call) -> None:
        """Service to trigger a Homey flow."""
        # Get API from the entry data
        entry_data = hass.data[DOMAIN].get(entry.entry_id)
        if not entry_data or "api" not in entry_data:
            _LOGGER.error("Homey API not available")
            return
        
        api_instance = entry_data["api"]
        flow_id = call.data.get("flow_id")
        flow_name = call.data.get("flow_name")
        entity_id = call.data.get("entity_id")
        
        # If entity_id provided, extract flow_id from the entity
        if entity_id:
            # Handle both full entity_id (e.g., "button.sova") and just the entity name
            entity_id_str = str(entity_id)
            if not entity_id_str.startswith("button."):
                entity_id_str = f"button.{entity_id_str}"
            
            entity_registry = dr.async_get(hass)
            entity = entity_registry.async_get(entity_id_str)
            if entity and entity.platform == DOMAIN and entity.unique_id:
                flow_id = extract_unique_id_primary(
                    entity.unique_id,
                    "flow",
                    homey_id=entry_data.get("homey_id"),
                    multi_homey=entry_data.get("multi_homey", False),
                )
                if flow_id:
                    _LOGGER.debug("Extracted flow_id %s from entity %s", flow_id, entity_id_str)
            else:
                # If entity not found, try to use entity_id as flow_name
                _LOGGER.debug("Entity %s not found in registry, trying as flow_name", entity_id_str)
                flow_name = entity_id_str.replace("button.", "").strip()
        
        if not flow_id and not flow_name:
            # Provide helpful error message with what was actually provided
            provided_data = {k: v for k, v in call.data.items() if v is not None and v != ""}
            _LOGGER.error(
                "homey_hass.trigger_flow service called without required parameters. "
                "Either 'entity_id', 'flow_id', or 'flow_name' must be provided. "
                "Provided data: %s. "
                "Example: service: homey_hass.trigger_flow, data: {entity_id: 'button.sova'} or {flow_name: 'Sova'}",
                provided_data
            )
            return
        
        # If flow_name provided, find flow_id
        if flow_name and not flow_id:
            flows = await api_instance.get_flows()
            flow_name_normalized = flow_name.strip().lower()
            available_flow_names = []
            
            for fid, flow in flows.items():
                flow_display_name = flow.get("name", "Unknown")
                available_flow_names.append(flow_display_name)
                
                # Try exact match first
                if flow_display_name == flow_name:
                    flow_id = fid
                    break
                
                # Try case-insensitive match
                if flow_display_name.strip().lower() == flow_name_normalized:
                    flow_id = fid
                    break
            
            if not flow_id:
                _LOGGER.error("Flow not found: '%s'. Available flows: %s", flow_name, ", ".join(available_flow_names[:10]))
                return
        
        success = await api_instance.trigger_flow(flow_id)
        if success:
            _LOGGER.info("Triggered Homey flow: %s", flow_id)
        else:
            _LOGGER.error("Failed to trigger Homey flow: %s", flow_id)

    # Register service with schema that includes entity selector for flow buttons
    # The EntitySelector will show a dropdown of available Homey flow button entities
    # Note: In button card UI, you may need to manually enter entity_id if dropdown doesn't appear
    # Format: button.<flow_name> (e.g., button.sova)
    
    hass.services.async_register(
        DOMAIN,
        "trigger_flow",
        async_trigger_flow,
        schema=vol.Schema({
            vol.Optional("entity_id"): vol.Any(
                selector.EntitySelector(
                    selector.EntitySelectorConfig(
                        domain="button",
                        integration=DOMAIN,
                        multiple=False,
                    )
                ),
                vol.Coerce(str),  # Allow string input as fallback
            ),
            vol.Optional("flow_id"): selector.TextSelector(
                selector.TextSelectorConfig(type="text")
            ),
            vol.Optional("flow_name"): selector.TextSelector(
                selector.TextSelectorConfig(type="text")
            ),
        }),
    )

    # Register service to enable flows
    async def async_enable_flow(call) -> None:
        """Service to enable a Homey flow."""
        entry_data = hass.data[DOMAIN].get(entry.entry_id)
        if not entry_data or "api" not in entry_data:
            _LOGGER.error("Homey API not available")
            return
        
        api_instance = entry_data["api"]
        flow_id = call.data.get("flow_id")
        flow_name = call.data.get("flow_name")
        
        if not flow_id and not flow_name:
            _LOGGER.error("Either flow_id or flow_name must be provided")
            return
        
        # If flow_name provided, find flow_id
        if flow_name and not flow_id:
            flows = await api_instance.get_flows()
            flow_name_normalized = flow_name.strip().lower()
            
            for fid, flow in flows.items():
                flow_display_name = flow.get("name", "Unknown")
                if flow_display_name == flow_name or flow_display_name.strip().lower() == flow_name_normalized:
                    flow_id = fid
                    break
            
            if not flow_id:
                _LOGGER.error("Flow not found: '%s'", flow_name)
                return
        
        success = await api_instance.enable_flow(flow_id)
        if success:
            _LOGGER.info("Enabled Homey flow: %s", flow_id)
        else:
            _LOGGER.error("Failed to enable Homey flow: %s", flow_id)

    # Register service to disable flows
    async def async_disable_flow(call) -> None:
        """Service to disable a Homey flow."""
        entry_data = hass.data[DOMAIN].get(entry.entry_id)
        if not entry_data or "api" not in entry_data:
            _LOGGER.error("Homey API not available")
            return
        
        api_instance = entry_data["api"]
        flow_id = call.data.get("flow_id")
        flow_name = call.data.get("flow_name")
        
        if not flow_id and not flow_name:
            _LOGGER.error("Either flow_id or flow_name must be provided")
            return
        
        # If flow_name provided, find flow_id
        if flow_name and not flow_id:
            flows = await api_instance.get_flows()
            flow_name_normalized = flow_name.strip().lower()
            
            for fid, flow in flows.items():
                flow_display_name = flow.get("name", "Unknown")
                if flow_display_name == flow_name or flow_display_name.strip().lower() == flow_name_normalized:
                    flow_id = fid
                    break
            
            if not flow_id:
                _LOGGER.error("Flow not found: '%s'", flow_name)
                return
        
        success = await api_instance.disable_flow(flow_id)
        if success:
            _LOGGER.info("Disabled Homey flow: %s", flow_id)
        else:
            _LOGGER.error("Failed to disable Homey flow: %s", flow_id)

    hass.services.async_register(DOMAIN, "enable_flow", async_enable_flow)
    hass.services.async_register(DOMAIN, "disable_flow", async_disable_flow)

    return True


async def async_migrate_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Migrate old device identifiers and entity unique IDs."""
    if entry.version >= 3:
        return True

    # Skip device ID migration when multi-homey isn't enabled, but still migrate entity unique_ids.
    multi_homey_enabled = hass.data.get(DOMAIN, {}).get("multi_homey_enabled")
    homey_id = entry.data.get("homey_id") or entry.data.get(CONF_HOST)
    if not homey_id:
        _LOGGER.debug("Skipping migration: missing homey_id")
        return True

    _LOGGER.info("Migrating Homey config entry from version %s", entry.version)

    device_registry = dr.async_get(hass)
    entity_registry = er.async_get(hass)

    # Update entry data with resolved homey_id for future lookups
    if entry.data.get("homey_id") != homey_id:
        hass.config_entries.async_update_entry(
            entry,
            data={**entry.data, "homey_id": homey_id},
        )

    # Reattach entities for this entry to a Homey-scoped device entry
    if multi_homey_enabled:
        for entity_entry in entity_registry.entities.values():
            config_entry_id = getattr(entity_entry, "config_entry_id", None)
            if config_entry_id != entry.entry_id:
                continue

            if not entity_entry.device_id:
                continue

            device_entry = device_registry.async_get(entity_entry.device_id)
            if not device_entry:
                continue

            # Find the legacy device_id for this integration
            legacy_device_id = None
            already_scoped = False
            for identifier in device_entry.identifiers:
                if identifier[0] != DOMAIN:
                    continue
                legacy_device_id = extract_device_id(identifier)
                if legacy_device_id and ":" in identifier[1]:
                    already_scoped = True
                    break

            if not legacy_device_id or already_scoped:
                continue

            target_identifier = build_device_identifier(homey_id, legacy_device_id, True)
            target_device = device_registry.async_get_device(
                identifiers={target_identifier}, connections=set()
            )
            if not target_device:
                target_device = device_registry.async_get_or_create(
                    config_entry_id=entry.entry_id,
                    identifiers={target_identifier},
                    manufacturer=device_entry.manufacturer,
                    model=device_entry.model,
                    name=device_entry.name,
                    suggested_area=device_entry.suggested_area,
                )

            entity_registry.async_update_entity(
                entity_entry.entity_id, device_id=target_device.id
            )

    # Clean up legacy device entries with unscoped identifiers
    if multi_homey_enabled:
        legacy_devices = []
        for device_entry in device_registry.devices.values():
            for identifier in device_entry.identifiers:
                if identifier[0] != DOMAIN:
                    continue
                if ":" in identifier[1]:
                    continue
                legacy_devices.append(device_entry)
                break

        for device_entry in legacy_devices:
            # Only remove if no entities are still attached
            has_entities = any(
                ent.device_id == device_entry.id
                for ent in entity_registry.entities.values()
            )
            if not has_entities:
                device_registry.async_remove_device(device_entry.id)

    # Update entity unique IDs to include the Homey ID for this entry.
    updated = 0
    for entity_entry in list(entity_registry.entities.values()):
        config_entry_id = getattr(entity_entry, "config_entry_id", None)
        if config_entry_id != entry.entry_id:
            continue
        if not entity_entry.unique_id:
            continue
        if not entity_entry.unique_id.startswith(UNIQUE_ID_PREFIX):
            continue
        if entity_entry.unique_id.startswith(f"{UNIQUE_ID_PREFIX}{homey_id}_"):
            continue

        suffix = entity_entry.unique_id[len(UNIQUE_ID_PREFIX):]
        new_unique_id = f"{UNIQUE_ID_PREFIX}{homey_id}_{suffix}"
        conflict = any(
            ent.unique_id == new_unique_id and ent.config_entry_id == entry.entry_id
            for ent in entity_registry.entities.values()
        )
        if conflict:
            _LOGGER.warning(
                "Skipping unique_id migration for %s due to conflict: %s",
                entity_entry.entity_id,
                new_unique_id,
            )
            continue

        entity_registry.async_update_entity(
            entity_entry.entity_id, new_unique_id=new_unique_id
        )
        updated += 1

    entry.version = 3
    _LOGGER.info(
        "Homey config entry migration complete (updated %d unique IDs)", updated
    )
    return True


async def _async_rescope_devices(
    hass: HomeAssistant, entry: ConfigEntry, new_homey_id: str
) -> None:
    """Rescope devices when Homey ID becomes available or multi-homey is enabled."""
    _LOGGER.info("Rescoping Homey devices to %s", new_homey_id)
    device_registry = dr.async_get(hass)
    entity_registry = er.async_get(hass)

    # First, reattach entities for this entry
    for entity_entry in entity_registry.entities.values():
        config_entry_id = getattr(entity_entry, "config_entry_id", None)
        if config_entry_id != entry.entry_id:
            continue
        if not entity_entry.device_id:
            continue

        device_entry = device_registry.async_get(entity_entry.device_id)
        if not device_entry:
            continue

        legacy_device_id = None
        already_scoped = False
        for identifier in device_entry.identifiers:
            if identifier[0] != DOMAIN:
                continue
            value = identifier[1]
            legacy_device_id = extract_device_id(identifier)
            if value.startswith(f"{new_homey_id}:"):
                already_scoped = True
                break

        if not legacy_device_id or already_scoped:
            continue

        target_identifier = build_device_identifier(new_homey_id, legacy_device_id, True)
        target_device = device_registry.async_get_device(
            identifiers={target_identifier}, connections=set()
        )
        if not target_device:
            target_device = device_registry.async_get_or_create(
                config_entry_id=entry.entry_id,
                identifiers={target_identifier},
                manufacturer=device_entry.manufacturer,
                model=device_entry.model,
                name=device_entry.name,
                suggested_area=device_entry.suggested_area,
            )

        entity_registry.async_update_entity(
            entity_entry.entity_id, device_id=target_device.id
        )

    # Then, handle entities without config_entry_id but tied to our legacy devices
    for device_entry in device_registry.devices.values():
        legacy_device_id = None
        already_scoped = False
        for identifier in device_entry.identifiers:
            if identifier[0] != DOMAIN:
                continue
            legacy_device_id = extract_device_id(identifier)
            if ":" in identifier[1]:
                already_scoped = True
            break

        if not legacy_device_id or already_scoped:
            continue

        # Reattach all entities from this legacy device to the scoped device
        target_identifier = build_device_identifier(new_homey_id, legacy_device_id, True)
        target_device = device_registry.async_get_device(
            identifiers={target_identifier}, connections=set()
        )
        if not target_device:
            target_device = device_registry.async_get_or_create(
                config_entry_id=entry.entry_id,
                identifiers={target_identifier},
                manufacturer=device_entry.manufacturer,
                model=device_entry.model,
                name=device_entry.name,
                suggested_area=device_entry.suggested_area,
            )

        for entity_entry in entity_registry.entities.values():
            if entity_entry.device_id == device_entry.id:
                entity_registry.async_update_entity(
                    entity_entry.entity_id, device_id=target_device.id
                )

    _LOGGER.info("Rescoping Homey devices complete")


async def _async_enable_multi_homey(hass: HomeAssistant) -> None:
    """Enable multi-homey mode and rescope devices."""
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN]["multi_homey_enabled"] = True

    persistent_notification.async_create(
        hass,
        "Multiple Homey hubs detected. Migrating device registry identifiers "
        "to prevent collisions. This may create new devices once.",
        title="Homey: Multi-hub migration",
        notification_id=f"{DOMAIN}_multi_homey_migration",
    )

    for entry in hass.config_entries.async_entries(DOMAIN):
        if entry.domain != DOMAIN:
            continue
        homey_id = entry.data.get("homey_id") or entry.data.get(CONF_HOST)
        hass.config_entries.async_update_entry(
            entry,
            data={**entry.data, "homey_id": homey_id, "multi_homey_enabled": True},
        )
        await _async_rescope_devices(hass, entry, homey_id)

    # Remove legacy unscoped devices only if no entities remain
    device_registry = dr.async_get(hass)
    entity_registry = er.async_get(hass)
    for device_entry in list(device_registry.devices.values()):
        for identifier in device_entry.identifiers:
            if identifier[0] != DOMAIN:
                continue
            if ":" in identifier[1]:
                continue
            has_entities = any(
                ent.device_id == device_entry.id
                for ent in entity_registry.entities.values()
            )
            if not has_entities:
                device_registry.async_remove_device(device_entry.id)
            break

    persistent_notification.async_create(
        hass,
        "Multi-hub migration completed. If you see duplicate devices, remove the old ones.",
        title="Homey: Multi-hub migration complete",
        notification_id=f"{DOMAIN}_multi_homey_migration_done",
    )


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    if unload_ok:
        data = hass.data[DOMAIN].pop(entry.entry_id)
        if data and "api" in data:
            await data["api"].disconnect()

    return unload_ok

