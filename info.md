# Homey Integration for Home Assistant

---

## Version 2.1.2

**Current stable release** for the `homey_hass` integration (folder `custom_components/homey_hass/`, services `homey_hass.*`).

**Available in the official HACS default catalog** — search for **Homey** in HACS → Integrations (listed as **Homey 2.x** while legacy 1.x may still be installed on some systems).

---

## What's New in 2.1.2

### Fixed
- **Huge Home Assistant logs from long Homey values (#34)**: Some Homey capabilities (for example weather SVG icons and long Logic text) are longer than Home Assistant's 255-character state limit. The integration used to pass those values straight into the entity state, so every update logged a long error and could grow logs by many gigabytes. States are now truncated for display (SVG becomes `svg`), and the full value is kept in the `full_value` attribute.
- **Duplicate / orphaned entities after adding a second Homey hub (#35)**: Turning on multi-hub mode changed entity unique IDs (hub prefix) without migrating the entity registry, so Home Assistant created a second live entity next to an unavailable orphan. Unique IDs are now migrated when multi-hub is enabled. Single-hub installs are unchanged. If both old and new IDs already exist, remove only the **unavailable** orphans in Settings → Devices & Services → Entities.
- **Google Nest thermostat capabilities reported as unknown (#36)**: Nest's `nest_thermostat_mode`, `nest_thermostat_hvac`, and `nest_thermostat_eco` triggered "new capability" notifications and were not mapped cleanly. They are now recognized; climate handles Nest mode (including `heatcool`) and HVAC action; eco stays a switch.
- **Config entry migration crash on newer Home Assistant**: An early 2.1.2 build set `entry.version` directly, which newer HA rejects (`AttributeError: version cannot be changed directly`). Migration failed, Homey never loaded, and entities showed *"This entity is no longer being provided by the homey_hass integration"*. Version is now updated via `async_update_entry`. If you hit this, redownload **2.1.2** / restart — entities should come back without deleting them.

### Thanks

Thanks to [@Bigkun-HU](https://github.com/Bigkun-HU) for reporting the long-state log flood and multi-hub unique ID orphans ([#34](https://github.com/ifMike/homeyHASS/issues/34), [#35](https://github.com/ifMike/homeyHASS/issues/35)), and to [@mca-rolando](https://github.com/mca-rolando) for reporting the Nest thermostat capabilities ([#36](https://github.com/ifMike/homeyHASS/issues/36)).

### Permissions

Unchanged. Homey API key with **Local API** access — typically:

- `homey.device.readonly` — discover and read device states
- `homey.device.control` — control devices
- `homey.system.readonly` — Socket.IO real-time updates (recommended)
- Optional: flows, moods, logic variables (see [README](https://github.com/ifMike/homeyHASS/blob/main/README.md))

---

## New installation?

Install normally: **Add integration → Homey 2.x** and enter your Homey host and API key. **No migration steps apply.**

---

## Upgrading from 1.x?

Use the **guided migration assistant** (added in 2.1.0). Full guide: [Migrating from 1.x to 2.x](https://github.com/ifMike/homeyHASS#migrating-from-1x-to-2x).

**Quick summary:** backup → install **2.1.2** alongside 1.x → **Add integration → Homey 2.x** → **Migrate from Homey 1.x** → delete `custom_components/homey/` when done.

---

## Staying on 1.x?

Use HACS repository **[`ifMike/homeyHASS-legacy`](https://github.com/ifMike/homeyHASS-legacy)** — **only 1.2.x updates**. Do not install 2.x until you are ready to migrate.

---

## Upgrading from 2.1.x / 2.0.x

1. Update via HACS or download **v2.1.2** from [Releases](https://github.com/ifMike/homeyHASS/releases)
2. Restart Home Assistant

No migration steps required unless you are still on 1.x.

**Multi-hub users who already see duplicate/unavailable entities:** after updating, restart once. Prefer keeping the **live** entities; delete **unavailable** orphans only. Do not delete live entities.

**If Homey entities all became unavailable after an early 2.1.2 install:** redownload **2.1.2** (or pull latest from this tag) and restart — do not delete entities.

For the full changelog, see [CHANGELOG](https://github.com/ifMike/homeyHASS/blob/main/CHANGELOG.md).
