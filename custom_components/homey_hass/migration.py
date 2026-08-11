"""Migration helpers for upgrading from Homey integration 1.x to 2.x."""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er

from .const import (
    CONF_DEVICE_FILTER,
    CONF_HOST,
    CONF_MIGRATE_FROM_LEGACY_ENTRY_ID,
    CONF_PRESERVE_ENTITY_IDS,
    CONF_REMOVE_LEGACY_ENTRY,
    CONF_TOKEN,
    CONF_USE_CAPABILITY_TITLES,
    CONF_WORKING_ENDPOINT,
    DEFAULT_USE_CAPABILITY_TITLES,
    DOMAIN,
    LEGACY_DOMAIN,
    LEGACY_UNIQUE_ID_PREFIX,
    UNIQUE_ID_PREFIX,
)

_LOGGER = logging.getLogger(__name__)

AUTOMATION_SERVICE_HINTS = (
    ("homey.trigger_flow", "homey_hass.trigger_flow"),
    ("homey.enable_flow", "homey_hass.enable_flow"),
    ("homey.disable_flow", "homey_hass.disable_flow"),
    ("homey.set_device_temperature_unit", "homey_hass.set_device_temperature_unit"),
    ("homey.rename_entities_to_titles", "homey_hass.rename_entities_to_titles"),
    ("homey.test_capability_report", "homey_hass.test_capability_report"),
)


@dataclass(slots=True)
class LegacyMigrationResult:
    """Summary of a 1.x → 2.x migration run."""

    entities_preserved: int = 0
    entities_skipped: int = 0
    device_areas_restored: int = 0
    legacy_entry_removed: bool = False
    legacy_entry_id: str | None = None


def legacy_integration_available(hass: HomeAssistant) -> bool:
    """Return True when the Homey 1.x integration is installed and loaded."""
    return LEGACY_DOMAIN in hass.config.components


def get_legacy_config_entries(hass: HomeAssistant) -> list[ConfigEntry]:
    """Return Homey 1.x config entries when a guided migration is possible.

    Migration UI is shown only when the legacy integration (domain ``homey``,
    folder ``custom_components/homey/``) is loaded **and** at least one 1.x
    config entry exists. New 2.x installations without 1.x never see migration steps.
    """
    if not legacy_integration_available(hass):
        return []
    return list(hass.config_entries.async_entries(LEGACY_DOMAIN))


def legacy_unique_id_body(unique_id: str | None) -> str | None:
    """Return the match key for a legacy or current unique ID (prefix stripped)."""
    if not unique_id:
        return None
    if unique_id.startswith(UNIQUE_ID_PREFIX):
        return unique_id[len(UNIQUE_ID_PREFIX) :]
    if unique_id.startswith(LEGACY_UNIQUE_ID_PREFIX):
        return unique_id[len(LEGACY_UNIQUE_ID_PREFIX) :]
    return None


def build_entry_data_from_legacy(legacy_entry: ConfigEntry) -> dict[str, Any]:
    """Build a 2.x config entry data dict from a 1.x entry."""
    data: dict[str, Any] = {
        CONF_HOST: legacy_entry.data[CONF_HOST],
        CONF_TOKEN: legacy_entry.data[CONF_TOKEN],
        CONF_WORKING_ENDPOINT: legacy_entry.data.get(CONF_WORKING_ENDPOINT),
        CONF_DEVICE_FILTER: legacy_entry.data.get(CONF_DEVICE_FILTER),
        CONF_USE_CAPABILITY_TITLES: legacy_entry.data.get(
            CONF_USE_CAPABILITY_TITLES, DEFAULT_USE_CAPABILITY_TITLES
        ),
    }
    if legacy_entry.data.get("homey_id"):
        data["homey_id"] = legacy_entry.data["homey_id"]
    return data


def snapshot_legacy_entity_map(
    entity_registry: er.EntityRegistry,
    legacy_entry_id: str | None = None,
) -> dict[str, str]:
    """Map legacy unique_id body → entity_id for entity ID preservation."""
    mapping: dict[str, str] = {}
    for entity_entry in entity_registry.entities.values():
        if entity_entry.platform != LEGACY_DOMAIN:
            continue
        if (
            legacy_entry_id
            and _entity_config_entry_id(entity_entry)
            and _entity_config_entry_id(entity_entry) != legacy_entry_id
        ):
            continue
        body = legacy_unique_id_body(entity_entry.unique_id)
        if not body:
            continue
        if body in mapping and mapping[body] != entity_entry.entity_id:
            _LOGGER.debug(
                "Legacy entity map: duplicate body %s (%s vs %s)",
                body,
                mapping[body],
                entity_entry.entity_id,
            )
            continue
        mapping[body] = entity_entry.entity_id
    return mapping


