# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [2.0.0] - 2026-06-19

### BREAKING CHANGES

**Read this before updating. This is a major release with no automatic upgrade path.**

The integration domain was renamed from `homey` to `homey_hass` to resolve a conflict with the existing HACS default integration [RonnyWinkler/homeassistant.homey](https://github.com/RonnyWinkler/homeassistant.homey). This rename is **required** before this integration can be included in the official HACS default repository.

**If you are on version 1.x and your installation is working: do not update to 2.0.0 unless you are ready to migrate manually.** Stay on 1.2.6 until you have planned time for the steps below.

#### What changes

| Before (1.x) | After (2.0.0) |
|--------------|---------------|
| Domain `homey` | Domain `homey_hass` |
| Folder `custom_components/homey/` | Folder `custom_components/homey_hass/` |
| Services `homey.*` | Services `homey_hass.*` |
| Display name **Homey** | Display name **Homey** (unchanged) |

#### What breaks if you update without migrating

- Existing config entries under domain `homey` stop loading.
- All entities become unavailable until you set up the integration again.
- Automations and scripts using `homey.*` services fail (must use `homey_hass.*`).
- Dashboards may show unavailable entities; entity history may not carry over if entity IDs change.

#### Migration steps (1.x → 2.0.0)

1. **Create a Home Assistant backup.**
2. Note your Homey **host/IP** and **API key**.
3. **Settings → Devices & services → Homey** → delete the old config entry.
4. Update to 2.0.0 via HACS (or install manually).
5. Delete `custom_components/homey/` if it still exists.
6. Ensure `custom_components/homey_hass/` is present.
7. Restart Home Assistant.
8. Add the **Homey** integration again and complete setup.
9. Update automations/scripts: `homey.*` → `homey_hass.*`.
10. Fix dashboards and remove orphaned unavailable entities if needed.

#### New installations

Install `custom_components/homey_hass/` and add the **Homey** integration normally. No migration needed.

### Fixed
- **Dyson fan capabilities**: `oscillate` is exposed on the fan entity; `less_air` and `more_air` are exposed as button entities. Stops false "new capability" alerts for these Dyson Air Multiplier controls.

## [1.2.6] - 2026-05-17

### Added
- **Device temperature unit override**: Per-device Celsius/Fahrenheit when Homey metadata is wrong or missing (integration **Configure → Device temperature units**, or `homey.set_device_temperature_unit` service).
- **Temperature unit handling**: Climate and temperature sensors use Homey `units` metadata; values are shown in the unit for your Home Assistant region (**Settings → System → Home information**; region sets Metric = °C or US Customary = °F).

### Fixed
- **Capability alerts**: New-capability notifications only for capabilities the integration does not already support (e.g. no alert for known `measure_current`).
- **Thermostat temperatures**: Fixes incorrect display when drivers send Fahrenheit values but metadata says Celsius (e.g. 69°F shown as 156°F).

## [1.2.5] - 2026-05-07

### Fixed
- **Energy dashboard source eligibility for gas/water sensors**: `meter_gas`, `meter_water`, and legacy `sgas*`/`swater*` capabilities now expose gas/water `device_class` when supported by Home Assistant so they appear correctly in the Energy Dashboard source picker.
- **Legacy Homey Energy Dongle compatibility**: Added backward compatibility for legacy cumulative gas/water capabilities (`sgas*` / `swater*`) with proper `TOTAL_INCREASING` state class and `m³` units.
- **Legacy gas/water labeling clarity**: Improved naming for legacy gas/water entities to make them easier to identify in Home Assistant.

## [1.2.4] - 2026-04-28

### Fixed
- **Homey Energy Dongle legacy gas/water compatibility**: Added backward compatibility for legacy `sgas*` / `swater*` capability names by treating them as cumulative gas/water meters with `TOTAL_INCREASING` state class and `m³` units. Improved naming of these legacy entities for clearer labels.

## [1.2.3] - 2026-04-02

### Added
- **Light scene capability support**: Added support for `lightScenes.light` (and `lightScenes`) on lights. Devices exposing this capability are now classified as lights and can use Home Assistant light `effect` / `effect_list` for scene selection.
- **Capability mapping**: Added `lightScenes` and `lightScenes.light` to platform capability mapping to improve automatic classification and capability reporting context.

### Fixed
- **Light vs switch classification**: Devices with `onoff` + `lightScenes.*` are now treated as lights instead of switches.
- **Numeric capability parsing (Philips Hue)**: Fixed crash when Homey returns `"auto"` for numeric capability values (seen with Philips Hue capability payloads).
- **Moisture sensors**: Improved moisture capability handling so moisture-related capabilities map to the proper moisture device class.

## [1.2.2] - 2026-03-18

### Added
- **Discovery logging**: Logs all discovery info (DHCP/Zeroconf) for debugging. Search logs for `[discovery]` to find entries. Helps identify model and troubleshoot discovery issues.
- **Model filtering**: Homey 2019 and older no longer appear in Zeroconf discovery. Filter by mDNS `model` property: missing model or known unsupported IDs (homey3d, homey4d, homey2s, etc.) are suppressed. Supported: homey5q (Pro 2023), homey6q (Pro mini), homey7q (Pro 2026), SHS. Unknown models are still shown for future compatibility.

### Fixed
- **Discovery suppression**: Improved matching to avoid "new" Homey when already configured. Now compares by host+port (for SHS same-IP different ports), MAC address (when available from DHCP or Zeroconf properties), and resolved IP. Fixes duplicate discovery cards for users with multiple interfaces or same subnet.
- **Multi-hub migration**: Migration notifications only appear once, not on every restart. Added check for persisted `multi_homey_enabled` in config entries.
- **HACS**: Removed deprecated `beta` key from `hacs.json` (fixes CI validation).

### Changed
- **Discovery logging**: Zeroconf and DHCP discovery now log API reachability and full discovery properties for easier troubleshooting.

---

## [1.2.1] - 2026-01-27

### Added
- **Discovery card identification**: Shows IPv4 on discovered cards (e.g. "Homey (192.168.1.32)") so multiple Homeys can be distinguished. Falls back to "Homey (IP unknown)" when IPv4 cannot be resolved.
- **Setup step descriptions**: Step descriptions explain what to do, required permissions (Devices, Flows, System read), and Pro 2023+ limitation.
- **Translations**: Added translations/en.json for config flow to display step descriptions correctly.

### Changed
- **Discovery host field**: Never show .local hostname or IPv6 in the host field. Resolve to IPv4 when possible; use empty when resolution fails. Default manual host changed from homey.local to empty.
- **Error messages**: Full error messages for invalid_auth and cannot_connect with causes and solutions, including Pro 2019 not supported. Passed directly since translation keys may not resolve in custom components.

### Fixed
- **Sensor unavailability**: Removed registry filter that skipped existing sensors, causing them to become orphaned and show Unavailable (controls worked, sensors did not).
- **Discovery suppression**: Suppress discovery when an existing config entry points to the same host. Fixes "Discovered" Homey showing when manually configured (manual uses homeyId, discovery uses MAC/hostname).
- **IPv6 discovery suppression**: When discovered host is IPv6, resolve hostname to IPv4 and compare with existing entries so discovery is correctly suppressed for already-configured hosts.
- **Discovery card fallback**: When title_placeholders was empty, the card showed "homey" (domain). Now always shows "Homey (IP)" or "Homey (IP unknown)".

---

## [1.2.0] - 2026-03-03

### Added
- **Virtual button support**: Homey Virtual Button devices (`button` capability) now create button entities. Added to CAPABILITY_TO_PLATFORM, boolean conversion in API, and device class mapping.
- **Zeroconf (mDNS) discovery**: Homey broadcasts `_homey._tcp` via mDNS. Discovery works regardless of MAC address or router DHCP reporting. Helps when DHCP discovery fails (e.g. different MAC prefix, Docker networking).
- **DHCP discovery**: Automatic discovery via MAC address prefix (9013DA) for supported routers. DHCP updates the configured host when the router reassigns a new IP to the same MAC (e.g. after router change). Based on PR #18 by @rrooggiieerr.
- **measure_distance capability**: Map `measure_distance` to sensor with DISTANCE device class and cm unit for ultrasonic/ToF presence sensors.

### Changed
- **Discovery form**: Confirmation form includes editable host so you can correct the detected address (e.g. when Homey has multiple interfaces). Default host for manual setup is now `homey.local` instead of a fixed IP. Added strings for discovery confirmation step.
- **Logging**: Reduced per-entity and discovery logs from INFO/WARNING to DEBUG for light, switch, Zeroconf, logic variables success, and Socket.IO reconnection attempts. Light devices with ONOFF-only (no dim/hue/temp) now log at DEBUG. Connection failure messages (polling, set_capability, get_device, trigger_flow) now include host and exception for easier debugging. Warns when host contains `.local` and suggests using a static IP for stability.
- **Zeroconf discovery**: Prefer IP addresses from mDNS instead of `.local` hostname when both are available; only use hostname when no IP is discovered. When no address is reachable (e.g. HA in Docker), prefer IPv4 over IPv6; use hostname instead of IPv6 when no IPv4 is available (IPv6 often fails on local networks).

### Fixed
- **Discovery host overwrite**: Zeroconf and DHCP discovery no longer overwrite a user's manually configured host when discovery finds the same hub. Zeroconf keeps the user's host unchanged; DHCP still updates when the router reassigns a new IP to support dynamic addressing.
- **Log spam when Homey unreachable**: Rate limit connection/polling error logs to at most every 5 minutes when Homey is down. Prevents thousands of repeated "No devices returned", "Polling failed", and "Socket.IO connection error" messages overnight. Subsequent occurrences logged at DEBUG.
- **Duplicate hub detection**: Abort setup (instead of warning) when another config entry targets the same Homey hub or host, with a clear notification to remove the duplicate.
- **Sensor duplicate unique IDs**: Sensors were created twice for `measure_*` and `meter_*` capabilities (handled in both generic loops). Now skipped in the third loop, with deduplication by unique_id before add.
- **Manifest**: MAC address must be uppercase (9013DA) and keys sorted for hassfest validation.
- **Logic variables**: Handle nested API responses (`{"result": {...}}`, `{"variables": [...]}`) when fetching variables. Try both `{"value": value}` and `{"variable": {"value": value}}` payload formats when updating, so toggles and edits work regardless of Homey API structure.
- **Zeroconf discovery host field**: When mDNS provides no IP addresses (only hostname like `Homey-9013DA123456.local`), resolve the hostname to an IP so the form shows a connectable address instead of hostname/MAC.

## [1.1.9] - 2026-02-18

### Added
- **Opt-in capability title naming**: Homey apps can provide human-readable `title` fields for capabilities (e.g., "Temperature", "Target Temperature"). By default, entity names use the capability ID (e.g., "Living Room measure_temperature"). Enable this option in integration settings to use the app-provided titles instead (e.g., "Living Room Temperature") for cleaner names in the UI.
- **Rename entities service**: `homey.rename_entities_to_titles` service to bulk-update existing entity display names to capability titles without changing entity_ids. Use this after enabling title naming to update entities that were created before the option was turned on.
- **Media player shuffle/repeat**: Full support for `speaker_shuffle` and `speaker_repeat` capabilities (SHUFFLE_SET, REPEAT_SET features)
- **Binary sensor alarm types**: Added device classes for `alarm_vibration`, `alarm_occupancy`, and `alarm_presence`
- **Device class mappings**: Added `heater`, `switch`, and `vacuumcleaner` to central device class mapping for correct type detection

### Changed
- **Device info**: Expanded Homey device class mapping for more reliable classification

### Fixed
- **Capability reporting**: When new Homey capabilities are detected (e.g., after an app update), the integration now shows a persistent notification with device and capability details plus a prefilled GitHub issue link. Call `homey.test_capability_report` from Developer Tools → Actions to try the report flow and see the format. Reports include device class, driver, type, setable/getable flags, and suggested platform for unknown capabilities.

## [1.1.8] - 2026-02-05

### Fixed
- **Cover stop**: Enum-based covers now stop correctly even when position capability exists
- **Token prompts**: Avoids nightly reauth on transient 401s and logs the reason clearly for troubleshooting

## [1.1.7] - 2026-01-27

**Highlights**

- **Multi-Homey**: Supports multiple hubs with auto-rescope and collision-safe IDs. Single‑hub users are unaffected and keep existing devices as-is.
- **Logic Variables**: Numbers/booleans/strings now appear as entities. Ensure the API key includes `homey.logic.readonly` (and `homey.logic` for editing).
- **Options & Settings**: Manage API key/host updates and tune string exposure plus advanced behaviors from the integration options.

### Added
- **Homey Logic variables**: Import Logic numbers, booleans, and strings as Number, Switch, and Text entities
- **Multi-homey guardrails**: Multi-homey activates only when 2+ hubs exist, with auto-rescope when a new hub is added
- **Multi-homey unique IDs**: Entity and device identifiers are scoped per Homey hub to prevent collisions
- **User notifications**: Pending rescope, migration start/finish, duplicate hub detection
- **Read-only string sensors (default on)**: String capabilities can be exposed without enabling editable text inputs
- **Text entities (optional)**: Expose settable string capabilities as editable text inputs via integration options
- **Switch coverage**: Create switches for other settable boolean capabilities beyond `onoff`
- **Enum/string selects**: Select entities now support string/enum capabilities with proper titles
- **Capability reporting**: Notify when new capabilities appear with a prefilled GitHub issue link (auto-labeled `enhancement`)
- **Light temperature option**: Toggle to invert normalized `light_temperature` for devices with warm/cold reversed
- **Generic sensor coverage**: Create sensors for getable numeric/string capabilities beyond `measure_*` and `meter_*`
- **Heat pump counters**: Added compressor counter sensors (`compressor_hours`, `compressor_starts`)
- **Automation checks**: CI runs HASSfest, HACS, syntax, lint, type, test, and pre-commit checks

### Fixed
- **Cover controls**: Use enum `windowcoverings_state` for actions and `windowcoverings_set` for numeric position where available
- **Logic device retention**: Prevent device filter cleanup from removing the Homey Logic device
- **Entity registration conflicts**: Avoid duplicate entity warnings for multi-homey sensors
- **Entity migration gaps**: Entities without config entry linkage are migrated by legacy identifiers
- **Multi-homey device removal**: Prevent devices from disappearing when multiple Homeys are configured
- **Invert toggle persistence**: Light temperature inversion option now persists correctly in settings
- **Options persistence**: String exposure toggles now persist reliably across reloads
- **Binary sensor filtering**: Settable boolean capabilities no longer create duplicate binary sensors
- **Heat pump status entities**: Restored missing boolean entities (e.g., `compressor_active`, `circulation_pump`, `hot_water`)
- **Cover stop error**: Fixed `UnboundLocalError` when stopping enum-based curtains
- **Service setup error**: Fixed `vol` import scoping issue during integration setup
- **Light temperature default**: Invert normalized `light_temperature` by default (warm/cold correction)
- **Light color temperature**: Expose color temperature mode even when saturation is missing
- **CI type checks**: Mypy is enforced again after fixing type errors

### Notes
- **Single Homey users**: No change needed — the integration works as before
- **Multiple Homeys**: When a second hub is added, entities are re-scoped to avoid collisions and device visibility issues
- **Missing status strings**: If you can’t see status/notification strings, check the string toggles in settings; you can disable them if you don’t want those entities

## [1.1.6] - 2026-01-15

### 🚀 Major Real-Time Updates Release

**This is a significant update that transforms the integration from polling-based to real-time event-driven updates. Device state changes in Homey now appear in Home Assistant instantly (< 1 second) instead of waiting for the next poll cycle (previously 10 seconds). This provides a truly responsive smart home experience where actions taken in Homey (via app, physical switches, or automations) are immediately reflected in Home Assistant's UI.**

**⚠️ IMPORTANT: API Key Requirement**
- **This feature requires a new API key with the `homey.system.readonly` permission enabled**
- Go to **Homey Settings → API Keys** and **create a new API key**
- Enable the **System → View System** permission (`homey.system.readonly`)
- After creating the new API key, update your Home Assistant integration configuration with the new key and restart Home Assistant or reload the Homey integration
- Without this permission, Socket.IO real-time updates will not work and the integration will fall back to polling
- The integration will continue to work with polling if the permission is missing, but you won't get instant updates

**What This Really Means:**
- **Before**: When you turned on a light in Homey, Home Assistant would show the old state until the next poll (up to 10 seconds later)
- **After**: When you turn on a light in Homey, Home Assistant updates instantly (< 1 second) - the UI reflects reality in real-time
- **Bidirectional**: Commands sent from Home Assistant to Homey also get instant feedback, so you see the result immediately
- **Seamless**: If Socket.IO connection fails, the integration automatically falls back to polling (5-10 seconds) - you never lose updates
- **Efficient**: When Socket.IO is active, polling reduces to 60 seconds (safety net), saving API calls while maintaining reliability

### Added
- **Socket.IO Real-Time Updates**: Full support for real-time device updates via Socket.IO
  - Integration now uses Socket.IO for instant device state updates when available
  - Device changes in Homey (via app, physical switches, or automations) appear in Home Assistant immediately (< 1 second)
  - Socket.IO provides bidirectional communication for instant feedback on control commands
  - Automatic fallback to polling (every 5 seconds) if Socket.IO connection fails or disconnects
  - Seamless reconnection: Socket.IO automatically reconnects if connection is lost
  - Connection status clearly logged: INFO when Socket.IO connects, WARNING when it disconnects and polling takes over
  - Polling continues as backup even when Socket.IO is active, ensuring updates are never missed
  - Works with both local Homey devices and self-hosted Homey servers
- **Options & Reauth flows**: Update Homey host/IP, API key, and fallback polling settings without reinstalling
- **Reauthentication flow**: Prompts for a new API key when credentials are invalid
- **Auto-recovery**: Integration reconnects automatically after Homey restarts or network drops
- **Devicegroups plugin support**: Groups are detected and handled based on class/capabilities (lights, fans, switches, climate, covers)
- **Energy dashboard compatibility**: Energy sensors now use proper device_class/state_class and kWh units
- **Price sensor unit normalization**: Tibber sensors normalize currency units (SEK/EUR/USD) to `/kWh`
- **Accumulated cost currency detection**: Auto-detects currency for `accumulatedCost`
- **Battery device support**: Full sensor mapping for Homey battery devices
- **Lawn mower support**: Gardena lawn mower buttons and sensors
- **Heat pump support**: Expanded heat pump capabilities, programs, and sensors
- **Generic boolean binary sensors**: All boolean capabilities detected (not only alarm_*)
- **Number pattern matching**: Auto-detects numeric settable sub-capabilities (target_temperature.*)

### Fixed
- **Cover position feature**: Use compatible position feature flags to avoid attribute errors on older HA versions
- **Enum-based windowcoverings support**: Proper enum handling for `windowcoverings_state` (up/idle/down)
- **Device selection defaults**: All devices are selected by default in the setup flow
- **Transient outages**: Prevents device removals when the API temporarily returns no devices
- **Self-hosted SSL support**: Proper HTTPS handling for Homey self-hosted servers
- **Vacuum compatibility**: Updated vacuum entity to HA 2026.1 API
- **Light detection for socket-class devices**: Dimmable/socket-class devices now detected as lights
- **Sensor labeling**: Corrected energy vs power sensor labels
- **Cover operation handling**: Improved handling for `windowcoverings_set` and cover operations
- **Area assignment**: Preserves user-assigned areas; only updates integration-set areas
- **Indentation/stability fixes**: Multiple platform files now load cleanly without syntax errors

### Changed
- **Socket.IO logging**: Reduced per-update log noise (kept only key status)

## [1.1.5] - 2026-01-12

### 🎉 Major Release: Comprehensive Device Support Expansion and Home Assistant 2026.1 Compatibility

This is a significant release that dramatically expands device support and platform capabilities. Highlights include:

- **New device types**: Vacuum cleaners, battery storage, lawn mowers, heat pumps, solar panels
- **Universal capability detection**: Automatic support for all `measure_*`, `meter_*`, and `alarm_*` capabilities
- **Energy dashboard integration**: Proper energy classes/units + currency normalization for price sensors
- **Enhanced platform support**: Number entities, generic boolean binary sensors, enum-based select entities
- **Custom thermostat support**: Mode-based control for ThermoFloor and other custom thermostats
- **Home Assistant 2026.1 compatibility**: Vacuum entity updates to `StateVacuumEntity`/`VacuumActivity`
- **Device classification improvements**: Light/switch detection, multi-channel switches, enum covers
- **User experience improvements**: Area preservation, flow trigger selector, reduced log noise

### Added

#### New Device Support
- **Vacuum cleaner support**: Full integration with cleaning states, battery, dock control, fan speeds, modes
- **Battery devices**: Comprehensive sensors for capacity, charging/discharging, emergency reserve, module count
- **Lawn mower support**: Gardena mower buttons and sensors
- **Heat pump support**: Target temperature sub-capabilities, programs, sensors, compressor stats
- **Solar panel support**: Grid/battery/house delivery sensors and connected status

#### Enhanced Platform Support
- **Generic boolean binary sensors**: All boolean capabilities detected (not just `alarm_*`)
- **Universal sensor support**: Automatic handling for all `measure_*` and `meter_*` capabilities
- **Universal alarm support**: Automatic handling for all `alarm_*` capabilities
- **Number entity pattern matching**: Auto-detect numeric settable sub-capabilities (e.g., `target_temperature.*`)
- **Select entity enhancements**: Enum capabilities become select entities (e.g., Tibber price level)

#### Energy Dashboard Support
- **Energy sensor compatibility**: Proper `device_class`/`state_class` and kWh units
- **Price unit normalization**: Currency symbols normalized to `/kWh` (SEK/EUR/USD)
- **Accumulated cost currency detection**: Auto-detects currency from related price sensors
- **Sub-capability support**: `meter_power.*` sub-capabilities correctly mapped

#### Custom Thermostat Support
- **Custom mode capabilities**: `_mode` enums mapped to HVAC modes
- **Thermostat binary sensors**: Proper read-only status sensors (e.g., `thermofloor_onoff`)

### Fixed

#### Home Assistant 2026.1 Compatibility
- **Vacuum entity compatibility**: Updated to `StateVacuumEntity` + `VacuumActivity`

#### Device Detection & Classification
- **Light detection for socket-class devices**: Dimmable sockets detected as lights
- **Switch detection**: Sub-capability handling for multi-channel switches
- **Multi-channel switch classification**: Proper classification for `onoff.output*` devices
- **Sensor labeling**: Energy vs power labels corrected

#### Cover Operation
- **Cover position feature flag**: Correct position feature handling for numeric covers
- **Enum-based windowcoverings**: Proper enum handling (up/idle/down)
- **Cover operation improvements**: Better `windowcoverings_set` handling and error control

#### Area Assignment
- **User-assigned areas preserved**: No overwriting manual areas

#### Climate Entity Controls
- **Turn on/off support**: Proper control + read-only status handling

#### Flow Trigger Service
- **Entity selector**: Flow trigger service now supports entity selector with clearer errors

#### Logging Improvements
- **Reduced log noise**: Routine logs and expected warnings lowered to DEBUG

### Changed

#### Currency Handling
- **No default currency** for unknown symbols

#### Light Detection Logging
- **Enhanced logging** for troubleshooting device classification

## [1.1.3] - 2026-01-11

### 🎉 Major Device Classification and Capability Support Update

**This version significantly improves device classification accuracy, adds comprehensive support for all Homey device classes and capabilities, fixes maintenance button filtering, adds multi-channel switch support, and includes enhanced troubleshooting documentation.**

### Added

#### Comprehensive Device Class Support
- **All Homey Device Classes**: Added support for all Homey device classes including `light`, `socket`, `sensor`, `thermostat`, `speaker`, `tv`, `remote`, `windowcoverings`, `cover`, `garagedoor`, `curtain`, `blind`, `shutter`, `awning`, `lock`, `fan`, `camera`, `doorbell`, and `other`
- **Device Class Priority**: Homey's `device_class` field is now used as the primary classification method for more reliable device type detection
- **Garage Door Support**: Added support for `garagedoor_closed` capability (garage doors are now detected as covers)
- **Window Coverings Variants**: Added support for `windowcoverings_set` capability (alternative to `windowcoverings_state`) for devices that use different capability names

#### Multi-Channel Device Support
- **Multi-Channel Switches**: Added support for multi-channel switches with sub-capabilities (e.g., `onoff.output1`, `onoff.output2`)
- **Separate Switch Entities**: Multi-channel devices now create separate switch entities for each output channel
- **Entity Naming**: Multi-channel switches automatically get descriptive names (e.g., "Device Name Output 1", "Device Name Output 2")
- **Examples**: Supports devices like Shelly Plus 2 PM, Fibaro Double Switch, and other multi-channel relay devices

#### Enhanced Capability Support
- **Meter Capabilities**: Added support for `meter_power`, `meter_water`, and `meter_gas` capabilities with proper state classes (`TOTAL_INCREASING`)
- **Sub-Capability Support**: Full support for sub-capabilities (capabilities with dots, e.g., `measure_temperature.inside`, `alarm_motion.outside`)
- **Additional Binary Sensors**: Added support for `alarm_gas`, `alarm_fire`, `alarm_panic`, `alarm_burglar`, `alarm_generic`, `alarm_maintenance`, `button`, and `vibration` capabilities
- **Alternative Capability Names**: Added support for alternative capability names (`measure_wind_speed`, `measure_wind_direction`, `measure_light`, `measure_illuminance`)

#### Device-Specific Detection
- **Philips Hue Devices**: Enhanced detection to ensure Philips Hue devices (including White & Ambiance bulbs) are correctly identified as lights with full dimming and color temperature support
- **Sunricher Devices**: Added device-specific detection for Sunricher dimming devices to ensure they're classified as lights
- **Fibaro Devices**: Enhanced detection for Fibaro switches, outlets, and roller shutters to ensure correct classification
- **Shelly Devices**: Added device-specific detection for Shelly devices to ensure switches are correctly identified

#### Light Enhancements
- **Normalized Temperature Handling**: Improved handling of normalized `light_temperature` values (0-1) with automatic conversion to Kelvin range (2000-6500K)
- **Better Capability Detection**: Enhanced light entity creation to properly detect and expose dimming and color temperature capabilities

#### Maintenance Button Filtering
- **Maintenance Action Detection**: Added filtering for maintenance buttons using Homey's `maintenanceAction` property
- **Automatic Cleanup**: Added automatic cleanup of existing maintenance button entities (migrate, identify, reset buttons) on integration reload
- **Comprehensive Filtering**: Maintenance buttons are now filtered in button, sensor, and binary sensor platforms

#### Documentation
- **Troubleshooting Guide**: Added comprehensive troubleshooting guide with step-by-step instructions for gathering device information using Homey Developer Tools
- **Device Information Guide**: Added detailed guide explaining how to use Homey Web API Playground to get device capabilities and class information for issue reporting

### Fixed

#### Device Classification Fixes
- **Philips Hue E27 White & Ambiance**: Fixed issue where bulbs were recognized as lights but only supported on/off - now properly supports dimming and color temperature
- **Sunricher Dim Lighting**: Fixed issue where dimming devices were recognized as lights but only supported on/off - now properly supports dimming
- **Fibaro Walli Roller Shutter (FGWREU-111)**: Fixed issue where roller shutters were recognized as sensors - now correctly detected as covers
- **Fibaro Walli Switch (FGWDSEU-221)**: Fixed issue where switches were recognized as sensors - now correctly detected as switches
- **Fibaro Single/Double Switch (FGS-213/223)**: Fixed issue where switches were recognized as sensors - now correctly detected as switches
- **Fibaro Wall Plug (FGWPE-102)**: Fixed issue where wall plugs were recognized as sensors - now correctly detected as switches
- **Fibaro Walli Outlet (FGWOE-011)**: Fixed issue where outlets were recognized as sensors - now correctly detected as switches
- **Shelly Plus Plug S**: Fixed issue where Shelly devices were recognized as sensors - now correctly detected as switches
- **Shelly 1 Mini Gen 3**: Fixed issue where Shelly devices were recognized as sensors - now correctly detected as switches
- **Shelly Plus 2 PM**: Fixed issue where Shelly devices were recognized as sensors - now correctly detected as switches
- **Window Coverings with `windowcoverings_set`**: Fixed issue where devices using `windowcoverings_set` instead of `windowcoverings_state` were not detected as covers
- **Multi-Channel Switches**: Fixed issue where devices with `onoff.output1`, `onoff.output2` sub-capabilities were not creating switch entities - now creates separate switch entities for each channel

#### Priority Order Improvements
- **Control Capabilities First**: Fixed device classification priority to prioritize control capabilities (cover, light, switch) over sensor capabilities (measure_*, meter_*)
- **Switch vs Sensor**: Devices with `onoff` capability are now correctly classified as switches even when they also have metering capabilities

#### Maintenance Button Issues
- **Maintenance Buttons Appearing**: Fixed issue where maintenance buttons (migrate, identify, reset) were appearing as entities in Home Assistant
- **Entity Cleanup**: Added automatic removal of existing maintenance button entities on integration reload

#### Configuration Flow Bugfix
- **Missing Logger Import**: Fixed `NameError: name '_LOGGER' is not defined` error in config flow by adding missing logger import to `device_info.py` module

### Changed

#### Device Type Detection Logic
- **Priority Order**: Updated device type detection priority to: Cover > Light > Climate > Fan > Lock > Media Player > Switch > Sensor
- **Device Class Integration**: Homey's `device_class` field is now checked first for device classification, with capability-based detection as fallback
- **Multi-Entity Support**: Devices with both control and sensor capabilities now correctly get multiple entities (e.g., switch + power sensor)

#### Light Platform
- **Temperature Conversion**: Improved `light_temperature` handling to detect normalized values (0-1) and convert to Kelvin range automatically
- **Capability Logging**: Enhanced logging for light entity creation to help diagnose capability detection issues

#### Switch Platform
- **Classification Logic**: Updated switch platform to use centralized `get_device_type` function for consistent device classification
- **Multi-Channel Support**: Added support for multi-channel switches with sub-capabilities (e.g., `onoff.output1`, `onoff.output2`) - creates separate switch entities for each channel
- **Better Logging**: Improved logging to show why devices are or aren't created as switch entities

---

## [1.1.2] - 2026-01-10

### Fixed
- **Config Flow Validation Error** - Fixed "extra keys not allowed" error in config flow by importing `CONF_TOKEN` from local `const.py` instead of `homeassistant.const` (which doesn't include this constant). This resolves validation errors when adding the integration via HACS or manual installation.

---

## [1.1.1] - 2026-01-11

### Added
- **Migration Guide** - Added comprehensive migration instructions for users switching from manual installation to HACS
- **Installation Conflict Detection** - Integration now detects and warns about conflicting installation methods (manual + HACS)

### Fixed
- Improved detection of installation method conflicts to prevent update issues

---

## [1.1.0] - 2026-01-11

### 🎉 Major Feature Release: Scenes, Moods, and Enhanced Platforms

**This version adds comprehensive support for Homey Scenes and Moods, physical device buttons, Number and Select platforms, flow management services, and extensive sensor/binary sensor capabilities. It also includes a robust permission checking system and improved error handling.**

### Added

#### New Platforms
- **Scene Platform** - Homey scenes now appear as Scene entities in Home Assistant
- **Moods Support** - Homey moods are exposed as Scene entities with distinct icons
- **Number Platform** - Ready for numeric control capabilities (placeholder for future capabilities)
- **Select Platform** - Ready for mode/option selection capabilities (placeholder for future capabilities)
- **Physical Device Buttons** - Physical device buttons (`button`, `button.1`, etc.) now appear as Button entities

#### Enhanced Sensor Capabilities
- **Additional Sensor Types**: Noise (dB), Rain (mm), Wind Strength/Angle (m/s, °), Ultraviolet (UV index), PM2.5/PM10 (µg/m³), VOC (µg/m³), AQI, Frequency (Hz), Gas (ppm), Soil Moisture/Temperature (%, °C), Energy (kWh)
- **Proper State Classes**: Energy sensors now use `TOTAL_INCREASING` state class for proper energy tracking

#### Enhanced Binary Sensor Capabilities
- **Additional Alarm Types**: Gas, Fire, Panic, Burglar, Generic, Maintenance alarms
- **Physical Buttons**: Button capabilities detected as binary sensors
- **Vibration Detection**: Vibration sensor support

#### Climate Enhancements
- **Humidity Support**: Added current and target humidity properties with proper unit conversion
- **HVAC Mode Detection**: Dynamic HVAC mode detection based on available thermostat capabilities (`thermostat_mode_off`, `thermostat_mode_heat`, `thermostat_mode_cool`, `thermostat_mode_auto`)
- **Mode Support**: Full support for OFF, HEAT, COOL, AUTO, and HEAT_COOL modes

#### Media Player Enhancements
- **Rich Metadata**: Added support for artist, album, track name, duration, position
- **Playback Controls**: Added shuffle and repeat state support
- **Position Tracking**: Media position with timestamp tracking

#### Flow Management
- **Flow Enable/Disable Services**: Added `homey.enable_flow` and `homey.disable_flow` services
- **Service Flexibility**: Both services support `flow_id` or `flow_name` parameters

#### Permission System
- **Comprehensive Permission Checking**: Added permission validation system that checks API permissions for all features
- **Graceful Degradation**: Integration continues to work even when permissions are missing - features are simply disabled
- **Clear Warnings**: Detailed log messages inform users about missing permissions and their impact
- **Permission Documentation**: Updated README with complete permission requirements and impact table

#### HACS Integration
- **HACS Support**: Added `hacs.json` configuration file for HACS integration
- **HACS Installation Guide**: Updated README with comprehensive HACS installation instructions
- **Table of Contents**: Added navigation table of contents to README for easier navigation

### Fixed
- **Humidity Conversions** - Fixed handling of normalized (0-1) vs percentage (0-100) humidity values in sensors and climate controls
- **Climate Initialization Bug** - Fixed `capabilities` variable used before definition in climate platform
- **Migration Buttons** - Filtered out internal Homey migration capabilities (`button.migrate_v3`, `button.reset_meter`, `button.identify`) from appearing as button entities
- **Empty Feature Handling** - Integration now gracefully handles cases where users have permissions but no features configured (e.g., moods permission but no moods)
- **Entity Registry Method** - Fixed `AttributeError` when removing devices by replacing non-existent `async_entries_for_device` with proper entity registry iteration
- **Authentication Error Detection** - Improved error handling to correctly identify authentication failures (401) vs connection issues, providing clearer error messages
- **Light Color Sync** - Fixed incorrect color values on startup by refreshing device state when entities are first added to Home Assistant
- **Button Platform Indentation** - Fixed syntax error in button platform that prevented integration from loading
- **Thermostat Temperature Control** - Fixed thermostat temperature setting to handle all parameter formats (`temperature`, `target_temperature_high`, `target_temperature_low`) and added default min/max temperatures for proper UI controls
- **Flows Device Removal** - Fixed virtual "flows" device being incorrectly removed by device cleanup logic when device filtering is enabled
- **Flow Logging** - Improved flow discovery logging to show enabled vs disabled flows and help diagnose flow visibility issues

### Changed
- **Permission Names** - Updated all permission references to use correct Homey API v3 permission names (`homey.device.readonly`, `homey.flow.start`, etc.)
- **Error Handling** - Improved distinction between permission errors (401/403) and missing features (empty results)
- **Logging** - More informative log messages that distinguish between permission issues and normal empty results
- **Scene/Mood Detection** - Scenes and moods are now properly detected and exposed, with moods using distinct icons

### Technical Details

#### Permission Mapping
- `homey.device.readonly` - Required for device discovery and reading states
- `homey.device.control` - Required for device control
- `homey.zone.readonly` - Recommended for room/area organization
- `homey.flow.readonly` - Recommended for flow listing
- `homey.flow.start` - Recommended for flow triggering and management
- `homey.mood.readonly` - Recommended for mood listing
- `homey.mood.set` - Recommended for mood activation
- Scenes use device permissions (no separate scene permissions in Homey API v3)

#### Humidity Conversion Logic
- Automatically detects if humidity values are normalized (0-1) or percentage (0-100) based on capability `max` value
- Converts normalized values to percentage when reading
- Converts percentage to normalized values when writing
- Applies to both `measure_humidity` sensors and `target_humidity` climate controls

#### Feature Availability Handling
- Empty results (200 OK with empty data) are treated as normal - user just doesn't have that feature configured
- Permission errors (401/403) trigger warnings and disable features
- 404 errors are treated as feature not available on this Homey version
- Integration never breaks due to missing features or permissions

**Impact**: This release significantly expands the integration's capabilities, adding support for scenes, moods, and many new sensor types. The permission system ensures users understand what features require which permissions, and the integration gracefully handles all edge cases.

---

## [1.0.2] - 2026-01-09

### 🚀 Major Fix: Flow Support for Homey Pro 2026

**This version fixes critical issues with flow discovery and triggering, and adds support for Advanced Flows.**

### Fixed
- **Fixed flow endpoint bug** - Changed from incorrect `/api/manager/flows/flow` (plural) to correct `/api/manager/flow/flow` (singular) per Homey API v3 documentation
- **Fixed flow discovery** - Flows now properly appear as button entities in Home Assistant
- **Fixed flow triggering** - Both Standard and Advanced Flows can now be triggered successfully

### Added
- **Advanced Flows support** - Added support for Homey Advanced Flows using `/api/manager/flow/advancedflow` endpoint
- **Improved flow discovery** - Now fetches both Standard and Advanced Flows separately and combines them
- **Case-insensitive flow name matching** - Flow names can now be matched regardless of case when using service calls
- **Update guide** - Added comprehensive update instructions to README

### Changed
- **Reduced verbose logging** - Removed excessive debug logs for cleaner production logs
- **Improved flow error messages** - Better error messages when flows are not found, including list of available flows
- **Enhanced flow triggering** - Automatically uses correct endpoint (standard vs advanced) based on flow type

### Technical Details
- Standard Flows: `/api/manager/flow/flow` endpoint
- Advanced Flows: `/api/manager/flow/advancedflow` endpoint
- Flow type detection: Automatically marks flows as "standard" or "advanced" for correct endpoint usage
- Flow name matching: Now supports both exact match and case-insensitive matching

**Impact**: This fix resolves issues where flows were not appearing or could not be triggered, especially on Homey Pro 2026. All users with flows should update to this version.

---

## [1.0.1] - 2026-01-08

### 🎨 Major Fix: Light Color Control

**This version includes a critical fix for light color control that was preventing colors from changing correctly.**

### ⚠️ IMPORTANT: API Key Update Required

**Before upgrading to version 1.0.1, you MUST create a new API key in Homey with the following permissions:**

1. Go to **Homey Web App** → **Settings** → **API Keys**
2. Create a **new API key** (or update your existing one)
3. Ensure these permissions are enabled:
   - `device:read` - Required to read device states
   - `device:write` - Required to control devices
   - `zone:read` - **Required for room/area organization** (recommended)
   - `flow:read` - **Required for Flow support** (needed to list Flows and create button entities)
   - `flow:write` - **Required for Flow support** (needed to trigger Flows)
4. Update your Home Assistant integration configuration with the new API key

**Why?** This version includes improvements that require proper API permissions. Without `zone:read`, devices won't be organized by rooms. Without `device:write`, you won't be able to control devices. Without `flow:read` and `flow:write`, Flow support (button entities and service calls) will be disabled.

### Added
- Manual device deletion support - users can now delete devices from the Devices page
- Device selection during initial setup - choose which devices to import
- Post-setup device management - add/remove devices via integration options
- Device filtering - only selected devices are imported and managed

### Changed
- Removed emojis from device selection UI for better compatibility
- Improved error handling for 401 authentication errors - now tries all endpoints before failing
- Enhanced device value conversion to prevent "invalid literal for int()" errors
- Improved room/zone detection - gracefully handles missing zone permissions
- Updated config flow to handle missing zones/rooms gracefully
- Reduced polling interval from 30 seconds to 10 seconds for faster background updates
- Implemented immediate device state refresh after control commands for instant UI feedback (1-2 seconds)
- Improved logging - reduced excessive debug logging for production use
- Enhanced color control error handling - better error messages and logging for troubleshooting color issues

### Fixed
- **Fixed light color control** - Colors now change correctly! The issue was a value format mismatch between Home Assistant (hue 0-360°, saturation 0-100%) and Homey API (normalized 0-1). The integration now automatically converts between these formats.
- Fixed light color mode validation - prevents "invalid supported color modes" warnings by correctly handling color mode combinations
- Improved color setting reliability - ensures light is turned on before setting color, sets saturation before hue, and enforces minimum brightness for color visibility
- Fixed schema serialization errors in config flow (`cv.multi_select` instead of boolean checkboxes)
- Fixed authentication flow - no longer fails immediately on first 401 error
- Fixed device registry updates - devices now properly sync names and areas
- Fixed device deletion - devices removed from Homey are now properly cleaned up
- Fixed deprecated constants (`ATTR_COLOR_TEMP_KELVIN`, removed `UnitOfVoltage`)
- Fixed coordinator update interval - now uses `timedelta` instead of `int`
- Fixed binary sensor device class - removed unsupported `CO2` device class
- Fixed thermostat temperature sync - now properly syncs back to Homey
- Fixed motion/contact sensor state updates - improved value parsing
- Fixed cover position handling - better handling of missing capability values
- Fixed flow triggering - tries multiple endpoints and HTTP methods
- Fixed missing `Any` import in `__init__.py`
- Fixed OptionsFlow initialization error (`AttributeError: property 'config_entry' has no setter`)
- Fixed missing `CONF_DEVICE_FILTER` import in coordinator causing `NameError`
- Fixed status update delays - status now updates immediately after control commands instead of waiting for polling cycle

### Technical Details
- Added automatic value format conversion for `light_hue` and `light_saturation` capabilities
- Home Assistant format → Homey API format: hue (0-360° → 0-1), saturation (0-100% → 0-1)
- Homey API format → Home Assistant format: hue (0-1 → 0-360°), saturation (0-1 → 0-100%)
- Updated API reference documentation to reflect Homey's normalized value format (0-1) for many capabilities

**Impact**: This fix resolves a critical issue where light colors would not change or would change incorrectly. All users with color-capable lights should update to this version.

### Known Issues
- **Room/Zone Detection**: Room grouping may not work if API key doesn't have `zone:read` permission. Devices will still be imported but without room grouping.
- **Config Flow Window Size**: Home Assistant config flow dialogs have a fixed size and cannot be customized. This is a Home Assistant limitation.
- **Socket.IO Real-time Updates**: Currently disabled due to authentication complexity. Using polling instead (10-second intervals) with immediate refresh after control commands for near-instant feedback.
- **Entity Name Updates**: Entity names (`_attr_name`) don't update automatically when device names change in Homey. Device names in UI will update, but entity names require integration reload.
- **External Changes**: Changes made outside Home Assistant (via Homey app or physical switches) may take up to 10 seconds to appear in Home Assistant due to polling interval.

---

## [1.0.0] - 2026-01-08

### Added
- Initial release
- Support for multiple device types: lights, switches, sensors, binary sensors, covers, climate, fans, locks, media players
- Homey Flow (automation) triggering via button entities and service calls
- Automatic device discovery and synchronization
- Device registry synchronization (names, areas, deletions)
- Config flow for easy setup
- Options flow for device management
- Room/area organization based on Homey zones
- Device type detection and grouping

### Technical Details
- Uses `DataUpdateCoordinator` for efficient polling
- Supports multiple Homey API endpoint structures (Manager API and V1 API)
- Automatic endpoint discovery
- Robust error handling and fallback mechanisms
- Type hints throughout codebase
- Comprehensive logging

---

## Version History Notes

### How to Use This Changelog

- **Unreleased**: Changes that are in development but not yet released
- **Version numbers**: Follow semantic versioning (MAJOR.MINOR.PATCH)
- **Release naming**: Stable releases should use `vX.Y.Z` for tags/titles (no dev/beta suffixes)
- **Sections**: Added, Changed, Fixed, Removed, Known Issues
- **Details**: Each entry should be clear and actionable
- **README versioning**: Update the README with stable-only versions (no dev/beta), and summarize everything since the last main release

### Contributing

When making changes:
1. Add entries to the "Unreleased" section
2. Group changes by type (Added, Changed, Fixed, etc.)
3. Be specific about what changed and why
4. Include relevant issue numbers or references
5. When releasing, move "Unreleased" to a new version section

---

**Last Updated**: 2026-05-07
