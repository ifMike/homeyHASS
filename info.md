# Homey Integration for Home Assistant

## What's New in 1.2.2

### Added
- **Model filtering**: Homey 2019 and older no longer appear in discovery. Zeroconf now filters by mDNS `model` property—unsupported models (homey3d, homey4d, etc.) are suppressed. Pro 2023, Pro mini, Pro 2026, and SHS are supported.
- **Discovery logging**: Search logs for `[discovery]` to see full discovery info (hostname, MAC, model, API reachability) for troubleshooting.

### Fixed
- **Discovery suppression**: Improved matching so the "new" Homey card no longer appears when your hub is already configured. Compares by host+port, MAC, and resolved IP.
- **Multi-hub migration**: Migration notifications only appear once, not on every restart.
- **HACS**: Removed deprecated `beta` key (fixes validation).

For the full list of changes, see the [CHANGELOG](https://github.com/ifMike/homeyHASS/blob/main/CHANGELOG.md).

---

## Installation

After installing via HACS:

1. Go to **Settings** → **Devices & Services** → **Add Integration**
2. Search for **"Homey"**
3. Enter your Homey IP address and API key
4. Select devices to import

For detailed setup instructions, see the [README](README.md).
