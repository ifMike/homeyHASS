# Homey Integration for Home Assistant

---

## Version 2.1.1

**Current stable release** for the `homey_hass` integration (folder `custom_components/homey_hass/`, services `homey_hass.*`).

**Available in the official HACS default catalog** — search for **Homey** in HACS → Integrations (listed as **Homey 2.x** while legacy 1.x may still be installed on some systems).

---

## New installation?

Install normally: **Add integration → Homey 2.x** and enter your Homey host and API key. **No migration steps apply.**

---

## Upgrading from 1.x?

Use the **guided migration assistant** (added in 2.1.0). Full guide: [Migrating from 1.x to 2.x](https://github.com/ifMike/homeyHASS#migrating-from-1x-to-2x).

**Quick summary:** backup → install **2.1.1** alongside 1.x → **Add integration → Homey 2.x** → **Migrate from Homey 1.x** → delete `custom_components/homey/` when done.

---

## Staying on 1.x?

Use HACS repository **[`ifMike/homeyHASS-legacy`](https://github.com/ifMike/homeyHASS-legacy)** — **only 1.2.x updates**. Do not install 2.x until you are ready to migrate.

---

## What's New in 2.1.1

### Fixed
- **Vacuum platform on Home Assistant 2026.9**: `VacuumEntityFeature.BATTERY` was removed in Core 2026.9 and caused the entire vacuum platform to fail setup (all vacuum entities disappeared). Battery remains available via the existing `measure_battery` sensor. ([#33](https://github.com/ifMike/homeyHASS/issues/33))

### Changed
- **CI**: GitHub Actions updated to Node 24–compatible versions (`checkout@v5`, `setup-python@v6`, `cache@v6`).
- **Hassfest**: Added `CONFIG_SCHEMA` for config-entry-only setup.

### Permissions

Unchanged. Homey API key with **Local API** access — typically:

- `homey.device.readonly` — discover and read device states
- `homey.device.control` — control devices
- `homey.system.readonly` — Socket.IO real-time updates (recommended)
- Optional: flows, moods, logic variables (see [README](https://github.com/ifMike/homeyHASS/blob/main/README.md))

---

## Upgrading from 2.1.0 / 2.0.x

1. Update via HACS or download **v2.1.1** from [Releases](https://github.com/ifMike/homeyHASS/releases)
2. Restart Home Assistant

No migration steps required unless you are still on 1.x.

For the full changelog, see [CHANGELOG](https://github.com/ifMike/homeyHASS/blob/main/CHANGELOG.md).
