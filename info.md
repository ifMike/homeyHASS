# Homey Integration for Home Assistant

---

## Version 2.1.2

**Current stable release** for the `homey_hass` integration (folder `custom_components/homey_hass/`, services `homey_hass.*`).

**Available in the official HACS default catalog** — search for **Homey** in HACS → Integrations (listed as **Homey 2.x** while legacy 1.x may still be installed on some systems).

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

## What's New in 2.1.2

### Fixed
- **Long string / SVG states (#34)**: Values longer than Home Assistant's 255-character state limit are truncated for the entity state (SVG markup becomes `svg`). The full value is available as the `full_value` attribute. This stops multi-GB `homeassistant.core` log growth from rejected states.
- **Multi-hub unique_id orphans (#35)**: When a second Homey hub is added, existing entity unique IDs are migrated to the hub-prefixed form so entities are not recreated as duplicates. Single-hub installs are unchanged. If both old and new IDs already exist from an earlier upgrade, remove the **unavailable** orphans in Settings → Devices & Services → Entities.
- **Nest thermostat capabilities (#36)**: `nest_thermostat_mode`, `nest_thermostat_hvac`, and `nest_thermostat_eco` are recognized (stops “new capability” notifications). Climate correctly maps Nest `heatcool` and HVAC action.

### Permissions

Unchanged. Homey API key with **Local API** access — typically:

- `homey.device.readonly` — discover and read device states
- `homey.device.control` — control devices
- `homey.system.readonly` — Socket.IO real-time updates (recommended)
- Optional: flows, moods, logic variables (see [README](https://github.com/ifMike/homeyHASS/blob/main/README.md))

---

## Upgrading from 2.1.x / 2.0.x

1. Update via HACS or download **v2.1.2** from [Releases](https://github.com/ifMike/homeyHASS/releases)
2. Restart Home Assistant

No migration steps required unless you are still on 1.x.

**Multi-hub users who already see duplicate/unavailable entities:** after updating, restart once. Prefer keeping the **live** entities; delete **unavailable** orphans only. Do not delete live entities.

For the full changelog, see [CHANGELOG](https://github.com/ifMike/homeyHASS/blob/main/CHANGELOG.md).
