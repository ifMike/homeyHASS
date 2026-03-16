# Homey Integration for Home Assistant

## What's New in 1.2.1

### Critical

- **Sensor unavailability fix**: A registry filter was incorrectly skipping existing sensors, causing them to become orphaned and show Unavailable. Controls (lights, switches, etc.) worked, but sensors did not. This is a critical fix for all users who rely on sensor data—temperature, humidity, presence, distance, and similar capabilities.

### ✨ Added
- **Discovery card identification**: Shows IPv4 on discovered cards (e.g. "Homey (192.168.1.32)") so multiple Homeys can be distinguished
- **Setup step descriptions**: Step descriptions explain what to do, required permissions, and Pro 2023+ limitation
- **Translations**: Added translations for config flow step descriptions

### 🔧 Changed
- **Discovery host field**: Never show .local hostname or IPv6; resolve to IPv4 when possible. Default manual host changed from homey.local to empty
- **Error messages**: Full error messages for invalid_auth and cannot_connect with causes and solutions, including Pro 2019 not supported

### 🐛 Fixed
- **Discovery suppression**: Suppress discovery when an existing config entry points to the same host (fixes "Discovered" Homey showing when manually configured)
- **IPv6 discovery suppression**: Correctly suppress discovery for already-configured hosts when discovered host is IPv6
- **Discovery card fallback**: Card now always shows "Homey (IP)" or "Homey (IP unknown)" instead of domain name

For the full list of changes, see the [CHANGELOG](https://github.com/ifMike/homeyHASS/blob/v1.2.1/CHANGELOG.md).

---

## What's New in 1.2.0

### ✨ New Features
- **Virtual button support**: Homey Virtual Button devices now create button entities
- **Zeroconf (mDNS) discovery**: Automatic discovery via `_homey._tcp` mDNS regardless of MAC or router DHCP
- **DHCP discovery**: Automatic discovery via MAC prefix (9013DA); updates host when router reassigns IP
- **measure_distance**: Ultrasonic/ToF presence sensors now get proper distance sensors with cm unit

### 🔧 Improvements
- **Discovery form**: Editable host in confirmation step; default manual host is `homey.local`
- **Better diagnostics**: Connection failures now include host and exception; warns when using `.local` hostname
- **Logging**: Rate-limited error logs when Homey is unreachable; reduced log noise across discovery, lights, logic variables, and Socket.IO

### 🐛 Fixes
- **Discovery host overwrite**: Zeroconf no longer overwrites your configured host; DHCP still updates for IP reassignment
- **Duplicate hub detection**: Setup aborts with clear message instead of warning
- **Sensor duplicates**: Fixed duplicate sensors for `measure_*` and `meter_*` capabilities
- **Logic variables**: Handle nested API responses and try both payload formats so toggles/edits work regardless of Homey API structure
- **Zeroconf discovery**: Resolve hostname to IP when mDNS has no addresses, so the form shows a connectable IP instead of hostname/MAC

For the full list of changes, see the [CHANGELOG](https://github.com/ifMike/homeyHASS/blob/v1.2.0/CHANGELOG.md).

---

## Installation

After installing via HACS:

1. Go to **Settings** → **Devices & Services** → **Add Integration**
2. Search for **"Homey"**
3. Enter your Homey IP address and API key
4. Select devices to import

For detailed setup instructions, see the [README](README.md).
