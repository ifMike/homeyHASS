# Supported Devices

This document lists the capabilities and device types supported by the Homey integration. The integration uses generic detection for many capability types, so new device types are often supported without code changes.

---

## Table of Contents

- [Lights](#lights)
- [Switches](#switches)
- [Sensors](#sensors)
- [Binary Sensors](#binary-sensors)
- [Covers](#covers)
- [Climate](#climate)
- [Fans](#fans)
- [Locks](#locks)
- [Media Players](#media-players)
- [Scenes and Moods](#scenes-and-moods)
- [Buttons](#buttons)
- [Select Entities](#select-entities)
- [Number Entities](#number-entities)
- [Text Entities](#text-entities)
- [Homey Logic Variables](#homey-logic-variables)
- [Homey Flows](#homey-flows)
- [Vacuum Cleaners](#vacuum-cleaners)
- [Battery Devices](#battery-devices)
- [Lawn Mowers](#lawn-mowers)
- [Heat Pumps](#heat-pumps)
- [Solar Panels](#solar-panels)
- [Homey Device Classes](#homey-device-classes)
- [Generic Capability Support](#generic-capability-support)

---

## Lights

**Capabilities**
- `onoff` - Basic on/off control
- `dim` - Brightness control (0–100% in HA; Homey often uses 0–1)
- `light_hue` - Color hue control
- `light_saturation` - Color saturation control
- `light_temperature` - Color temperature (Kelvin)
- `lightScenes` / `lightScenes.light` / `lightScenes.*` - Light scene/effect selection (exposed as light `effect` when values exist)

**Color Modes**
- `onoff` - Simple on/off
- `brightness` - Dimming only
- `hs` - Hue and saturation (full color)
- `color_temp` - Color temperature (warm/cool white), Kelvin scale (typically 2000K–6500K)

HS color and color temperature modes are mutually exclusive. If both are available, HS is preferred.

**Driver / class notes**
- Devices with dimming or color capabilities are created as lights, not switches
- Philips Hue drivers with `onoff` are treated as lights even if dim/color caps are incomplete
- Sunricher dimmers with `onoff` are treated as lights
- Homey class `socket` that also has `dim` / light color caps is treated as a light
- Devicegroups with class `light` create light entities
- Optional integration setting: invert `light_temperature` direction

---

## Switches

**Capabilities**
- `onoff` - On/off control
- `onoff.output1`, `onoff.output2`, etc. - Multi-channel switches (sub-capabilities)
- `nest_thermostat_eco` - Google Nest Eco mode (settable boolean)
- Other settable boolean capabilities not owned by another platform (light, lock, fan, button, etc.) become switches

**Multi-Channel Support**: Devices with multiple outputs (e.g., Shelly Plus 2 PM, Fibaro Double Switch) create separate switch entities for each channel.

**Also**: Homey Logic boolean variables → switches (see [Homey Logic Variables](#homey-logic-variables)). Devicegroups with class `socket` / `switch` create switch entities.

---

## Sensors

**Measure Capabilities**
- `measure_temperature` - Temperature (°C)
- `measure_temperature.inside`, `measure_temperature.outside`, etc. - Sub-capability temperature sensors
- `measure_humidity` - Humidity (%)
- `measure_pressure` - Pressure (hPa)
- `measure_power` - Power consumption (W)
- `measure_power.output1`, `measure_power.output2`, etc. - Multi-channel power sensors
- `measure_voltage` - Voltage (V)
- `measure_current` - Current (A)
- `measure_luminance` - Light level (lux)
- `measure_light` / `measure_illuminance` - Aliases of luminance (lux)
- `measure_co2` - CO2 (ppm)
- `measure_co` - CO (ppm)
- `measure_distance` - Distance (cm), for ultrasonic/ToF presence sensors
- `measure_noise` - Sound pressure (dB)
- `measure_rain` - Rainfall (mm)
- `measure_wind_strength` / `measure_wind_speed` - Wind speed (m/s)
- `measure_wind_angle` / `measure_wind_direction` - Wind direction (°)
- `measure_ultraviolet` - UV index
- `measure_pm25` - PM2.5 air quality (µg/m³)
- `measure_pm10` - PM10 air quality (µg/m³)
- `measure_voc` - Volatile Organic Compounds (µg/m³)
- `measure_aqi` - Air Quality Index
- `measure_frequency` - Frequency (Hz)
- `measure_gas` - Gas (ppm)
- `measure_soil_moisture` / `measure_moisture` - Soil / moisture (%)
- `measure_soil_temperature` - Soil temperature (°C)
- `measure_energy` - Energy consumption (kWh)
- `measure_battery` - Battery level (%)
- `meter_power` - Energy meter (kWh), Energy Dashboard compatible
- `meter_power.imported` / `meter_power.exported` - Imported / exported energy (kWh)
- `meter_power.output1`, `meter_power.output2`, etc. - Multi-channel energy meters
- `meter_power.charged` / `meter_power.discharged` - Battery charge/discharge energy (kWh)
- `meter_water` - Water meter (m³)
- `meter_gas` - Gas meter (m³)
- `measure_price_total` - Total electricity price (currency/kWh), Energy Dashboard compatible
- `measure_price_lowest` / `measure_price_highest` - Price extremes (currency/kWh)
- `measure_price_level` / `measure_price_info_level` - Price level indicators (sensor when not handled as enum select)
- `accumulatedCost` - Accumulated energy cost (currency)
- Legacy `sgas*` / `swater*` meter names - Gas / water cumulative sensors

**Battery / solar extras** (also listed under their device sections): `measure_capacity`, `measure_max_charging_power`, `measure_max_discharging_power`, `measure_emergency_power_reserve`, `measure_dcbcount`, `measure_grid_delivery`, `measure_battery_delivery`, `measure_house_consumption`, `firmware_version`, `charge_time`, Gardena string sensors, etc.

**Sub-Capability Support**: Capabilities with dots (e.g., `measure_temperature.inside`, `meter_power.imported`) create separate sensor entities with descriptive names.

**Generic Sensor Support**: Any `measure_*` or `meter_*` capability is automatically created as a sensor, even if not explicitly listed. Other getable numeric/string capabilities (non-enum) can also become sensors when not owned by another platform.

**Long string sensors**: Read-only string capabilities longer than 255 characters are truncated in the entity state (SVG markup → `svg`); the full value is in the `full_value` attribute.

---

## Binary Sensors

**Capabilities**
- `alarm_motion` - Motion detector
- `alarm_contact` - Door/window contact sensor
- `alarm_tamper` - Tamper sensor
- `alarm_vibration` - Vibration detection
- `alarm_occupancy` - Occupancy detection
- `alarm_presence` - Presence detection
- `alarm_smoke` - Smoke detector
- `alarm_co` - CO alarm
- `alarm_co2` - CO2 alarm
- `alarm_water` - Water leak detector
- `alarm_battery` - Low battery indicator
- `alarm_gas` - Gas alarm
- `alarm_fire` - Fire alarm
- `alarm_panic` - Panic alarm
- `alarm_burglar` - Burglar alarm
- `alarm_generic` - Generic alarm
- `alarm_maintenance` - Maintenance required indicator
- `alarm_problem` / `alarm_stuck` - Vacuum problem / stuck (also under Vacuum)
- `vibration` - Vibration detection
- `thermofloor_onoff` - Thermostat heating active/idle status (read-only; not used for climate turn on/off)
- `circulation_pump`, `comfort_program`, `eco_program`, `hot_water`, `compressor_active` - Heat-pump status flags
- `water_box_attached`, `mop_attached`, `mop_dry_status` - Vacuum accessory status
- `external_power_delivery_connected` - Solar / power source connected

**Generic Binary Sensor Support**: Any boolean-type capability is automatically created as a binary sensor (excluding settable buttons). Homey class `doorbell` maps to binary sensor.

**Note**: Settable `button` / `button.*` capabilities create **button** entities, not binary sensors. Non-setable boolean `button` may still appear as a binary sensor.

---

## Covers

**Capabilities**
- `windowcoverings_state` - Window covering position or state (numeric 0–1 or enum `up` / `idle` / `down`)
- `windowcoverings_set` - Alternative window covering position capability
- `windowcoverings_tilt_up` / `windowcoverings_tilt_down` - Tilt control (both required for tilt support)
- `garagedoor_closed` - Garage door state (open/closed)

Both `windowcoverings_state` and `windowcoverings_set` are supported for position-style covers.

**Homey device classes**: `windowcoverings`, `cover`, `curtain`, `blind`, `shutter`, `awning`, `garagedoor` (also devicegroups with those classes).

**Legacy Fibaro / dim-based shutters**

Some older Fibaro Z-Wave roller shutters (and similar drivers) expose position through the `dim` capability (0–1) instead of `windowcoverings_state` or `windowcoverings_set`. When the Homey device class is a window covering or the Fibaro driver indicates a roller/shutter (`fgr` / `fgw` / `roller` / `shutter` / `blind`), the integration creates a `cover.*` entity that maps open/close/position to `dim`.

---

## Climate

**Capabilities**
- `target_temperature` - Target temperature control
- `target_humidity` - Target humidity control (%)
- `measure_temperature` - Current temperature
- `measure_humidity` - Current humidity (%)
- `thermostat_mode` - HVAC mode control when present
- `thermostat_mode_off`, `thermostat_mode_heat`, `thermostat_mode_cool`, `thermostat_mode_auto` - Discrete mode capabilities
- `thermofloor_mode` - ThermoFloor custom mode (Heat, Energy Save Heat → AUTO, Off, Cool)
- `nest_thermostat_mode` - Google Nest HVAC mode (off, heat, cool, heatcool → HEAT_COOL); preferred over other `*_mode` enums when present
- `nest_thermostat_hvac` - Google Nest HVAC action (off, heating, cooling, …) → climate `hvac_action`
- `nest_thermostat_eco` - Google Nest Eco mode → **switch** (not HVAC mode)
- `*_mode` - Other enum capabilities ending with `_mode` (except `thermostat_mode`) can drive climate modes
- Settable `onoff` or settable `*_onoff` - Used for climate turn on/off when available (`thermofloor_onoff` is read-only and is **not** used for control)

**Supported HVAC Modes**: OFF, HEAT, COOL, AUTO, HEAT_COOL (from mapped Homey values)

**Custom Thermostat Support**: Custom mode strings map to standard HVAC modes (Off, Heat, Cool, HeatCool, Energy Save Heat/Auto). Unmapped Homey-specific values may not appear as HA HVAC modes.

**Google Nest** (`com.google.nest`): Thermostats with `target_temperature` plus Nest capabilities create a climate entity with mode + action mapping. Eco remains a switch.

**Devicegroups**: Groups with class `heater` / `thermostat` can create climate entities even without `target_temperature`.

**Turn On/Off**: Prefers settable `onoff` / `*_onoff`. Otherwise, `turn_on` / `turn_off` use HVAC mode when OFF and a non-OFF mode exist.

**Temperature units**: Per-device Homey unit resolution; optional override via the `homey_hass.set_device_temperature_unit` service / options.

---

## Fans

**Capabilities**
- `fan_speed` - Fan speed control (0–100%)
- `onoff` - On/off control
- `oscillate` - Oscillation toggle (tower / Dyson-style and similar)

Devicegroups with Homey class `fan` and `onoff` also create a fan entity even if `fan_speed` is missing.

---

## Locks

**Capabilities**
- `locked` - Lock state and control

Homey class `lock` maps to lock when capabilities allow.

---

## Media Players

**Capabilities**
- `volume_set` - Volume control (0–100%)
- `volume_mute` - Mute control
- `speaker_playing` - Play/pause control
- `speaker_next` - Next track
- `speaker_prev` - Previous track
- `speaker_artist` - Current artist
- `speaker_album` - Current album
- `speaker_track` - Current track title
- `speaker_duration` - Track duration (seconds)
- `speaker_position` - Playback position (seconds)
- `speaker_shuffle` - Shuffle state
- `speaker_repeat` - Repeat state

Homey classes `speaker` / `tv` map toward media player when capabilities allow.

---

## Scenes and Moods

**Scenes**: All Homey scenes appear as Scene entities. Activate directly from Home Assistant.

**Moods**: All Homey moods appear as Scene entities with a distinct icon. Activate directly from Home Assistant.

---

## Buttons

**Capabilities**
- `button` - Virtual button (Homey Virtual Devices) or single-button device
- `button.1`, `button.2`, etc. - Multi-button devices
- `*_button` - Device-specific button capabilities
- `gardena_button.park`, `gardena_button.start`, other `gardena_button.*` - Lawn mower / Gardena actions
- `less_air` / `more_air` - Step airflow down/up (Dyson and similar drivers)
- Physical device buttons appear as Button entities for automation triggers

Maintenance-style capabilities (`identify`, `reset`, `migrate`, etc.) are excluded.

---

## Homey Flows

Enabled Homey **Flows** (standard and advanced, when discovered) appear as Button entities under a **Homey Flows** device. Pressing the button triggers the flow.

Disabled flows are skipped. Requires Homey API flow permissions.

---

## Select Entities

**Generic Enum Support**: Any enum-type capability with `values` or `options` is eligible as a select entity (including unknown vendor enums).

**Explicit / common examples**
- `operating_program` - Heat pump operating program
- `suction_power`, `clean_mode`, `mop_route`, `scrub_intensity`, `active_map` - Vacuum enums
- `measure_price_level` / `measure_price_info_level` / `price_level` - When exposed as Homey enums

**Climate mode overlap**: Mode enums used by climate (`nest_thermostat_mode`, `thermofloor_mode`, `thermostat_mode`, other `*_mode`) are controlled via the climate entity. A parallel select may also appear for the same enum. Prefer the climate entity for HVAC control.

`windowcoverings_state` is handled by the cover platform, not select.

---

## Number Entities

**Capabilities**
- `target_temperature.*` sub-capabilities (e.g. `normal`, `comfort`, `reduced`, `dhw`, `dhw2`) for heat pumps and similar
- Other settable numeric **sub-capabilities** (capability id contains `.`) that are `type: number` and not owned by climate/light/etc.
- Homey Logic number variables (see [Homey Logic Variables](#homey-logic-variables))

Top-level settable numbers that are measurements stay sensors; they are not duplicated as number entities.

---

## Text Entities

**Capabilities**
- Settable string capabilities without predefined options
- Requires **Expose string capabilities as editable text inputs** enabled in integration options
- Read-only string capabilities appear as sensors by default (option: expose/hide readonly strings)
- Homey Logic string variables (always created when Logic is available; see below)

**Long values**: Home Assistant limits entity state to 255 characters. Longer Homey strings (for example SVG icons or long Logic text) are truncated in the state (SVG → `svg`); the full value is available as the `full_value` attribute.

---

## Homey Logic Variables

When Homey Logic API permissions allow (`homey.logic.readonly` / `homey.logic`):

| Homey type | Home Assistant |
|------------|----------------|
| Boolean | Switch |
| Number | Number |
| String | Text |

Logic entities are grouped under a **Homey Logic** device.

---

## Vacuum Cleaners

**Detection**: Homey class `vacuumcleaner`, or devices exposing `is_cleaning` / `clean_full` / `pause_clean` / `dock`.

**Control Capabilities**
- `clean_full` - Start cleaning (all rooms)
- `pause_clean` - Pause/resume cleaning
- `dock` - Return to dock
- `suction_power` - Fan speed on the vacuum entity (enum may also create a select)
- `is_cleaning` - Cleaning state
- `measure_battery` - Battery level (%) as a sensor (vacuum BATTERY feature removed on HA 2026.9+)
- `battery_charging_state` - Charging state (used for activity)

**Sensors**
- `clean_time` - Cleaning time
- `clean_area` - Cleaning area
- `clean_last` - Last cleaning task
- `position_x` / `position_y` - Position coordinates

**Binary Sensors**
- `alarm_problem` - Problem detected
- `alarm_stuck` - Vacuum stuck
- `alarm_battery` - Low battery
- `water_box_attached` - Water box attached
- `mop_attached` - Mop attached
- `mop_dry_status` - Mop drying status

**Select Entities** (when exposed as enums)
- `suction_power` - Vacuum intensity
- `clean_mode` - Clean mode
- `mop_route` - Mop route
- `scrub_intensity` - Mop intensity
- `active_map` - Active map selection

---

## Battery Devices

**Device Class**: Homey class `battery` (capability-driven; not a separate HA device type)

**Sensors**
- `measure_battery` - Battery level (%)
- `measure_capacity` - Battery capacity (kWh)
- `measure_voltage` - Battery voltage (V)
- `measure_temperature` - Battery temperature (°C)
- `measure_temperature_max` / `measure_temperature_min` - Cell temperature range (°C)
- `measure_power` - Current power (W)
- `meter_power.charged` - Total energy charged (kWh), Energy Dashboard compatible
- `meter_power.discharged` - Total energy discharged (kWh), Energy Dashboard compatible
- `measure_max_charging_power` - Max charging power (W)
- `measure_max_discharging_power` - Max discharging power (W)
- `measure_emergency_power_reserve` - Emergency reserve (Wh/kWh)
- `measure_dcbcount` - Module count

---

## Lawn Mowers

**Device Class**: Often `other` with Gardena capabilities

**Buttons**
- `gardena_button.park` - Park the mower
- `gardena_button.start` - Start mowing
- Other `gardena_button.*` actions when present

**Sensors**
- `measure_battery` - Battery level (%)
- `gardena_wireless_quality` - Wireless signal quality (%)
- `gardena_mower_state` - Mower state (string)
- `gardena_operating_hours` - Operating hours

---

## Heat Pumps

**Device Class**: Homey class `heatpump` (capability-driven)

**Climate Entity**
- `target_temperature` - Main target temperature
- `thermostat_mode` - Exposed on the climate entity when present; Homey-specific values (e.g. `dhw`, `dhwAndHeating`, `standby`) may not map 1:1 to HA HVAC modes
- `measure_temperature` - Current temperature
- `measure_temperature.*` sub-capabilities (normal, comfort, reduced, outside, supply, dhw, return, …)

**Number Entities**
- `target_temperature.normal` - Day temperature target
- `target_temperature.comfort` - Comfort temperature target
- `target_temperature.reduced` - Night temperature target
- `target_temperature.dhw` / `target_temperature.dhw2` - Hot water targets

**Select Entities**
- `operating_program` - Heating program (comfort, eco, fixed, normal, reduced, heatpump, standby, …)

**Binary Sensors**
- `circulation_pump` - Circulation pump status
- `comfort_program` - Comfort program active
- `eco_program` - Eco program active
- `hot_water` - Hot water heating active
- `compressor_active` - Compressor running

**Sensors**
- `compressor_hours` - Compressor operating hours
- `compressor_starts` - Compressor start count

---

## Solar Panels

**Device Class**: Homey class `solarpanel` (capability-driven)

**Sensors**
- `measure_power` - Current power generation (W)
- `meter_power` - Total energy generated (kWh), Energy Dashboard compatible
- `measure_grid_delivery` - Grid power delivery (W)
- `measure_battery_delivery` - Battery power delivery (W)
- `measure_house_consumption` - House consumption (W)
- `measure_battery` - Battery level (%)
- `firmware_version` - Firmware version (string)
- `charge_time` - Charge/discharge time estimate (string)

**Binary Sensors**
- `external_power_delivery_connected` - External power source connected

---

## Homey Device Classes

When Homey exposes a device `class`, the integration uses it as a strong hint (capabilities still win when more specific):

| Homey class | Typical HA type |
|-------------|-----------------|
| `light` | light |
| `socket` / `switch` | switch (unless light caps present) |
| `sensor` | sensor |
| `thermostat` / `heater` | climate |
| `speaker` / `tv` | media_player |
| `windowcoverings` / `cover` / `curtain` / `blind` / `shutter` / `awning` / `garagedoor` | cover |
| `lock` | lock |
| `fan` | fan |
| `vacuumcleaner` | vacuum |
| `doorbell` | binary_sensor |
| `button` | button platform entities |
| `remote` | sensor-oriented |
| `heatpump` / `solarpanel` / `battery` | capability-driven (see sections above) |
| `other` | capability-driven (e.g. Gardena mowers) |

---

## Generic Capability Support

The integration automatically detects and creates entities for:

| Type | Pattern | Platform |
|------|---------|----------|
| Sensors | `measure_*`, `meter_*`, plus known generics (`accumulatedCost`, vacuum clean_* / position_*) | sensor |
| Binary sensors | Boolean capabilities (excluding settable buttons) | binary_sensor |
| Select entities | Enum capabilities (`values` or `options`) | select |
| Number entities | Settable numeric **sub-capabilities** (`type: number` with `.` in id) | number |
| Switches | Other settable booleans not owned elsewhere | switch |
| Buttons | `button`, `button.*`, `*_button`, `gardena_button.*`, `less_air` / `more_air` | button |
| Flows | Enabled Homey flows | button |
| Logic | Boolean / number / string variables | switch / number / text |

This ensures support for new device types and capabilities without code changes. Unknown capabilities can still trigger a report notification so they can be mapped explicitly when needed.
