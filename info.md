# Homey Integration for Home Assistant (Legacy 1.x)

## Dedicated legacy repository — v1.2.7

This is the **HACS repository for the 1.x line** (domain `homey`, folder `custom_components/homey/`). It publishes **only 1.2.x releases**, so you do not receive update notifications for 2.x from the main [`ifMike/homeyHASS`](https://github.com/ifMike/homeyHASS) repository.

### Who should use this repository

- You have a **working 1.x setup** (domain `homey`) and want bug fixes without migrating to 2.0.0.
- You previously used `ifMike/homeyHASS` in HACS and want to **stop 2.x update notifications**.

### Who should not use this repository

- **New users** — install from [`ifMike/homeyHASS`](https://github.com/ifMike/homeyHASS) (**2.0.0**, domain `homey_hass`) instead.
- Users already on **2.0.0** — stay on the main repository.

---

## What's New in 1.2.7

### Fixed
- **Legacy Fibaro roller shutters**: Older Fibaro Z-Wave shutters that expose position via `dim` instead of `windowcoverings_*` now create `cover.*` entities with open, close, stop, and set position.
- **Dyson fan capabilities**: `oscillate` on the fan entity; `less_air` and `more_air` as buttons. Stops false capability alerts on Dyson Air Multiplier devices.
- **Discovery hostname resolution**: Improved handling when resolving `.local` hostnames to IP addresses.

### Added
- Integration brand icon for HACS validation.

For the full list of changes, see the [CHANGELOG](https://github.com/ifMike/homeyHASS-legacy/blob/main/CHANGELOG.md).

---

## HACS installation

1. **HACS** → **Integrations** → three dots → **Custom repositories**
2. Remove `https://github.com/ifMike/homeyHASS` if present (optional but recommended)
3. Add `https://github.com/ifMike/homeyHASS-legacy` (Category: Integration)
4. Search **Homey** → **Download** → restart Home Assistant

If switching from the main repository, **Redownload** once from this repo (select **v1.2.7** or latest 1.2.x).

**Permissions** (unchanged from 1.2.6): Homey API key with Local API access — typically `homey.device.readonly` and `homey.device.control` (plus flow permissions if you use flows).

Issues: [ifMike/homeyHASS/issues](https://github.com/ifMike/homeyHASS/issues) (shared with the main project).