def _legacy_device_id(identifier: tuple[str, str]) -> str | None:
    if identifier[0] != LEGACY_DOMAIN:
        return None
    value = identifier[1]
    if ":" in value:
        return value.split(":", 1)[1]
    return value


def _current_device_id(identifier: tuple[str, str]) -> str | None:
    if identifier[0] != DOMAIN:
        return None
    value = identifier[1]
    if ":" in value:
        return value.split(":", 1)[1]
    return value


def _device_config_entry_ids(device_entry: dr.DeviceEntry) -> set[str]:
    """Return config entry IDs linked to a device (HA 2024+ uses config_entries)."""
    entry_ids = getattr(device_entry, "config_entries", None)
    if entry_ids is not None:
        return set(entry_ids)
    entry_id = getattr(device_entry, "config_entry_id", None)
    return {entry_id} if entry_id else set()


def _device_belongs_to_entry(device_entry: dr.DeviceEntry, entry_id: str) -> bool:
    """Return True when a device is linked to the given config entry."""
    return entry_id in _device_config_entry_ids(device_entry)


def _entity_config_entry_id(entity_entry: er.RegistryEntry) -> str | None:
    """Return the config entry ID for an entity registry entry."""
    return getattr(entity_entry, "config_entry_id", None)


async def async_preserve_entity_ids(
    hass: HomeAssistant,
    new_entry_id: str,
    legacy_entry_id: str | None,
) -> tuple[int, int]:
    """Transfer legacy entity IDs to matching 2.x entities."""
    entity_registry = er.async_get(hass)
    legacy_map = snapshot_legacy_entity_map(entity_registry, legacy_entry_id)
    if not legacy_map:
        _LOGGER.info("No legacy Homey entities found to preserve")
        return 0, 0

    preserved = 0
    skipped = 0
    claimed_entity_ids: set[str] = set()

    for entity_entry in list(entity_registry.entities.values()):
        if entity_entry.platform != DOMAIN:
            continue
        if _entity_config_entry_id(entity_entry) != new_entry_id:
            continue

        body = legacy_unique_id_body(entity_entry.unique_id)
        if not body:
            skipped += 1
            continue

        target_entity_id = legacy_map.get(body)
        if not target_entity_id:
            continue
        if target_entity_id == entity_entry.entity_id:
            claimed_entity_ids.add(target_entity_id)
            continue

        if target_entity_id in claimed_entity_ids:
            skipped += 1
            continue

        existing = entity_registry.async_get(target_entity_id)
        if existing and existing.entity_id != entity_entry.entity_id:
            if existing.platform == LEGACY_DOMAIN:
                entity_registry.async_remove(target_entity_id)
            else:
                _LOGGER.warning(
                    "Cannot preserve entity ID %s — already used by %s",
                    target_entity_id,
                    existing.platform,
                )
                skipped += 1
                continue

        try:
            entity_registry.async_update_entity(
                entity_entry.entity_id,
                new_entity_id=target_entity_id,
            )
            claimed_entity_ids.add(target_entity_id)
            preserved += 1
            _LOGGER.debug(
                "Preserved entity ID %s for %s",
                target_entity_id,
                entity_entry.unique_id,
            )
        except Exception as err:
            _LOGGER.warning(
                "Failed to preserve entity ID %s for %s: %s",
                target_entity_id,
                entity_entry.unique_id,
                err,
            )
            skipped += 1

    return preserved, skipped


async def async_migrate_device_areas(
    hass: HomeAssistant,
    new_entry_id: str,
    legacy_entry_id: str | None,
) -> int:
    """Copy area assignments from legacy devices to matching 2.x devices."""
    device_registry = dr.async_get(hass)
    legacy_areas: dict[str, str] = {}

    for device_entry in device_registry.devices.values():
        if legacy_entry_id and not _device_belongs_to_entry(device_entry, legacy_entry_id):
            continue
        device_id = None
        for identifier in device_entry.identifiers:
            device_id = _legacy_device_id(identifier)
            if device_id:
                break
        if not device_id or not device_entry.area_id:
            continue
        legacy_areas[device_id] = device_entry.area_id

    if not legacy_areas:
        return 0

    restored = 0
    for device_entry in device_registry.devices.values():
        if not _device_belongs_to_entry(device_entry, new_entry_id):
            continue
        device_id = None
        for identifier in device_entry.identifiers:
            device_id = _current_device_id(identifier)
            if device_id:
                break
        if not device_id:
            continue
        area_id = legacy_areas.get(device_id)
        if not area_id or device_entry.area_id == area_id:
            continue
        device_registry.async_update_device(device_entry.id, area_id=area_id)
        restored += 1

    return restored


