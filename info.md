# Homey Integration for Home Assistant

## What's New in 1.2.4

### Fixed
- **Homey Energy Dongle legacy gas/water compatibility**: Added backward compatibility for legacy `sgas*` / `swater*` capability names by treating them as cumulative gas/water meters.
- **Energy metadata for legacy entities**: Legacy gas/water entities now use `total_increasing` with `m³` units for correct utility tracking behavior.
- **Legacy label clarity**: Improved naming for legacy gas/water entities to make them easier to identify in Home Assistant.

For the full list of changes, see the [CHANGELOG](https://github.com/ifMike/homeyHASS/blob/main/CHANGELOG.md).

---

## Installation

After installing via HACS:

1. Go to **Settings** → **Devices & Services** → **Add Integration**
2. Search for **"Homey"**
3. Enter your Homey IP address and API key
4. Select devices to import

For detailed setup instructions, see the [README](README.md).
