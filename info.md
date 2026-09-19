# Homey Integration for Home Assistant

---

## Version 2.1.3

**Current stable release** for the `homey_hass` integration (folder `custom_components/homey_hass/`, services `homey_hass.*`).

**Available in the official HACS default catalog** — search for **Homey** in HACS → Integrations (listed as **Homey 2.x** while legacy 1.x may still be installed on some systems).

---

## What's New in 2.1.3

### Fixed
- **Integration failed to load after updating to 2.1.2 (all entities unavailable)**: On newer Home Assistant, config entry migration cannot set `entry.version` directly. 2.1.2 crashed during migration with `AttributeError: version cannot be changed directly`, so Homey never finished setup and entities showed *"This entity is no longer being provided by the homey_hass integration"*. Migration now uses `async_update_entry(..., version=3)`.

### Thanks

Thanks to everyone who reported issues around 2.1.2 — especially for the migration traceback that pinned this down quickly.

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

**Quick summary:** backup → install **2.1.3** alongside 1.x → **Add integration → Homey 2.x** → **Migrate from Homey 1.x** → delete `custom_components/homey/` when done.

---

## Staying on 1.x?

Use HACS repository **[`ifMike/homeyHASS-legacy`](https://github.com/ifMike/homeyHASS-legacy)** — **only 1.2.x updates**. Do not install 2.x until you are ready to migrate.

---

## Upgrading from 2.1.2 / 2.1.x / 2.0.x

1. Update via HACS or download **v2.1.3** from [Releases](https://github.com/ifMike/homeyHASS/releases)
2. Restart Home Assistant

If you updated to **2.1.2** and all Homey entities became unavailable: install **2.1.3** and restart — entities should come back without deleting anything.

For the full changelog, see [CHANGELOG](https://github.com/ifMike/homeyHASS/blob/main/CHANGELOG.md).
