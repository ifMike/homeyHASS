# Homey Integration for Home Assistant

## Legacy 1.x release — v1.2.7

This release is for **existing users on the 1.x line** (domain `homey`, folder `custom_components/homey/`) who want bug fixes without migrating to **2.0.0** (`homey_hass`).

**Do not install this if you are already on 2.0.0.** New installations should use **2.0.0** on the `main` branch.

### Who should use v1.2.7

- You have a **working 1.x setup** today (domain `homey`) and want fixes only.
- You are **not ready** to delete your config entry and re-setup under `homey_hass`.

### Who should not use v1.2.7

- **New users** — install **2.0.0** instead.
- Users who want the official HACS default listing path — that requires **2.0.0** on `main`.

---

## What's New in 1.2.7

### Fixed
- **Legacy Fibaro roller shutters**: Older Fibaro Z-Wave shutters that expose position via `dim` instead of `windowcoverings_*` now create `cover.*` entities with open, close, stop, and set position.
- **Dyson fan capabilities**: `oscillate` on the fan entity; `less_air` and `more_air` as buttons. Stops false capability alerts on Dyson Air Multiplier devices.
- **Discovery hostname resolution**: Improved handling when resolving `.local` hostnames to IP addresses.

### Added
- Integration brand icon for HACS validation.

### Included from 1.2.6
- Device temperature unit override (`homey.set_device_temperature_unit` service).
- Temperature unit handling from Homey metadata.
- Capability alert and thermostat temperature display fixes.

For the full list of changes, see the [CHANGELOG](https://github.com/ifMike/homeyHASS/blob/release/1.x/CHANGELOG.md).

---

## Installation (1.x / v1.2.7)

1. Install **v1.2.7** from [GitHub Releases](https://github.com/ifMike/homeyHASS/releases/tag/v1.2.7), or track the [`release/1.x`](https://github.com/ifMike/homeyHASS/tree/release/1.x) branch in HACS.
2. Ensure the folder is `custom_components/homey/` (not `homey_hass`).
3. Restart Home Assistant.
4. Add or reload the **Homey** integration (domain `homey`).

**Permissions** (unchanged from 1.2.6): Homey API key with **Local API** access — typically `homey.device.readonly` and `homey.device.control` (plus flow permissions if you use flows).
