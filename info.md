# Homey Integration for Home Assistant

## What's New in 1.6.0-dev.1

### Added
- **Device temperature unit override**: Configure per-device Celsius/Fahrenheit when Homey capability metadata is wrong or missing (**Settings → Homey → Configure → Device temperature units**), or use the `homey.set_device_temperature_unit` service.
- **Temperature unit handling**: Climate and temperature sensors use Homey `units` metadata so Home Assistant can display values in your system unit.

### Fixed
- **Capability alerts**: New-capability notifications only fire for capabilities the integration does not already support (no more alerts for known `measure_*` capabilities such as `measure_current`).
- **Thermostat temperature display**: Fixes wrong temperatures (e.g. 69°F shown as 156°F) when drivers report Fahrenheit values but label them as Celsius.

For the full list of changes, see the [CHANGELOG](https://github.com/ifMike/homeyHASS/blob/dev/CHANGELOG.md).

---

## Installation

After installing via HACS:

1. Go to **Settings** → **Devices & Services** → **Add Integration**
2. Search for **"Homey"**
3. Enter your Homey IP address and API key
4. Select devices to import

For detailed setup instructions, see the [README](https://github.com/ifMike/homeyHASS/blob/dev/README.md).
