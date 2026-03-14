# Homey Integration for Home Assistant

[![GitHub](https://img.shields.io/github/license/ifMike/homeyHASS)](https://github.com/ifMike/homeyHASS/blob/main/LICENSE)
[![GitHub issues](https://img.shields.io/github/issues/ifMike/homeyHASS)](https://github.com/ifMike/homeyHASS/issues)
[![GitHub stars](https://img.shields.io/github/stars/ifMike/homeyHASS)](https://github.com/ifMike/homeyHASS/stargazers)

**Version**: 1.2.0-dev.1 | **Last Updated**: 2026-03-03 | [Changelog](CHANGELOG.md)
A Homey integration for Home Assistant that automatically discovers and connects all your Homey devices, making them available natively in Home Assistant.

---

## Overview

This Homey integration brings your [Homey](https://homey.app) hub into Home Assistant, allowing you to control all your Homey devices directly from Home Assistant. It supports a wide range of device types including lights, switches, sensors, climate devices, and more. Additionally, it allows you to trigger Homey Flows (automations) from Home Assistant.

**Note**: This is a work in progress made by just one guy with too much time on his hands who couldn't sit on his ass waiting for someone else to create this plugin. It works, but expect bugs, occasional updates, and the occasional "oops, that broke something" moment. 🤷‍♂️

---

## Features

- 🔍 **Automatic Device Discovery**: Automatically discovers all devices from your Homey hub
- 💡 **Multiple Entity Types**: Supports lights, switches, sensors, binary sensors, covers, climate devices, fans, locks, media players, scenes, buttons, numbers, and selects
- 🎨 **Full Light Control**: Supports dimming, color (HS), and color temperature control
- 📊 **Comprehensive Sensors**: Temperature, humidity, pressure, power, voltage, current, luminance, CO2, CO, noise, rain, wind, UV, PM2.5/PM10, VOC, AQI, frequency, gas, soil moisture/temperature, and energy
- 🚨 **Security Sensors**: Motion, contact, tamper, smoke, CO alarm, CO2 alarm, water leak, battery, gas, fire, panic, burglar, and vibration sensors
- 🌡️ **Climate Control**: Thermostat support with target temperature and humidity control, plus HVAC mode support (OFF, HEAT, COOL, AUTO, HEAT_COOL)
- 🎬 **Homey Flows**: Trigger, enable, and disable your Homey automations (Standard and Advanced Flows) from Home Assistant as button entities or via service calls
- 🎭 **Scenes & Moods**: Activate Homey scenes and moods directly from Home Assistant
- 🧠 **Homey Logic Variables**: Import Logic variables as native Number, Switch, and Text entities
- 🔘 **Physical Buttons**: Physical device buttons appear as Button entities for automation triggers
- 🎵 **Media Player Metadata**: Full media metadata support including artist, album, track, duration, position, shuffle, and repeat
- 🏠 **Room Organization**: Automatically assigns devices to Home Assistant Areas based on Homey rooms
- 🔄 **Automatic Synchronization**: Automatically syncs device changes from Homey (renames, room changes, deletions)
- ⚡ **Real-Time Updates**: Socket.IO-powered instant state synchronization (< 1 second latency) - device changes in Homey appear immediately in Home Assistant
- 📡 **Smart Polling**: Automatic fallback to polling (5-10 seconds) if Socket.IO fails, with dynamic intervals (60s when Socket.IO active, 10s when inactive)
- ⚙️ **Easy Setup**: Simple configuration flow through Home Assistant's UI
- ⚙️ **Options & Reauth flows**: Update Homey host/IP, API key, and fallback polling settings without reinstalling
- 🎯 **Smart Device Grouping**: All entities from the same device are automatically grouped under one device entry
- 🔐 **Permission Management**: Comprehensive permission checking with graceful degradation - integration works even with limited permissions

---

## Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
  - [Manual Installation](#manual-installation)
    - [Option 1: Direct File System Access](#option-1-direct-file-system-access)
    - [Option 2: Using Samba (Network Drive)](#option-2-using-samba-network-drive)
  - [Installation via HACS](#installation-via-hacs)
    - [Prerequisites](#prerequisites-1)
    - [Installation Steps](#installation-steps)
    - [Updating via HACS](#updating-via-hacs)
    - [Enabling Automatic Updates for Beta/Dev Releases](#enabling-automatic-updates-for-betadev-releases)
  - [Switching Between Release Channels (Stable/Beta/Dev)](#switching-between-release-channels-stablebetadev)
  - [Migrating from Manual Installation to HACS](#migrating-from-manual-installation-to-hacs)
- [Updating the Integration](#updating-the-integration)
  - [Step 1: Download the Latest Version](#step-1-download-the-latest-version)
  - [Step 2: Replace the Integration Files](#step-2-replace-the-integration-files)
  - [Step 3: Restart Home Assistant](#step-3-restart-home-assistant)
  - [Step 4: Reload the Integration (Recommended)](#step-4-reload-the-integration-recommended)
  - [Step 5: Verify the Update](#step-5-verify-the-update)
  - [Troubleshooting Updates](#troubleshooting-updates)
- [Configuration](#configuration)
  - [Setup Steps](#setup-steps)
  - [Homey Self Hosted Server Configuration](#homey-self-hosted-server-configuration)
- [Usage](#usage)
  - [Devices](#devices)
  - [Homey Flows (Automations)](#homey-flows-automations)
    - [1. Button Entities](#1-button-entities)
    - [2. Service Calls](#2-service-calls)
  - [Homey Logic Variables](#homey-logic-variables)
  - [Homey Scenes and Moods](#homey-scenes-and-moods)
  - [Physical Device Buttons](#physical-device-buttons)
- [Device Organization](#device-organization)
- [Automatic Synchronization](#automatic-synchronization)
  - [Device Name Changes](#device-name-changes)
  - [Room/Area Changes](#roomarea-changes)
  - [Device Deletion](#device-deletion)
  - [Update Frequency](#update-frequency)
- [Real-Time Updates](#real-time-updates)
  - [How It Works](#how-it-works)
  - [Requirements](#requirements)
  - [Benefits](#benefits)
  - [Troubleshooting Real-Time Updates](#troubleshooting-real-time-updates)
- [Supported Devices](SUPPORTED_DEVICES.md)
- [Known Issues & Limitations](#known-issues--limitations)
  - [Room/Zone Detection](#roomzone-detection)
  - [Config Flow Window Size](#config-flow-window-size)
  - [Entity Name Updates](#entity-name-updates)
- [Troubleshooting](#troubleshooting)
  - [Connection Issues](#connection-issues)
  - [Devices Not Appearing](#devices-not-appearing)
  - [Duplicate Devices](#duplicate-devices)
  - [Real-time Updates Not Working](#real-time-updates-not-working)
  - [Device Changes Not Syncing](#device-changes-not-syncing)
  - [Gathering Device Information for Troubleshooting](#gathering-device-information-for-troubleshooting)
- [Development](#development)
  - [Project Structure](#project-structure)
  - [Key Technical Features](#key-technical-features)
  - [Contributing](#contributing)
  - [Reporting Issues](#reporting-issues)
    - [Gathering Device Information for Troubleshooting](#gathering-device-information-for-troubleshooting)
- [API Documentation](#api-documentation)
- [License](#license)
- [Credits](#credits)
- [Acknowledgments](#acknowledgments)
- [Support](#support)

---

## Prerequisites

:warning: **Quick heads-up for the older Homey gang**: If you're on Homey (Pro) Early 2016–2019 (aka "no Local API club"), this integration won't work.

The good news: you can still bridge Homey ↔ Home Assistant using the universal MQTT approach.

**How-to**: https://community.homey.app/t/tutorial-pro-how-to-integrate-home-assistant-with-homey-pro-and-v-v/92641

---

Before installing the integration, you need to create an API Key in Homey:

1. Open the [Homey Web App](https://homey.app)
2. Go to **Settings** → **API Keys**
3. Click **New API Key**
4. Give it a name (e.g., "Home Assistant")
5. Select the necessary permissions:

   **Required Permissions:**
   - **View devices** (`homey.device.readonly`) - **Required** to read device states and discover devices
   - **Control devices** (`homey.device.control`) - **Required** to control devices (turn on/off, set brightness, etc.)
   - **View System** (`homey.system.readonly`) - **Required** for Socket.IO real-time updates. Without this, the integration will use polling (5-10 second updates) instead of instant updates (< 1 second). See [Real-Time Updates](#real-time-updates) section below.
   
   **Recommended Permissions:**
   - **View Zones** (`homey.zone.readonly`) - **Recommended** for room/area organization. Without this, devices won't be organized by Homey rooms.
   - **View Flows** (`homey.flow.readonly`) - **Recommended** to list Flows (needed for Flow button entities and service calls using flow names)
   - **Start Flows** (`homey.flow.start`) - **Recommended** to trigger, enable, and disable Flows
   - **View Moods** (`homey.mood.readonly`) - **Recommended** to list Moods (needed for Mood entities)
   - **Set Moods** (`homey.mood.set`) - **Recommended** to trigger Moods
   - **View Variables** (`homey.logic.readonly`) - **Recommended** to list Logic variables (needed for Logic entities)
   - **Variables** (`homey.logic`) - **Recommended** to update Logic variables from Home Assistant
   
   **Note on Scenes**: Scenes in Homey API v3 may not have separate permissions. Scene listing and activation likely use `homey.device.readonly` and `homey.device.control` permissions.

6. Copy the API Key (you won't be able to see it again!)

**Permission Impact:**

| Permission | Impact if Missing |
|-----------|-------------------|
| `homey.device.readonly` | ❌ **Integration will not work** - Cannot discover or read devices |
| `homey.device.control` | ⚠️ **Device control disabled** - Cannot turn devices on/off, change settings, etc. |
| `homey.system.readonly` | ⚠️ **Socket.IO disabled** - Real-time updates via Socket.IO won't work, will use polling (5-10 second updates) instead |
| `homey.zone.readonly` | ⚠️ **No room organization** - Devices won't be grouped by Homey rooms/areas |
| `homey.flow.readonly` | ⚠️ **Flow listing disabled** - Flow button entities won't be created |
| `homey.flow.start` | ⚠️ **Flow control disabled** - Cannot trigger, enable, or disable flows |
| `homey.mood.readonly` | ⚠️ **Mood listing disabled** - Mood entities won't be created |
| `homey.mood.set` | ⚠️ **Mood activation disabled** - Cannot activate moods |
| `homey.logic.readonly` | ⚠️ **Logic variables disabled** - Logic entities won't be created |
| `homey.logic` | ⚠️ **Logic updates disabled** - Cannot change Logic variables from Home Assistant |

**Note**: The integration will log warnings in Home Assistant's logs when permissions are missing, but it won't break. Features requiring missing permissions will simply be disabled. However, `homey.system.readonly` is **required** for Socket.IO real-time updates - without it, the integration will use polling (5-10 second updates) instead of instant updates (< 1 second).

**⚠️ Important for Real-Time Updates**: The **System → View System** permission (`homey.system.readonly`) is **required** for Socket.IO real-time updates. You need to **create a new API key** with this permission enabled. Go to Homey Settings → API Keys and create a new API key. Make sure to enable all the same permissions as your current API key, plus the new `homey.system.readonly` permission. After creating the new API key, update your Home Assistant integration configuration with the new key and restart Home Assistant or reload the Homey integration.

**Important**: Keep this API Key safe - you'll need it during the setup process!

## Installation

### Manual Installation

#### Option 1: Direct File System Access

If you have direct access to your Home Assistant file system (e.g., via SSH, Docker volume, etc.):

1. Download or clone this repository:
   ```bash
   git clone https://github.com/ifMike/homeyHASS.git
   ```

2. Copy the `custom_components/homey` folder to your Home Assistant `custom_components` directory:
   ```
   <config directory>/custom_components/homey/
   ```
   
   For example, if your Home Assistant config directory is `/config`, the path would be:
   ```
   /config/custom_components/homey/
   ```

3. Restart Home Assistant

4. Go to **Settings** → **Devices & Services** → **Add Integration**

5. Search for **"Homey"** and follow the setup instructions

---

#### Option 2: Using Samba (Network Drive)

This is a user-friendly way to access your Home Assistant config folder if you don't have direct file system access.

**Step 1 — Enable Samba in Home Assistant**

1. In Home Assistant UI, go to **Settings** → **Add-ons**
2. Click **Add-on Store** (if not already there)
3. Search for **"Samba share"** and install it
4. Open the add-on configuration
5. Set:
   - **Username**: `homeassistant`
   - **Password**: (choose a password and remember it!)
6. Click **Save** and then **Start**
7. Enable **Start on boot** toggle

**Step 2 — Connect from Your Computer**

**On macOS:**
1. Open **Finder**
2. Press `⌘ + K` (or go to **Go** → **Connect to Server**)
3. Enter your Home Assistant IP address:
   ```
   smb://YOUR_HA_IP_ADDRESS
   ```
   > **Note**: Replace `YOUR_HA_IP_ADDRESS` with your actual Home Assistant IP (e.g., `smb://192.168.1.161`)
4. Click **Connect**
5. Log in with:
   - **Username**: `homeassistant`
   - **Password**: (the password you set in Step 1)
6. You'll now see folders like:
   ```
   config/
   └── custom_components/
   ```
7. Navigate to `config/custom_components/` and copy the `homey` folder there

**On Windows:**
1. Open **File Explorer**
2. In the address bar, type:
   ```
   \\YOUR_HA_IP_ADDRESS
   ```
   > **Note**: Replace `YOUR_HA_IP_ADDRESS` with your actual Home Assistant IP (e.g., `\\192.168.1.161`)
3. Press Enter
4. Log in when prompted with:
   - **Username**: `homeassistant`
   - **Password**: (the password you set in Step 1)
5. Navigate to `config/custom_components/` and copy the `homey` folder there

**Step 3 — Restart Home Assistant**

After copying files:
- Go to **Settings** → **System** → **Restart**

**Step 4 — Add the Integration**

1. Go to **Settings** → **Devices & Services** → **Add Integration**
2. Search for **"Homey"** and follow the setup instructions

### Installation via HACS

**HACS (Home Assistant Community Store)** is the easiest way to install and keep this integration updated.

#### Prerequisites

1. **Install HACS** (if you haven't already):
   - Follow the [HACS installation guide](https://hacs.xyz/docs/setup/download)
   - Restart Home Assistant after installing HACS

#### Installation Steps

**Option 1: Custom Repository (Recommended for now)**

1. Open **HACS** in Home Assistant
2. Go to **Integrations**
3. Click the three dots menu (⋮) in the top-right corner
4. Select **Custom repositories**
5. Add the repository:
   - **Repository**: `https://github.com/ifMike/homeyHASS`
   - **Category**: Select **Integration**
6. Click **Add**
7. Close the dialog
8. Search for **"Homey"** in HACS Integrations
9. Click on **Homey Integration**
10. Click **Download**
11. Restart Home Assistant
12. Go to **Settings** → **Devices & Services** → **Add Integration**
13. Search for **"Homey"** and follow the setup instructions
   - You can update the host/IP, API key, and fallback polling later via **Settings → Devices & Services → Homey → Configure**

**Option 2: HACS Default Repository (Future)**

Once this integration is added to the HACS default repository, you can simply:
1. Open **HACS** → **Integrations**
2. Click **Explore & Download Repositories**
3. Search for **"Homey"**
4. Click **Download**
5. Restart Home Assistant
6. Configure the integration
   - You can update the host/IP, API key, and fallback polling later via **Settings → Devices & Services → Homey → Configure**

#### Updating via HACS

When a new version is available:
1. Open **HACS** → **Integrations**
2. Find **Homey Integration**
3. Click **Update** if an update is available
4. Restart Home Assistant

**Note**: HACS will automatically check for updates and notify you when new versions are available.

#### Enabling Automatic Updates for Beta/Dev Releases

To receive automatic updates for beta and dev releases:

1. **Enable "Show Beta" in HACS:**
   - Open **HACS** in Home Assistant
   - Click the three dots menu (⋮) in the top-right corner
   - Select **Settings**
   - Enable **Show beta** (toggle it ON)
   - This allows HACS to check for prerelease versions

2. **Install from the Correct Branch/Tag:**
   - When installing, make sure to select the correct branch/tag:
     - For **Stable**: Don't specify a branch (or select `main`)
     - For **Beta**: Select `beta` branch/tag
     - For **Dev**: Select `dev` branch/tag
   - HACS will track the branch/tag you install from and show updates for that specific branch

3. **Verify Branch Tracking:**
   - After installing, check the integration details in HACS
   - The "Installed version" should match your branch (e.g., `1.1.4-dev.4` for dev)
   - The "Available version" should show updates for your branch, not stable
   - If it shows stable as available when you're on dev/beta, you may need to reinstall from the correct branch

**Important Note on Branch Tracking and Version Selection:**
- Beta and Dev releases use moving tags (`beta` and `dev`) that always point to the latest commit
- **When installing from dev/beta branch:**
  - HACS will track the `dev` or `beta` tag you install from
  - The "Available version" should show the latest dev/beta version, not stable
  - HACS compares your installed version (e.g., `1.1.4-dev.3`) with the latest version on your branch (e.g., `1.1.4-dev.4`)
- **If HACS shows stable as "Available version" when you're on dev/beta:**
  1. Make sure "Show beta" is enabled in HACS Settings
  2. Try clicking "Redownload" and selecting your branch (`dev` or `beta`) again
  3. HACS should then track that branch and show branch-specific updates
  4. You may need to reload HACS data: HACS → Settings → Reload Data

**Note**: The `dev` and `beta` tags are moving tags that always point to the latest commit on their respective branches. HACS should track the branch/tag you install from and show updates for that branch only, not stable releases.

#### Switching Between Release Channels (Stable/Beta/Dev)

This integration offers three release channels:

- **Stable** (main branch): Production-ready releases with semantic versioning (e.g., `v1.1.3`)
- **Beta** (beta branch): Pre-release testing - uses `beta` tag that tracks latest commit
- **Dev** (dev branch): Latest development builds - uses `dev` tag that tracks latest commit

**Note**: Beta and Dev releases use moving tags (`beta` and `dev`) that always point to the latest commit on their respective branches. This makes it easier for HACS to detect updates - you'll always see the latest version for your branch!

**To switch to Beta or Dev:**

1. **Remove current installation:**
   - Go to **HACS** → **Integrations** → **Homey Integration**
   - Click the three dots menu (⋮) → **Remove** or **Uninstall**

2. **Add custom repository with branch:**
   - In HACS, click the three dots menu (⋮) in the top-right corner
   - Select **Custom repositories**
   - Click **Add**
   - Enter:
     - **Repository**: `https://github.com/ifMike/homeyHASS`
     - **Category**: **Integration**
     - **Branch**: Select `beta` for Beta or `dev` for Dev (leave empty for Stable)
   - Click **Add**

3. **Install from selected branch:**
   - Search for **"Homey"** in HACS Integrations
   - Click on **Homey Integration**
   - Click **Download**
   - The version number will show which branch you're on (e.g., `1.1.4-beta.1` or `1.1.4-dev.1`)

4. **Restart Home Assistant**

5. **Enable Automatic Updates (Important!):**
   - After installing from beta or dev branch, enable **"Show beta"** in HACS Settings
   - Go to **HACS** → Three dots menu (⋮) → **Settings** → Enable **Show beta**
   - This ensures HACS will automatically detect and notify you of new beta/dev releases
   - Updates will appear automatically when available - no manual refresh needed!

**Note**: When switching branches, your configuration and devices are preserved. You can switch back to Stable at any time by removing and reinstalling without specifying a branch.

### Migrating from Manual Installation to HACS

If you previously installed this integration manually and want to switch to HACS for easier updates:

1. **Remove the manual installation:**
   - Delete the `custom_components/homey/` folder from your Home Assistant config directory
   - Or use SSH/Samba to remove: `<config directory>/custom_components/homey/`

2. **Restart Home Assistant:**
   - Go to **Settings** → **System** → **Restart**
   - Wait for full restart

3. **Install via HACS:**
   - Follow the HACS installation steps above
   - Your existing configuration will be preserved
   - No need to reconfigure - your devices and settings remain intact

4. **Verify installation:**
   - Check **Settings** → **Devices & Services** → **Homey**
   - All your devices should still be there
   - Integration should show version 1.1.0 or later

**Important**: Do NOT have both manual and HACS installations at the same time. This can cause conflicts and errors. Choose one method and stick with it.

## Updating the Integration

When a new version of the integration is released, follow these steps to update:

### Step 1: Download the Latest Version

1. **If you cloned the repository:**
   ```bash
   cd /path/to/homeyHASS
   git pull origin main
   ```

2. **If you downloaded manually:**
   - Go to the [GitHub repository](https://github.com/ifMike/homeyHASS)
   - Click **Code** → **Download ZIP**
   - Extract the ZIP file

### Step 2: Replace the Integration Files

**Option A: Direct File System Access (SSH/Docker)**

1. Stop Home Assistant (recommended but not required)
2. Replace the `custom_components/homey` folder:
   ```bash
   # Backup current version (optional but recommended)
   cp -r <config>/custom_components/homey <config>/custom_components/homey.backup
   
   # Copy new version
   cp -r /path/to/homeyHASS/custom_components/homey <config>/custom_components/
   ```

**Option B: Using Samba (Network Drive)**

1. Connect to your Home Assistant via Samba (see [Installation - Option 2](#option-2-using-samba-network-drive) above)
2. Navigate to `config/custom_components/`
3. Delete the old `homey` folder (or rename it to `homey.backup` for backup)
4. Copy the new `homey` folder from the downloaded repository

### Step 3: Restart Home Assistant

1. Go to **Settings** → **System** → **Restart**
2. Wait for Home Assistant to fully restart

### Step 4: Reload the Integration (Recommended)

After restarting, reload the integration to ensure all changes are applied:

1. Go to **Settings** → **Devices & Services**
2. Find **Homey** integration
3. Click the **⋮** (three dots) menu
4. Select **Reload**

### Step 5: Verify the Update

1. Check the logs for any errors:
   - **Settings** → **System** → **Logs**
   - Look for entries starting with `custom_components.homey`
2. Test functionality:
   - Try controlling a device
   - Check if flow buttons appear (if you have flows)
   - Verify devices are updating correctly

### Troubleshooting Updates

**If devices stop working after update:**

1. **Reload the integration** (see Step 4 above)
2. **Check API permissions** - Some updates may require additional API key permissions
3. **Check the CHANGELOG** - Review what changed in the new version
4. **Restore backup** (if you created one):
   ```bash
   rm -r <config>/custom_components/homey
   mv <config>/custom_components/homey.backup <config>/custom_components/homey
   ```
5. **Check GitHub Issues** - See if others are experiencing the same issue

**If flows stop working:**

- Ensure your API key has **View Flows** and **Start Flows** permissions
- Reload the integration
- Check that flows are enabled in Homey

---

## Configuration

### Setup Steps

1. In Home Assistant, go to **Settings** → **Devices & Services**
2. Click **Add Integration**
3. Search for **Homey**
4. Enter the following information:
   - **Host**: Your Homey's IP address or hostname
     - Examples: `homey.local` or `192.168.1.100` (without `http://` prefix)
     - The integration will automatically add the `http://` prefix if needed
   - **Token**: The API Key you created in Homey
5. Click **Submit**

The integration will automatically discover all your Homey devices and create entities in Home Assistant.

### Homey Self Hosted Server Configuration

If you're using **Homey Self Hosted Server (SHS)**, you need to specify the port number in the host address:

**Host Format**: `IP_ADDRESS:PORT`

**Example**: `192.168.1.100:4859`

**Important Notes:**
- **Default HTTP Port**: Homey Self Hosted Server uses port **4859** for HTTP connections
- **Port Configuration**: The port can be configured via the `PORT_SERVER_HTTP` environment variable in your Docker setup
- **Network Access**: Homey SHS runs in Docker with `network_mode: host` for direct LAN access
- **Other Ports**: Additional ports include 4860 (HTTPS), 4861 and 4862 (Bridge servers), but the integration uses the HTTP port (4859) by default
- **SSL Support**: If you're using HTTPS with a self-signed certificate, use `https://IP_ADDRESS:4860` format and the integration will automatically handle SSL certificate verification *(Note: SSL support for self-signed certificates is currently only available in BETA version)*

**Example Configuration:**
- **Host**: `192.168.1.100:4859` (for HTTP)
- **Host**: `https://192.168.1.100:4860` (for HTTPS with self-signed certificate - BETA only)
- **Token**: Your API Key from Homey

**Troubleshooting:**
- If you're having connection issues, verify the port number matches your Docker configuration
- Check that your Home Assistant instance can reach the Homey SHS server on the specified port
- For DNS resolution issues with `.local` hostnames, use the IP address directly instead

---

## Usage

### Devices

Once configured, all your Homey devices will appear in Home Assistant under **Settings** → **Devices & Services** → **Homey**. Each device will show all its supported entities grouped together.

**Example**: A Philips Hue lightstrip with power measurement will show as:
- 1 device: "Hue lightstrip plus 1"
  - 1 light entity (for dimming and color control)
  - 1 sensor entity (for power consumption)

### Homey Flows (Automations)

**Prerequisites**: Flow support requires **View Flows** (`homey.flow.readonly`) and **Start Flows** (`homey.flow.start`) permissions in your API key. Without these permissions, Flow button entities will not be created and flow services will not work.

**Supported Flow Types**: The integration supports both **Standard Flows** and **Advanced Flows** from Homey. Both types will appear as button entities and can be triggered via service calls.

The integration exposes your Homey Flows in three ways:

#### 1. Button Entities

Each enabled Homey Flow (both Standard and Advanced) appears as a button entity in Home Assistant. Simply press the button to trigger the Flow.

**Entity ID format**: `button.<flow_name>`

**Note**: Flows are automatically discovered from both Standard and Advanced Flow endpoints. Disabled flows will not appear as button entities.

#### 2. Service Calls

You can trigger, enable, and disable Flows from automations, scripts, or the Developer Tools:

**Trigger Flow Service**: `homey.trigger_flow`

**Service Data**:
```yaml
# Trigger by Flow ID
flow_id: "1234567890abcdef"

# OR trigger by Flow name
flow_name: "Turn on all lights"
```

**Enable Flow Service**: `homey.enable_flow`

**Service Data**:
```yaml
# Enable by Flow ID
flow_id: "1234567890abcdef"

# OR enable by Flow name
flow_name: "My Flow"
```

**Disable Flow Service**: `homey.disable_flow`

**Service Data**:
```yaml
# Disable by Flow ID
flow_id: "1234567890abcdef"

# OR disable by Flow name
flow_name: "My Flow"
```

**Example Automation**:
```yaml
automation:
  - alias: "Trigger Homey Flow at Sunset"
    trigger:
      - platform: sun
        event: sunset
    action:
      - service: homey.trigger_flow
        data:
          flow_name: "Evening Scene"
```

### Homey Logic Variables

Homey Logic variables are imported as native Home Assistant entities:

- **Number** variables → `number` entities
- **Boolean** variables → `switch` entities
- **String** variables → `text` entities

**Prerequisites**:
- **View Variables** (`homey.logic.readonly`) to list variables
- **Variables** (`homey.logic`) to change values from Home Assistant

**Note**: Logic variables are not devices in Homey, so they appear under a dedicated **"Homey Logic"** device in Home Assistant.

### Homey Scenes and Moods

**Prerequisites**: 
- **Scenes**: Use `homey.device.readonly` and `homey.device.control` permissions (scenes don't have separate permissions in Homey API v3)
- **Moods**: Require **View Moods** (`homey.mood.readonly`) and **Set Moods** (`homey.mood.set`) permissions

**Scene Platform**: All your Homey scenes appear as Scene entities in Home Assistant. Simply activate them like any other scene.

**Mood Support**: Homey moods are also exposed as Scene entities, but with a distinct icon (😊) to differentiate them from regular scenes.

**Entity ID format**: 
- Scenes: `scene.<scene_name>`
- Moods: `scene.<mood_name>` (with mood icon)

**Note**: If you don't have any scenes or moods configured in Homey, no entities will be created. This is normal and won't cause any errors.

### Physical Device Buttons

Physical device buttons (like Hue dimmer switches, IKEA remotes, etc.) are automatically detected and exposed as Button entities.

**Entity ID format**: `button.<device_name>_button` or `button.<device_name>_button_<number>` for multi-button devices

**Note**: Internal Homey migration capabilities are automatically filtered out and won't appear as buttons.

---

## Device Organization

Devices are automatically organized by:

- **Room/Area**: Devices are assigned to their Homey rooms, which become Areas in Home Assistant
- **Device Type**: Automatically detected based on capabilities (light, switch, sensor, etc.)
- **Grouping**: All entities from the same device are grouped under one device entry

**Note**: A single physical device may have multiple entities (e.g., a light with power measurement will show as 1 device with 2 entities: a light entity and a power sensor entity). This is normal and expected behavior.

---

## Automatic Synchronization

The integration automatically synchronizes changes made in Homey with Home Assistant:

### Device Name Changes
- When you rename a device in Homey, the device name in Home Assistant updates automatically
- Updates occur within ~30 seconds (the polling interval)

### Room/Area Changes
- When you move a device to a different room in Homey, the device's area in Home Assistant updates automatically
- New areas are automatically created in Home Assistant if they don't exist
- Room names are refreshed periodically (~5 minutes) to pick up room name changes
- **Note**: Room organization requires **View Zones** permission in your API key. Without this permission, devices will still work but won't be organized by rooms.

### Device Deletion
- When you delete a device in Homey, it and all its entities are automatically removed from Home Assistant
- Cleanup occurs within ~30 seconds after deletion

### Update Frequency

**Real-Time Updates (Socket.IO)** - *Recommended*
- **Instant Synchronization**: Device state changes in Homey (via app, physical switches, or automations) appear in Home Assistant instantly (< 1 second latency)
- **Bidirectional**: Commands sent from Home Assistant to Homey also get instant feedback
- **Requires**: `homey.system.readonly` permission on your API key (see [Prerequisites](#prerequisites))
- **Fallback**: If Socket.IO connection fails, automatically falls back to polling (5-10 seconds)
- **Polling Interval**: When Socket.IO is active, polling reduces to 60 seconds (safety net). When inactive, polling uses 5-10 seconds.

**Polling Mode** - *Fallback*
- **Immediate Updates**: When you control a device (turn on/off, change brightness, color, etc.), the status updates immediately (1-2 seconds) by fetching the device state right after the change
- **Background Polling**: Device states are polled every 5-10 seconds to catch changes made outside Home Assistant (e.g., via Homey app or physical switches)
- Device names/rooms: Checked during polling cycles
- Zones (rooms): Refreshed every ~5 minutes

**Note**: Entity names (`_attr_name`) are set during initialization and won't update automatically. The device name in the UI will update, but individual entity names may show the old name until you reload the integration. This is a Home Assistant limitation and is acceptable for most use cases.

---

## Real-Time Updates

The integration supports real-time device state updates via Socket.IO, providing instant synchronization between Homey and Home Assistant.

### How It Works

**Socket.IO Real-Time Updates** (Recommended)
- Device state changes in Homey (via app, physical switches, or automations) appear in Home Assistant instantly (< 1 second latency)
- Commands sent from Home Assistant to Homey also get instant feedback
- Uses a single WebSocket connection for efficient communication
- Automatically reconnects if the connection is lost
- When active, polling reduces to 60 seconds (safety net)

**Polling Fallback** (Automatic)
- If Socket.IO connection fails or the required permission is missing, the integration automatically falls back to polling
- Polling interval: 5-10 seconds when Socket.IO is inactive
- The integration continues to work normally, just without instant updates

### Requirements

To enable Socket.IO real-time updates:

1. **Create a New API Key**:
   - Go to **Homey Settings → API Keys**
   - **Create a new API key** with the **System → View System** permission (`homey.system.readonly`) enabled
   - Make sure to enable all the same permissions as your current API key, plus the new `homey.system.readonly` permission

2. **Update Integration Configuration**:
   - After creating the new API key, update your Home Assistant integration configuration with the new key
   - Go to **Settings** → **Devices & Services** → **Homey** → **Configure**
   - Enter the new API key
   - Restart Home Assistant or reload the Homey integration

3. **Verify Connection**:
   - Check Home Assistant logs for "Socket.IO real-time updates enabled" message
   - This confirms Socket.IO is active and working

### Benefits

- **Instant Updates**: Device changes appear immediately (< 1 second) instead of waiting for polling cycles
- **Bidirectional**: Both Homey → Home Assistant and Home Assistant → Homey updates are instant
- **Efficient**: Reduces API calls by using WebSocket instead of frequent HTTP polling
- **Reliable**: Automatic fallback to polling ensures updates are never missed

### Troubleshooting Real-Time Updates

If Socket.IO is not working, see the [Real-time Updates Not Working](#real-time-updates-not-working) section in Troubleshooting.

---

## Supported Devices

The integration supports a wide range of Homey devices and capabilities. For detailed information about all supported device types and capabilities, see [SUPPORTED_DEVICES.md](SUPPORTED_DEVICES.md).

### Overview

The integration automatically detects and creates entities for:

- **Lights** - Full dimming, color (HS), and color temperature control
- **Switches** - On/off control, including multi-channel devices
- **Sensors** - Temperature, humidity, power, energy, and many more (including Energy Dashboard compatible sensors)
- **Binary Sensors** - Motion, contact, alarms, and all boolean capabilities
- **Covers** - Window coverings and garage doors with position control
- **Climate** - Thermostats with custom mode support
- **Fans** - Fan speed control
- **Locks** - Lock state and control
- **Media Players** - Full media control with metadata support
- **Scenes & Moods** - Activate Homey scenes and moods
- **Buttons** - Physical device buttons and Homey Flow triggers
- **Select Entities** - Mode and option selection (automatically detected for enum capabilities)
- **Number Entities** - Numeric settings (e.g., temperature targets)
- **Vacuum Cleaners** - Full vacuum control with cleaning modes and status
- **Battery Devices** - Battery storage systems with energy tracking
- **Lawn Mowers** - Gardena lawn mower support
- **Heat Pumps** - Comprehensive heat pump control with multiple temperature zones
- **Solar Panels** - Solar panel/inverter monitoring

**Generic Capability Support**: The integration automatically creates entities for ANY `measure_*`, `meter_*`, boolean, or enum capability, ensuring support for new device types without code changes.

For complete details on all supported capabilities, device classes, and entity types, please see the [Supported Devices documentation](SUPPORTED_DEVICES.md).

---

## Known Issues & Limitations

### Room/Zone Detection
- **Issue**: Rooms may not be detected if your API key doesn't have **View Zones** permission.
- **Impact**: Devices will still be imported and work correctly, but won't be organized by rooms in the device selection dialog or assigned to areas automatically.
- **Solution**: Create a new API key in Homey Settings → API Keys with the **View Zones** permission enabled.

### Config Flow Window Size
- **Issue**: The device selection dialog has a fixed size and cannot be resized or customized.
- **Impact**: With many devices, you'll need to scroll through the list. The dialog size is controlled by Home Assistant and cannot be modified by integrations.
- **Solution**: Use your browser's search function (Ctrl+F / Cmd+F) to quickly find devices. This is a Home Assistant framework limitation and cannot be customized by individual integrations.

### Entity Name Updates
- **Issue**: Entity names don't update automatically when device names change in Homey.
- **Impact**: Device names in the UI will update, but individual entity names may show old names until you reload the integration.
- **Solution**: Reload the integration after renaming devices in Homey if you want entity names to update immediately.

---

## Troubleshooting

### Connection Issues

If you're having trouble connecting to Homey:

1. **Check the Host Address**: 
   - Make sure you're using the correct IP address or hostname
   - Examples: `192.168.1.100` or `homey.local` (no `http://` prefix needed)
   - The integration will automatically add the `http://` prefix if needed

2. **Check API Key**: 
   - Verify that your API Key is correct and has the necessary permissions
   - Make sure you copied the entire key (they can be quite long)

3. **Network Access**: 
   - Ensure that your Home Assistant instance can reach your Homey hub on the network
   - Check if there are any firewalls blocking the connection
   - Try pinging your Homey from the Home Assistant host

4. **Check Logs**: 
   - Go to **Settings** → **System** → **Logs**
   - Look for entries starting with `homey` or `custom_components.homey`
   - Enable debug logging if needed:
     ```yaml
     logger:
       default: info
       logs:
         custom_components.homey: debug
     ```

### Devices Not Appearing

If devices aren't appearing in Home Assistant:

1. **Check Device Capabilities**: 
   - Make sure your devices have supported capabilities (see Supported Devices above)
   - Some devices may not expose their capabilities via the API

2. **Restart Integration**: 
   - Try removing and re-adding the integration
   - Or reload the integration: **Settings** → **Devices & Services** → **Homey** → **⋮** → **Reload**

3. **Check Logs**: 
   - Check the logs for any errors related to device discovery
   - Look for messages about unsupported capabilities

4. **Device Classification Issues**:
   - If a device appears as the wrong type (e.g., switch showing as sensor, or light without dimming), see [Gathering Device Information](#gathering-device-information-for-troubleshooting) below
   - This helps us understand what capabilities Homey exposes for your device

### Duplicate Devices

If you see duplicate devices:

1. **Reload Integration**: 
   - Go to **Settings** → **Devices & Services** → **Homey** → **⋮** → **Reload**
   - This will refresh the device registry

2. **Restart Home Assistant**: 
   - Sometimes a full restart is needed to refresh the device registry
   - This is especially true after updating the integration

3. **Check Device Info**: 
   - All entities from the same device should be grouped under one device entry
   - If you see separate devices with the same name, it may be a device registry caching issue

### Real-time Updates Not Working

If device states aren't updating in real-time:

1. **Check API Key Permissions**:
   - Go to **Homey Settings → API Keys** and create a new API key
   - Ensure **System → View System** (`homey.system.readonly`) permission is enabled
   - Make sure to enable all the same permissions as your current API key, plus the new `homey.system.readonly` permission
   - After creating the new API key, update your Home Assistant integration configuration with the new key
   - Restart Home Assistant or reload the Homey integration

2. **Check Socket.IO Connection Status**:
   - Go to **Settings** → **System** → **Logs**
   - Look for "Socket.IO real-time updates enabled" message (indicates Socket.IO is working)
   - If you see "Socket.IO status: DISCONNECTED", Socket.IO is not active and polling is being used

3. **Verify Network Connectivity**:
   - Ensure Home Assistant can reach your Homey hub on the network
   - Check for firewalls blocking WebSocket connections (Socket.IO uses WebSockets)

4. **Check Logs for Errors**:
   - Enable debug logging if needed:
     ```yaml
     logger:
       default: info
       logs:
         custom_components.homey: debug
     ```
   - Look for Socket.IO connection errors or permission-related warnings

5. **Fallback Behavior**:
   - If Socket.IO fails, the integration automatically uses polling (5-10 seconds)
   - The integration will continue to work, just without instant updates
   - Socket.IO will automatically reconnect if the connection is lost

### Device Changes Not Syncing

If device name or room changes made in Homey aren't appearing in Home Assistant:

1. **Wait for Polling**: Changes are detected during the next polling cycle (up to 30 seconds)
2. **Check Logs**: Look for messages about device registry updates in the logs
3. **Manual Refresh**: Reload the integration: **Settings** → **Devices & Services** → **Homey** → **⋮** → **Reload**
4. **Verify Changes**: Make sure the changes were actually saved in Homey

---

## Development

### Project Structure

```
custom_components/homey/
├── __init__.py          # Integration setup and service registration
├── manifest.json        # Integration metadata
├── config_flow.py       # Configuration flow UI
├── const.py            # Constants and capability mappings
├── coordinator.py      # Data update coordinator with device registry sync
├── homey_api.py        # Homey API client
├── device_info.py      # Device info helper functions
├── permissions.py      # Permission checking utilities
├── strings.json        # User-facing strings
├── services.yaml       # Service definitions
├── switch.py           # Switch platform
├── light.py            # Light platform
├── sensor.py           # Sensor platform
├── binary_sensor.py    # Binary sensor platform
├── cover.py            # Cover platform
├── climate.py          # Climate platform
├── fan.py              # Fan platform
├── lock.py             # Lock platform
├── media_player.py     # Media player platform
├── button.py           # Button platform (for Flows and device buttons)
├── scene.py            # Scene platform
├── select.py           # Select entity platform
├── number.py           # Number entity platform
└── vacuum.py           # Vacuum cleaner platform
```

### Key Technical Features

- **Device Registry Synchronization**: The coordinator automatically updates the Home Assistant device registry when devices are renamed, moved to different rooms, or deleted in Homey
- **Consistent Device Info**: All entities from the same device use identical device identifiers to ensure proper grouping
- **Smart Entity Creation**: Prevents duplicate entities (e.g., devices with light capabilities won't also create switch entities)
- **Zone Refresh**: Periodically refreshes room/zone information to keep areas up-to-date
- **Robust API Handling**: Supports multiple Homey API endpoint structures and automatically discovers the correct one

### Contributing

Contributions are welcome! Please feel free to:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

### Reporting Issues

If you encounter any issues, please:

1. Check the [existing issues](https://github.com/ifMike/homeyHASS/issues) first
2. Create a new issue with:
   - A clear description of the problem
   - Steps to reproduce
   - Home Assistant version
   - Homey firmware version
   - Relevant log entries

#### Gathering Device Information for Troubleshooting

**When to use this guide:** If you're experiencing issues with device classification (wrong entity type), missing capabilities (e.g., light without dimming), or devices not appearing correctly, gathering device information helps diagnose the issue.

If you're experiencing issues with a specific device (e.g., device not appearing, wrong entity type, missing capabilities), we need to see the device's capabilities and class information from Homey to diagnose the issue.

**Step-by-Step Guide:**

1. **Open Homey Developer Tools**:
   - Go to https://tools.developer.homey.app
   - Select your Homey hub
   - Click **"Devices"** in the left menu

2. **Find Your Device**:
   - Browse or search for the device you're having trouble with
   - Click on the device to open its details
   - **Copy the device ID** (it's a UUID like `0cb8501e-e786-4d24-9bec-00b57a15d7f7`)

3. **Get Device Information**:
   - Go to **"Web API Playground"** in the left menu
   - Paste the following code, replacing `YOUR_DEVICE_ID` with the device ID you copied:
   
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

4. **Copy the Output**:
   - Click **"Run"** or press Enter
   - The output will appear in the console below
   - **Copy the entire JSON output** (it contains all the device information we need)

5. **Include in Your Issue**:
   - Paste the device information JSON in your GitHub issue
   - This helps us understand:
     - What device class Homey assigns to the device
     - What capabilities are exposed
     - Whether capabilities are properly configured
     - If there are any missing or incorrectly exposed capabilities

**Example Output:**
```json
{
  "class": "thermostat",
  "capabilities": [
    "measure_temperature",
    "measure_temperature.external",
    "measure_temperature.floor",
    "thermofloor_onoff",
    "measure_power",
    "measure_voltage",
    "meter_power",
    "thermofloor_mode",
    "target_temperature",
    "button.reset_meter"
  ],
  "capabilitiesObj": {
    "measure_temperature": {
      "id": "measure_temperature",
      "type": "number",
      "title": "temperature",
      "getable": true,
      "setable": false,
      "units": "C",
      "decimals": 1,
      "value": 16.5,
      "lastUpdated": "2026-01-10T10:55:00.000Z"
    },
    "target_temperature": {
      "id": "target_temperature",
      "type": "number",
      "title": "target temperature",
      "getable": true,
      "setable": true,
      "min": 5,
      "max": 35,
      "units": "C",
      "decimals": 1,
      "value": 20.0
    },
    "button.reset_meter": {
      "id": "button.reset_meter",
      "type": "boolean",
      "title": "Reset power meter",
      "getable": false,
      "setable": true,
      "maintenanceAction": true
    }
  }
}
```

**Note:** The actual output will include all capabilities your device exposes. The `capabilitiesObj` contains detailed information for each capability including current values, min/max ranges, units, and whether capabilities are getable/setable.

**What This Information Tells Us:**
- **`class`**: The device type Homey assigns (e.g., "light", "socket", "sensor", "windowcoverings")
- **`capabilities`**: List of capability IDs the device exposes
- **`capabilitiesObj`**: Detailed capability information including min/max values, getable/setable flags, and current values
- **`driverId`**: The driver/app that manages this device (helps with device-specific detection)

**Common Issues This Helps Diagnose:**
- Device classified as wrong type (e.g., switch showing as sensor)
- Missing capabilities (e.g., light without dimming support)
- Capabilities not properly exposed by Homey app
- Device-specific detection issues

**Privacy Note:** The device information contains your device names and current states. If you're concerned about privacy, you can redact the `name` field and `value` fields in `capabilitiesObj` before sharing.

---

## API Documentation

For more information about the Homey API:

- [Homey API Documentation](https://api.developer.homey.app/)
- [Homey API Keys Guide](https://support.homey.app/hc/en-us/articles/8178797067292-Getting-started-with-API-Keys)
- [Homey Local API](https://apps.developer.homey.app/the-basics/local-api)

---

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## Credits

- **Author**: Mikael Collin ([@ifmike](https://github.com/ifMike))
- **Built for**: Home Assistant
- **Uses**: Homey Local API by Athom

## Acknowledgments

- Built for the Home Assistant community
- Uses the Homey Local API by Athom
- Inspired by the need to bridge Homey and Home Assistant ecosystems
- Special thanks to [@PeterKawa](https://github.com/PeterKawa) for initial testing, bug reports, and feedback that helped identify and fix many issues
- Created by one guy with too much time on his hands who couldn't sit on his ass waiting for someone else to build this 😄

---

## Support

For support, please:

1. Check the [Troubleshooting](#troubleshooting) section above
2. Search [existing issues](https://github.com/ifMike/homeyHASS/issues)
3. Create a new issue if needed

---

**Note**: This is a community-driven project and is not officially affiliated with Athom or Home Assistant. It's a work in progress made by just one guy with too much time on his hands who couldn't sit on his ass waiting for someone else to create this plugin. If you find bugs, report them. If you want features, ask nicely. If you want to help, pull requests are welcome! 🚀

---

## Support the Project

If you find this integration useful and want to support further development, you're welcome to buy me a coffee! ☕

[![Buy Me A Coffee](https://img.shields.io/badge/Buy%20Me%20A%20Coffee-%23FFDD00?style=for-the-badge&logo=buy-me-a-coffee&logoColor=black)](https://buymeacoffee.com/ifmike)

No pressure at all - this is completely optional! Your support helps keep projects like this going and motivates me to add more features and fixes. 🙏