async def async_remove_legacy_entry(hass: HomeAssistant, legacy_entry_id: str) -> bool:
    """Remove the Homey 1.x config entry."""
    legacy_entry = hass.config_entries.async_get_entry(legacy_entry_id)
    if not legacy_entry or legacy_entry.domain != LEGACY_DOMAIN:
        return False
    await hass.config_entries.async_remove(legacy_entry_id)
    return True


def build_migration_success_message(result: LegacyMigrationResult) -> str:
    """Build a user-facing migration summary notification."""
    lines = [
        "**Migration from Homey 1.x complete.**",
        "",
        f"- Entity IDs preserved: **{result.entities_preserved}**",
    ]
    if result.entities_skipped:
        lines.append(f"- Entity IDs skipped (conflicts): **{result.entities_skipped}**")
    if result.device_areas_restored:
        lines.append(f"- Device areas restored: **{result.device_areas_restored}**")
    if result.legacy_entry_removed:
        lines.append("- Old Homey 1.x integration: **removed**")
    else:
        lines.append(
            "- Old Homey 1.x integration: **still present** — remove it manually when ready"
        )

    lines.extend(
        [
            "",
            "**Next steps:**",
            "1. Confirm devices and entities work under **Settings → Devices & services → Homey**",
            "2. Update automations/scripts — replace `homey.` services with `homey_hass.`:",
        ]
    )
    for old, new in AUTOMATION_SERVICE_HINTS:
        lines.append(f"   - `{old}` → `{new}`")
    lines.extend(
        [
            "3. Delete the old folder `custom_components/homey/` on your config directory",
            "4. Restart Home Assistant",
            "5. Click **Ignore** on any leftover **Homey (IP unknown)** discovery card",
            "",
            "Full guide: [Migrating from 1.x](https://github.com/ifMike/homeyHASS#migrating-from-1x-to-2x)",
        ]
    )
    return "\n".join(lines)


async def async_run_legacy_migration(hass: HomeAssistant, entry: ConfigEntry) -> LegacyMigrationResult:
    """Run post-setup migration when requested by config flow."""
    legacy_entry_id = entry.data.get(CONF_MIGRATE_FROM_LEGACY_ENTRY_ID)
    if not legacy_entry_id:
        return LegacyMigrationResult()

    preserve = entry.data.get(CONF_PRESERVE_ENTITY_IDS, True)
    remove_legacy = entry.data.get(CONF_REMOVE_LEGACY_ENTRY, True)

    result = LegacyMigrationResult(legacy_entry_id=legacy_entry_id)

    if preserve:
        try:
            preserved, skipped = await async_preserve_entity_ids(
                hass, entry.entry_id, legacy_entry_id
            )
            result.entities_preserved = preserved
            result.entities_skipped = skipped
            result.device_areas_restored = await async_migrate_device_areas(
                hass, entry.entry_id, legacy_entry_id
            )
        except Exception as err:
            _LOGGER.exception("Legacy migration failed (integration will still load): %s", err)

    if remove_legacy:
        try:
            result.legacy_entry_removed = await async_remove_legacy_entry(
                hass, legacy_entry_id
            )
        except Exception as err:
            _LOGGER.exception("Failed to remove legacy Homey 1.x entry: %s", err)

    cleaned_data = {
        key: value
        for key, value in entry.data.items()
        if key
        not in (
            CONF_MIGRATE_FROM_LEGACY_ENTRY_ID,
            CONF_REMOVE_LEGACY_ENTRY,
            CONF_PRESERVE_ENTITY_IDS,
        )
    }
    hass.config_entries.async_update_entry(entry, data=cleaned_data)

    _LOGGER.info(
        "Legacy migration complete: preserved=%d skipped=%d areas=%d legacy_removed=%s",
        result.entities_preserved,
        result.entities_skipped,
        result.device_areas_restored,
        result.legacy_entry_removed,
    )
    return result
