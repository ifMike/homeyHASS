# Homey Integration for Home Assistant

[![GitHub](https://img.shields.io/github/license/ifMike/homeyHASS)](https://github.com/ifMike/homeyHASS/blob/main/LICENSE)
[![GitHub issues](https://img.shields.io/github/issues/ifMike/homeyHASS)](https://github.com/ifMike/homeyHASS/issues)
[![GitHub stars](https://img.shields.io/github/stars/ifMike/homeyHASS)](https://github.com/ifMike/homeyHASS/stargazers)

**Version**: 2.1.0 | **Last Updated**: 2026-08-11 | [Changelog](CHANGELOG.md)

> ### New installation?
> Search **Homey** in HACS and add **Homey 2.x**. **No migration steps apply.**
>
> ### Upgrading from 1.x?
> Use the **guided migration assistant** in 2.1.0 — see [Migrating from 1.x](#migrating-from-1x-to-2x).
>
> ### Staying on 1.x for now?
> Use the legacy HACS repo [`ifMike/homeyHASS-legacy`](https://github.com/ifMike/homeyHASS-legacy) (v1.2.x only). Do not update to 2.x from this repository until you are ready to migrate.

A Homey integration for Home Assistant that automatically discovers and connects all your Homey devices, making them available natively in Home Assistant.

---

## Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
  - [Installation via HACS (Recommended)](#installation-via-hacs-recommended)
  - [Manual Installation](#manual-installation)
- [Configuration](#configuration)
- [Usage](#usage)
- [Legacy 1.x (HACS)](#legacy-1x-hacs)
- [Updating](#updating)
- [Migrating from 1.x to 2.x](#migrating-from-1x-to-2x)
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
- If a device sends the wrong unit, set an override under **Settings → Devices & services → Homey → Configure → Device temperature units**, or call `homey_hass.set_device_temperature_unit`.

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

The integration is listed in the **official HACS default catalog** ([hacs/default PR #6696](https://github.com/hacs/default/pull/6696)). No custom repository is required for new installs.

1. Open **HACS** → **Integrations**
2. Click **+ Explore & download repositories** (or use the search field)
3. Search for **Homey** (repository: [ifMike/homeyHASS](https://github.com/ifMike/homeyHASS))
4. Click **Download**
5. Restart Home Assistant
6. Go to **Settings** → **Devices & Services** → **Add Integration** → Search for **Homey**

**Already using a custom repository?** If you previously added `https://github.com/ifMike/homeyHASS` manually, that still works. You can remove it from **Custom repositories** now that the integration is in the default catalog — HACS will continue to track updates from the same GitHub repo.

**Updating via HACS**: HACS → Integrations → Homey Integration → **Update** (when available). **1.x users:** use [`ifMike/homeyHASS-legacy`](https://github.com/ifMike/homeyHASS-legacy) instead — see [Legacy 1.x (HACS)](#legacy-1x-hacs).

**Beta/Dev releases**: Click **Redownload** and select the version (e.g., `dev`) from the dropdown.

### Manual Installation

**Option 1: Direct File System Access**

1. Download or clone this repository:
   ```bash
   git clone https://github.com/ifMike/homeyHASS.git
   ```

2. Copy the `custom_components/homey_hass` folder to your Home Assistant `custom_components` directory:
   ```
   <config directory>/custom_components/homey_hass/
   ```
   Example: `/config/custom_components/homey_hass/`

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
   - Copy the `homey_hass` folder there

4. **Restart Home Assistant** and add the integration

**Migrating from manual to HACS (same version)**: Delete the `custom_components/homey_hass` folder, restart Home Assistant, then install via HACS. Your configuration is preserved.

**Migrating from 1.x?** See [Migrating from 1.x to 2.x](#migrating-from-1x-to-2x). New installations do not need migration.


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
- Service calls: `homey_hass.trigger_flow`, `homey_hass.enable_flow`, `homey_hass.disable_flow`
- Use `flow_id` or `flow_name` in service data

  Example automation:
  ```yaml
  action:
    - service: homey_hass.trigger_flow
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

## Legacy 1.x (HACS)

If you have a **working 1.x installation** (domain `homey`, folder `custom_components/homey/`) and do not want 2.x update notifications from this repository, use the dedicated legacy HACS source:

**[`ifMike/homeyHASS-legacy`](https://github.com/ifMike/homeyHASS-legacy)**

That repository publishes **only 1.2.x releases**. HACS will not offer 2.0.0 or later from it.

### Switch from this repo to the legacy repo

1. **HACS** → **Integrations** → three dots → **Custom repositories**
2. Remove `https://github.com/ifMike/homeyHASS`
3. Add `https://github.com/ifMike/homeyHASS-legacy` (Category: Integration)
4. **Homey Integration** → three dots → **Redownload** → **v1.2.8** (or latest 1.2.x)
5. Restart Home Assistant

Your config entry, entities, and `homey.*` automations are unchanged.

If you already see a **2.x update notification**, use **Skip update** on the HACS update entity until you switch repositories.

When you are ready for 2.x, follow [Migrating from 1.x to 2.x](#migrating-from-1x-to-2x). Install from the default HACS catalog (search **Homey**) or this repository.

---

## Updating

### Version 2.1.0 — migration assistant

| If you are… | What to do |
|-------------|------------|
| A **new user** | Install **2.1.0** normally via HACS. No migration steps. |
| On **2.0.x** already | HACS → **Update** to **2.1.0** → restart. No migration steps. |
| On **1.x** and **ready to migrate** | Follow [Migrating from 1.x](#migrating-from-1x-to-2x) **before** updating. |
| On **1.x** and **not ready** | Use HACS repo **[`ifMike/homeyHASS-legacy`](https://github.com/ifMike/homeyHASS-legacy)**. Do **not** install 2.x from this repository. |

Updating from 1.x to 2.x **without** migrating breaks your integration (unavailable entities, failed config entry, broken `homey.*` automations).

### Via HACS (2.0.x → 2.1.0)

1. HACS → Integrations → Homey → **Update**
2. Restart Home Assistant

No config migration required.

### Via HACS (1.x → 2.1.0)

Only when you are ready to migrate — see [Migrating from 1.x](#migrating-from-1x-to-2x):

1. Create a Home Assistant **backup**
2. Install **2.1.0** (keep your existing **Homey 1.x** entry until migration completes)
3. Restart Home Assistant
4. **Add integration → Homey 2.x → Migrate from Homey 1.x**
5. Complete post-migration steps (automations, delete old folder)

### Via HACS (already on 2.0.x / 2.1.x)

1. HACS → Integrations → Homey → **Update**
2. Restart Home Assistant

### Manual

1. Download the latest version from GitHub
2. Replace the `custom_components/homey_hass` folder
3. Restart Home Assistant
4. Reload the integration: Settings → Devices & Services → Homey → Configure → Reload

### If devices stop working after update

- If you updated from 1.x without migrating, see [Migrating from 1.x to 2.x](#migrating-from-1x-to-2x)
- Reload the integration
- Check API key permissions
- Review the [CHANGELOG](CHANGELOG.md)
- Restore a backup if you created one

---

## Migrating from 1.x to 2.x

**Applies only if you have an existing Homey 1.x integration** (domain `homey`, folder `custom_components/homey/`). **New installations skip this entirely** — add Homey via HACS and enter your host and API key.

Version 2.0.0+ uses domain `homey_hass` (required for the [official HACS catalog](https://github.com/hacs/default/pull/6696)). The display name in Home Assistant is still **Homey**, but services change from `homey.*` to `homey_hass.*`.

### Before you start

- [ ] Create a **Home Assistant backup**
- [ ] Note your Homey **IP/hostname** and **API key** (Homey app → Settings → API Keys)
- [ ] Plan time to update automations and dashboards afterward

### Guided migration (recommended — 2.1.0+)

1. **Install 2.x alongside 1.x**
   - HACS → Integrations → Homey → Update to **2.1.0**, **or** copy `custom_components/homey_hass/` manually
   - Keep `custom_components/homey/` and your existing **Homey** config entry for now
2. **Restart Home Assistant**
3. **Settings → Devices & services → Add integration → Homey 2.x**
   - While both 1.x and 2.x folders are installed, you may see **Homey** (1.x) and **Homey 2.x** — always pick **Homey 2.x**
   - You should then see **Upgrade from Homey 1.x** — choose **Migrate from Homey 1.x** (not “Set up as new installation”)
4. **Confirm migration options**
   - ☑ **Keep my entity IDs** (recommended — preserves dashboards and automations)
   - ☑ **Remove the old Homey 1.x integration when done** (recommended once 2.x works)
5. **Wait for setup to finish** — you should get a **Migration complete** notification
6. **Verify** under **Settings → Devices & services → Homey 2.x** that devices respond
7. **Post-migration cleanup**
   - **If** automations/scripts use `homey.*` **services** (e.g. `homey.trigger_flow`), update to `homey_hass.*` (see [service table](#service-name-changes)). Automations that only trigger on entity states need no changes when entity IDs were preserved.
   - Delete `custom_components/homey/` from your config directory
   - Restart Home Assistant
   - Click **Ignore** on any **Homey (IP unknown)** card under Discovered integrations

**Already added 2.x manually but still have 1.x?** Open **Configure → Migrate from Homey 1.x** on your **Homey 2.x** entry.

### Which integration to pick?

| Name in Add integration | What it is |
|-------------------------|------------|
| **Homey 2.x** | Current integration (`homey_hass`) — use this |
| **Homey** | Legacy 1.x (`homey`) — only if you are **not** migrating yet |

After you delete `custom_components/homey/` and restart, only **Homey 2.x** remains in the list. The **2.x** suffix avoids confusion while both versions can coexist during migration.

### What you see during setup

| Your situation | What Home Assistant shows |
|----------------|---------------------------|
| **New install** (no 1.x folder) | **Homey 2.x** → normal connect form (host + API key). No migration screens. |
| **1.x still configured** | **Homey 2.x** → **Upgrade from Homey 1.x** with migrate vs fresh options |
| **Already on 2.x** | “This Homey hub is already configured” if you try to add again |
| **After migration** | One **Homey 2.x** entry only. Migration menu options disappear. |

### Why device count may differ

The integration tile counts devices in Home Assistant’s registry. After migration you may see slightly fewer devices than 1.x showed if old registry entries lingered for devices deleted from Homey, or if your 1.x **device filter** excluded some devices. Use **Configure → Manage Devices** to add any missing ones.

### Service name changes

| Old (1.x) | New (2.x) |
|-----------|-----------|
| `homey.trigger_flow` | `homey_hass.trigger_flow` |
| `homey.enable_flow` | `homey_hass.enable_flow` |
| `homey.disable_flow` | `homey_hass.disable_flow` |
| `homey.set_device_temperature_unit` | `homey_hass.set_device_temperature_unit` |
| `homey.rename_entities_to_titles` | `homey_hass.rename_entities_to_titles` |
| `homey.test_capability_report` | `homey_hass.test_capability_report` |

### Manual migration (fallback)

Use this if the guided assistant is unavailable:

1. **Settings → Devices & services → Homey** (1.x entry) → **Delete** the config entry
2. Install **2.x** and confirm `custom_components/homey_hass/` exists
3. Delete `custom_components/homey/` if it still exists
4. **Restart Home Assistant**
5. **Add integration → Homey 2.x** — enter host and API key; select devices
6. Update automations (service table above)
7. Remove orphaned unavailable entities if needed

### Troubleshooting migration

| Problem | What to do |
|---------|------------|
| Two **Homey** entries in Add integration | Pick **Homey 2.x** (current). Plain **Homey** is legacy 1.x. |
| Migration screen does not appear | Confirm Homey **1.x** is still configured **and** `custom_components/homey/` exists. Restart HA after installing 2.x. Pick **Homey 2.x**, not **Homey**. |
| “Already configured” | Remove the duplicate Homey entry, or delete failed 2.x entry and migrate again. |
| “Failed to set up” | Check logs (filter `homey_hass`). Reload the entry after updating to **2.1.0**. |
| **Homey (IP unknown)** in Discovered | Normal after migration. Click **Ignore** — do not add a second entry. |
| Entity ID conflicts in logs | Usually from overlapping 1.x and 2.x entries. Complete migration and remove 1.x. |

### After migration

- Enable debug logging if needed: `custom_components.homey_hass: debug` (see [Troubleshooting](#troubleshooting))
- Open an issue on GitHub if devices are missing after re-setup

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
- Check logs: Settings → System → Logs (look for `custom_components.homey_hass`)
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
      custom_components.homey_hass: debug
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
custom_components/homey_hass/
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
