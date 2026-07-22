# Homey Integration for Home Assistant

[![GitHub](https://img.shields.io/github/license/ifMike/homeyHASS-legacy)](https://github.com/ifMike/homeyHASS-legacy/blob/main/LICENSE)
[![GitHub issues](https://img.shields.io/github/issues/ifMike/homeyHASS)](https://github.com/ifMike/homeyHASS/issues)
[![GitHub stars](https://img.shields.io/github/stars/ifMike/homeyHASS-legacy)](https://github.com/ifMike/homeyHASS-legacy/stargazers)

**Version**: 1.2.8 | **Last Updated**: 2026-07-22 | [Changelog](CHANGELOG.md)

> ## Legacy 1.x repository (domain `homey`)
>
> This repository is the **dedicated HACS source for the 1.x line** (`custom_components/homey/`, domain `homey`). It receives **only 1.2.x updates** — you will not get HACS notifications for 2.x releases from the main [`ifMike/homeyHASS`](https://github.com/ifMike/homeyHASS) repo.
>
> - **Existing 1.x users**: Add **`https://github.com/ifMike/homeyHASS-legacy`** in HACS (see [Installation](#installation)). If you previously used `ifMike/homeyHASS`, remove that custom repository first.
> - **New users**: Install **[2.0.0 from `ifMike/homeyHASS`](https://github.com/ifMike/homeyHASS)** (domain `homey_hass`) instead.
> - **Ready to migrate?** See the [2.0.0 migration guide](https://github.com/ifMike/homeyHASS#migrating-from-1x-to-200) on the main repository.

A Homey integration for Home Assistant that automatically discovers and connects all your Homey devices, making them available natively in Home Assistant.

---

## Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
  - [Installation via HACS (Recommended)](#installation-via-hacs-recommended)
  - [Switching from ifMike/homeyHASS](#switching-from-ifmikehomeyhass)
  - [Manual Installation](#manual-installation)
- [Configuration](#configuration)
- [Usage](#usage)
- [Updating](#updating)
- [Error Messages](#error-messages)
- [Troubleshooting](#troubleshooting)
- [Supported Devices](#supported-devices)
- [Known Issues](#known-issues--limitations)
- [Development](#development)
- [API Documentation](#api-documentation)
- [License](#license)
- [Support](#support)


---

## Overview

This Homey integration brings your [Homey](https://homey.app) hub into Home Assistant, allowing you to control all your Homey devices directly from Home Assistant. It supports a wide range of device types including lights, switches, sensors, climate devices, and more. Additionally, it allows you to trigger Homey Flows (automations) from Home Assistant.

**Note**: This is a community-driven project and is not officially affiliated with Athom or Home Assistant. It works, but expect occasional updates and fixes. Report issues on GitHub.

**Requirements**: Homey Pro 2023 or later. Homey Pro 2019 and older do not support API Keys or the Local API.


---

## Features

**Device Discovery and Control**
- Automatic device discovery from your Homey hub
- Lights, switches, sensors, binary sensors, covers, climate, fans, locks, media players, scenes, buttons, numbers, and selects
- Full light control: dimming, color (HS), and color temperature
- Sensor types: temperature, humidity, pressure, power, voltage, current, luminance, CO2, CO, noise, rain, wind, UV, PM2.5/PM10, VOC, AQI, frequency, gas, soil moisture/temperature, energy
- Security sensors: motion, contact, tamper, smoke, CO alarm, CO2 alarm, water leak, battery, gas, fire, panic, burglar, vibration

**Homey Integration**
- Homey Flows: trigger, enable, and disable automations (Standard and Advanced) as button entities or via service calls
- Scenes and Moods: activate directly from Home Assistant
- Logic Variables: import as Number, Switch, and Text entities
- Physical device buttons: exposed as Button entities for automation triggers
- Media player: full metadata support (artist, album, track, duration, position, shuffle, repeat)

**Temperature units**
- Temperatures use the unit reported by Homey (`°C` or `°F` from capability metadata).
- Home Assistant displays them in the unit for your region (**Settings → System → Home information**; region sets Metric = Celsius or US Customary = Fahrenheit).
- If a device sends the wrong unit, set an override under **Settings → Devices & services → Homey → Configure → Device temperature units**, or call `homey.set_device_temperature_unit`.

**Organization and Sync**
- Room/area organization based on Homey rooms
- Automatic sync of device changes (renames, room changes, deletions)
- Real-time updates via Socket.IO (less than 1 second latency)
- Smart polling fallback (5–10 seconds) when Socket.IO is unavailable
- Device grouping: all entities from the same device under one device entry

**Setup**
- Simple configuration flow through Home Assistant UI
- Options and reauth flows: update host, API key, and polling settings without reinstalling
- Permission checking with graceful degradation

---

## Prerequisites

**Homey Compatibility**

Homey Pro 2019 and older do not support API Keys or the Local API. This integration requires Homey Pro 2023 or later.

If you have an older Homey, you can bridge Homey and Home Assistant using the universal MQTT approach: [Tutorial: Pro - How to integrate Home Assistant with Homey](https://community.homey.app/t/tutorial-pro-how-to-integrate-home-assistant-with-homey-pro-and-v-v/92641).

**API Key**

Create an API key in Homey before installing:

1. Open the [Homey Web App](https://homey.app)
2. Go to **Settings** → **API Keys**
3. Click **New API Key**
4. Give it a name (e.g., "Home Assistant")
5. Select the necessary permissions:

**Required**
- **View devices** (`homey.device.readonly`) - Discover and read device states
- **Control devices** (`homey.device.control`) - Control devices (on/off, brightness, etc.)
- **View System** (`homey.system.readonly`) - Required for Socket.IO real-time updates. Without this, the integration uses polling (5–10 second updates).

**Recommended**
- **View Zones** (`homey.zone.readonly`) - Room/area organization
- **View Flows** (`homey.flow.readonly`) - List flows
- **Start Flows** (`homey.flow.start`) - Trigger, enable, disable flows
- **View Moods** (`homey.mood.readonly`) - List moods
- **Set Moods** (`homey.mood.set`) - Activate moods
- **View Variables** (`homey.logic.readonly`) - List Logic variables
- **Variables** (`homey.logic`) - Update Logic variables from Home Assistant

6. Copy the API key (you will not be able to see it again).

**Permission Impact**

| Permission              | Impact if Missing                          |
|-------------------------|--------------------------------------------|
| `homey.device.readonly` | Integration will not work                  |
| `homey.device.control`  | Device control disabled                    |
| `homey.system.readonly` | Socket.IO disabled; polling only (5–10 s) |
| `homey.zone.readonly`  | No room organization                       |
| `homey.flow.readonly`  | Flow listing disabled                      |
| `homey.flow.start`     | Flow control disabled                      |
| `homey.mood.readonly`  | Mood listing disabled                      |
| `homey.mood.set`       | Mood activation disabled                   |
| `homey.logic.readonly` | Logic variables disabled                   |
| `homey.logic`          | Logic updates disabled                     |

**Recommendation**: Grant full access to all permissions. If you later want to use Logic variables, flows, moods, or other features, you will need to create a new API key with those permissions and update the integration. Granting full access from the start avoids having to reconfigure later.

**Important**: Keep this API key safe. You will need it during setup.

---

## Installation

### Installation via HACS (Recommended)

Use **this repository** (`ifMike/homeyHASS-legacy`) in HACS so update notifications stay on the 1.2.x line only.

1. Open **HACS** → **Integrations**
2. Click the three dots menu → **Custom repositories**
3. Add: `https://github.com/ifMike/homeyHASS-legacy` (Category: Integration)
4. Search for **Homey** and click **Download**
5. Restart Home Assistant
6. Go to **Settings** → **Devices & Services** → **Add Integration** → Search for **Homey**

**Updating via HACS**: HACS → Integrations → Homey Integration → **Update** when a new **1.2.x** release is available. You will not be offered 2.x versions from this repository.

### Switching from ifMike/homeyHASS

If you previously added the main [`ifMike/homeyHASS`](https://github.com/ifMike/homeyHASS) repository in HACS, switch to this legacy repo to stop 2.x update notifications:

1. **HACS** → **Integrations** → three dots → **Custom repositories**
2. Remove `https://github.com/ifMike/homeyHASS` (keep your installed integration — do not delete the config entry)
3. Add `https://github.com/ifMike/homeyHASS-legacy` (Category: Integration)
4. **HACS** → **Integrations** → **Homey Integration** → three dots → **Redownload** → select **v1.2.8** (or latest 1.2.x)
5. Restart Home Assistant

Your existing config entry, entities, and automations (`homey.*` services) are unchanged.

**If you already see a 2.x update notification** from the old repository: use **Skip update** on the HACS update entity, or disable that update entity, until you complete the switch above.

### Manual Installation

**Option 1: Direct File System Access**

1. Download or clone this repository:
   ```bash
   git clone https://github.com/ifMike/homeyHASS-legacy.git
   ```

2. Copy the `custom_components/homey` folder to your Home Assistant `custom_components` directory:
   ```
   <config directory>/custom_components/homey/
   ```
   Example: `/config/custom_components/homey/`

3. Restart Home Assistant

4. Go to **Settings** → **Devices & Services** → **Add Integration**

5. Search for **Homey** and follow the setup instructions

**Option 2: Using Samba (Network Drive)**

1. **Enable Samba in Home Assistant**
   - Settings → Add-ons → Add-on Store
   - Search for "Samba share" and install
   - Configure username and password, then Start

2. **Connect from your computer**
   - macOS: Finder → Go → Connect to Server → `smb://YOUR_HA_IP`
   - Windows: File Explorer → `\\YOUR_HA_IP`
   - Log in with the Samba credentials

3. **Copy files**
   - Navigate to `config/custom_components/`
   - Copy the `homey` folder there

4. **Restart Home Assistant** and add the integration

**Migrating from manual to HACS**: Delete the `custom_components/homey` folder, restart Home Assistant, then install via HACS. Your configuration is preserved.


---

## Configuration

1. Go to **Settings** → **Devices & Services** → **Add Integration**
2. Search for **Homey**
3. Enter:
   - **Host**: Your Homey IP address or hostname (e.g., `192.168.1.100` or `homey.local`, no `http://`)
   - **Token**: The API key from Homey
4. Click **Submit**

The integration will discover your devices and create entities.

**Homey Self Hosted Server**

For Homey Self Hosted Server (SHS), include the port in the host:

- Host: `192.168.1.100:4859` (HTTP, default port 4859)
- Host: `https://192.168.1.100:4860` (HTTPS, BETA only)

---

## Usage

**Devices**

All Homey devices appear under **Settings** → **Devices & Services** → **Homey**, grouped by device.

**Homey Flows**

- Each enabled Flow appears as a button entity
- Service calls: `homey.trigger_flow`, `homey.enable_flow`, `homey.disable_flow`
- Use `flow_id` or `flow_name` in service data

  Example automation:
  ```yaml
  action:
    - service: homey.trigger_flow
      data:
        flow_name: "Evening Scene"
  ```

**Logic Variables**

- Number, Boolean, and String variables appear as `number`, `switch`, and `text` entities
- Require `homey.logic.readonly` and `homey.logic` permissions

**Scenes and Moods**

- Activate Homey scenes and moods as Scene entities
- Moods require `homey.mood.readonly` and `homey.mood.set` permissions

**Physical Buttons**

- Physical device buttons (e.g., Hue dimmer, IKEA remote) appear as Button entities

---

## Updating

**Via HACS (this repository)**

1. HACS → Integrations → Homey Integration
2. Click **Update** when a new **1.2.x** release is available
3. Restart Home Assistant

Only 1.2.x versions are published in [`ifMike/homeyHASS-legacy`](https://github.com/ifMike/homeyHASS-legacy). To move to 2.x later, follow the [migration guide on the main repository](https://github.com/ifMike/homeyHASS#migrating-from-1x-to-200).

**Manual**

1. Download the latest **1.2.x** release from [GitHub Releases](https://github.com/ifMike/homeyHASS-legacy/releases)
2. Replace the `custom_components/homey` folder
3. Restart Home Assistant
4. Reload the integration: Settings → Devices & Services → Homey → Configure → Reload

**If devices stop working after update**

- Reload the integration
- Check API key permissions
- Review the [CHANGELOG](CHANGELOG.md)
- Restore a backup if you created one

---

## Error Messages

This section explains common setup errors and how to resolve them. Use your browser's search (Ctrl+F / Cmd+F) to find your error.

| Error code / Search for | Section |
|-------------------------|---------|
| `invalid_auth`, Authentication failed | [Authentication failed](#invalid_auth) |
| `cannot_connect`, Unable to connect | [Unable to connect](#cannot_connect) |
| `already_configured`, already configured | [Already configured](#already_configured) |
| `cannot_fetch_devices`, Unable to fetch devices | [Cannot fetch devices](#cannot_fetch_devices) |
| `unknown`, unexpected error | [Unknown error](#unknown) |
| Discovered Homey | ["Discovered" Homey keeps appearing](#discovered-homey-keeps-appearing) |
| Sensors Unavailable | [Sensors show Unavailable](#sensors-show-unavailable) |
| Real-time updates | [Real-time updates not working](#real-time-updates-not-working) |

### invalid_auth — Authentication failed

**When it appears**: During setup or reauthentication when entering the API key.

**Possible causes**
- Invalid or expired API key
- API key missing required permissions
- Homey Pro 2019 or older (no API Keys feature)

**Solutions**

1. Create a new API key in Homey: **Settings** → **API Keys** → **New API Key**
2. Grant at least: Devices (read), Flows (read), System (read)
3. Copy the full key and paste it into the setup form
4. If you have Pro 2019 or older, this integration is not supported; upgrade to Pro 2023+ for API support

### cannot_connect — Unable to connect

**When it appears**: During setup when the integration cannot reach Homey.

**Possible causes**
- Wrong IP address or hostname
- Homey powered off or unreachable
- Firewall blocking connections
- Homey Pro 2019 or older (no Local API)

**Solutions**

1. Verify the IP in the Homey app or your router
2. Ensure Homey and Home Assistant are on the same network
3. Try pinging the IP from your Home Assistant host
4. Use a static IP instead of `.local` hostnames for stability
5. If using Pro 2019 or older, upgrade to Pro 2023+ for Local API support

### already_configured — This Homey hub is already configured

**When it appears**: When adding a duplicate integration for the same Homey hub.

**Solutions**

- Remove the existing Homey integration first if you want to reconfigure
- Or use **Configure** on the existing integration to update host or API key

### "Discovered" Homey keeps appearing

**When it appears**: A discovery card appears even though you have already configured Homey manually.

**Explanation**: Manual setup uses `homeyId`; discovery uses MAC/hostname. They may not match initially.

**Solutions**

- Ignore the discovery card; your manual configuration is valid
- Or add the discovered integration; it will use the same host and you can configure it

### cannot_fetch_devices — Unable to fetch devices from Homey

**When it appears**: During device selection step. The connection succeeded but the device list could not be retrieved.

**What happens**: The integration proceeds with all devices. You can continue setup.

**Possible causes**
- Temporary API or network issue
- API key missing `homey.device.readonly` permission

**Solutions**
- Check API key has **View devices** permission
- Retry setup; if it persists, check logs for details

### unknown — An unexpected error occurred

**When it appears**: During setup when an unexpected error occurs.

**Solutions**
- Check logs: Settings → System → Logs (look for `custom_components.homey`)
- Enable debug logging and retry
- Report the issue on GitHub with log output

### Sensors show Unavailable

**When it appears**: Controls (lights, switches) work, but sensors show Unavailable.

**Solutions**

- Update to version 1.2.1 or later (fixes a registry filter issue)
- Reload the integration: Settings → Devices & Services → Homey → Configure → Reload

### Real-time updates not working

**When it appears**: Device states update slowly (every 5–10 seconds) instead of instantly.

**Cause**: Socket.IO requires the `homey.system.readonly` permission.

**Solutions**

1. Create a new API key in Homey with **System** → **View System** enabled
2. Update the integration configuration with the new key
3. Restart Home Assistant or reload the integration
4. Check logs for "Socket.IO real-time updates enabled" to confirm success

---

## Troubleshooting

### Connection Issues

- Verify host address (IP or hostname, no `http://`)
- Verify API key is correct and has required permissions
- Ensure Home Assistant can reach Homey on the network (ping, firewall)
- Check logs: Settings → System → Logs

  Enable debug logging if needed:
  ```yaml
  logger:
    default: info
    logs:
      custom_components.homey: debug
  ```

### Devices Not Appearing

- Check device capabilities (see [Supported Devices](SUPPORTED_DEVICES.md))
- Reload integration: Settings → Devices & Services → Homey → Configure → Reload
- Try removing and re-adding the integration
- Check logs for discovery errors

### Duplicate Devices

- Reload the integration
- Restart Home Assistant

### Device Changes Not Syncing

- Changes sync during polling (up to 30 seconds)
- Reload the integration to force a refresh

### Gathering Device Information

For device classification issues (wrong type, missing capabilities):

1. Go to [Homey Developer Tools](https://tools.developer.homey.app)
2. Select your hub → Devices → find your device
3. Copy the device ID
4. Use Web API Playground to fetch device info

```javascript
Homey.devices.getDevice({ id: "YOUR_DEVICE_ID" })
  .then(d => ({
    id: d.id,
    name: d.name,
    class: d.class,
    driverId: d.driverId,
    capabilities: d.capabilities,
    capabilitiesObj: d.capabilitiesObj,
  }));
```

5. Include the JSON output when reporting an issue

---

## Supported Devices

See [SUPPORTED_DEVICES.md](SUPPORTED_DEVICES.md) for a full list of supported device types and capabilities.

**Overview**

- Lights, switches, sensors, binary sensors, covers, climate, fans, locks, media players
- Scenes, moods, buttons, numbers, selects, vacuum cleaners
- Generic support for `measure_*`, `meter_*`, boolean, and enum capabilities

---

## Known Issues & Limitations

**Room/Zone Detection**

- Requires `homey.zone.readonly` permission. Without it, devices work but are not organized by rooms.

**Config Flow Window Size**

- Device selection dialog has a fixed size. Use browser search (Ctrl+F / Cmd+F) to find devices.

**Entity Name Updates**

- Entity names may not update when device names change in Homey. Reload the integration to refresh.

---

## Development

**Project Structure**

```
custom_components/homey/
├── __init__.py
├── binary_sensor.py
├── button.py
├── climate.py
├── config_flow.py
├── const.py
├── coordinator.py
├── cover.py
├── device_info.py
├── fan.py
├── homey_api.py
├── light.py
├── lock.py
├── manifest.json
├── media_player.py
├── number.py
├── permissions.py
├── scene.py
├── select.py
├── sensor.py
├── services.yaml
├── strings.json
├── switch.py
├── text.py
├── vacuum.py
└── translations/
    └── en.json
```

**Contributing**

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Open a Pull Request

**Reporting Issues**

- Check [existing issues](https://github.com/ifMike/homeyHASS/issues) first
- Include: description, steps to reproduce, Home Assistant version, Homey firmware version, relevant logs

---

## API Documentation

- [Homey API Documentation](https://api.developer.homey.app/)
- [Homey API Keys Guide](https://support.homey.app/hc/en-us/articles/8178797067292-Getting-started-with-API-Keys)
- [Homey Local API](https://apps.developer.homey.app/the-basics/local-api)

---

## License

This project is licensed under the MIT License. See [LICENSE](LICENSE) for details.

---

## Support

1. Check the [Error Messages](#error-messages) and [Troubleshooting](#troubleshooting) sections
2. Search [existing issues](https://github.com/ifMike/homeyHASS/issues)
3. Create a new issue if needed

---

**Credits**

- Author: Mikael Collin ([@ifmike](https://github.com/ifMike))
- Built for Home Assistant
- Uses Homey Local API by Athom
- Thanks to [@PeterKawa](https://github.com/PeterKawa) for testing and feedback
- Special thanks to the [Homey community](https://community.homey.app/t/re-homey-integration-for-home-assistant-now-available/) for support and feedback

---

**Support the Project**

I'm not asking for money. This integration is free to use. If you find it useful and want to help with further development (or buy me the occasional coffee), you can:

- [Buy Me A Coffee](https://buymeacoffee.com/ifmike)
- [PayPal](https://www.paypal.com/paypalme/ifmike)

Completely optional. Every bit helps keep the project going.
