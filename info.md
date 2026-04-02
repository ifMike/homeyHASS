# Homey Integration for Home Assistant

## What's New in 1.2.3

### Added
- **Light scenes/effects**: Added support for `lightScenes.light` (and `lightScenes`) on light devices. These scenes are now exposed through Home Assistant light `effect` / `effect_list`.
- **Capability mapping**: Added explicit light mapping for `lightScenes` and `lightScenes.light` to improve device classification.

### Fixed
- **Light classification**: Devices with `onoff` + `lightScenes.*` are now treated as lights (not switches).
- **Numeric capability parsing**: Fixed a crash when Homey returns `"auto"` for numeric capability values.
- **Moisture capabilities**: Improved moisture capability handling so moisture-related sensors use the moisture device class.

For the full list of changes, see the [CHANGELOG](https://github.com/ifMike/homeyHASS/blob/main/CHANGELOG.md).

---

## Installation

After installing via HACS:

1. Go to **Settings** → **Devices & Services** → **Add Integration**
2. Search for **"Homey"**
3. Enter your Homey IP address and API key
4. Select devices to import

For detailed setup instructions, see the [README](README.md).
