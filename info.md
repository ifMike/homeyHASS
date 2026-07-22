# Homey Integration for Home Assistant

---

## Version 2.0.1

**Current stable release** for the `homey_hass` integration (folder `custom_components/homey_hass/`, services `homey_hass.*`).

**Available in the official HACS default catalog** — search for **Homey** in HACS → Integrations. No custom repository required.

### Legacy 1.x users — read this first

If you have a **working 1.x installation** (domain `homey`, folder `custom_components/homey/`) and do **not** want to migrate yet:

- Use HACS repository **[`ifMike/homeyHASS-legacy`](https://github.com/ifMike/homeyHASS-legacy)** — it publishes **only 1.2.x updates**.
- Do **not** install 2.x from this repository until you follow the [migration guide](https://github.com/ifMike/homeyHASS#migrating-from-1x-to-200).

---

## What's New in 2.0.1

### Fixed
- **Legacy Fibaro roller shutters**: Older Fibaro Z-Wave shutters that expose position via `dim` instead of `windowcoverings_*` now create `cover.*` entities with open, close, stop, and set position.
- **Discovery hostname resolution**: Improved handling when resolving `.local` hostnames to IP addresses during setup.

### Documentation
- **HACS default catalog**: Search **Homey** in HACS → Integrations — no custom repository required ([PR #6696](https://github.com/hacs/default/pull/6696)).
- **Legacy 1.x HACS repository** documented in README for users who want bug fixes without the 2.0 domain migration.

### Permissions

Unchanged from 2.0.0. Homey API key with **Local API** access — typically:

- `homey.device.readonly` — discover and read device states
- `homey.device.control` — control devices
- `homey.system.readonly` — Socket.IO real-time updates (recommended)
- Optional: flows, moods, logic variables (see [README](https://github.com/ifMike/homeyHASS/blob/main/README.md))

---

## Upgrading from 2.0.0

1. Update via HACS or download **v2.0.1** from [Releases](https://github.com/ifMike/homeyHASS/releases).
2. Restart Home Assistant.

No migration steps required between 2.0.0 and 2.0.1.

---

## Upgrading from 1.x

**This is a breaking change.** Version 2.0.0+ renames the domain from `homey` to `homey_hass`. You must migrate manually — there is no in-place upgrade.

See the full [Migrating from 1.x to 2.0.0](https://github.com/ifMike/homeyHASS#migrating-from-1x-to-200) guide in the README, or stay on **[`ifMike/homeyHASS-legacy`](https://github.com/ifMike/homeyHASS-legacy)** for 1.2.x updates.

For the full changelog, see [CHANGELOG](https://github.com/ifMike/homeyHASS/blob/main/CHANGELOG.md).
