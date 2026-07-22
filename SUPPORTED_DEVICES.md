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
- [Vacuum Cleaners](#vacuum-cleaners)
- [Battery Devices](#battery-devices)
- [Lawn Mowers](#lawn-mowers)
- [Heat Pumps](#heat-pumps)
- [Solar Panels](#solar-panels)
- [Generic Capability Support](#generic-capability-support)


---

## Lights

**Capabilities**
- `onoff` - Basic on/off control
- `dim` - Brightness control (0-100%)
- `light_hue` - Color hue control (0-360°)
- `light_saturation` - Color saturation control (0-100%)
- `light_temperature` - Color temperature control (Kelvin)
- `lightScenes.light` - Light scene/effect selection (when provided by the driver)

**Color Modes**
- `onoff` - Simple on/off
- `brightness` - Dimming only
- `hs` - Hue and saturation (full color)
- `color_temp` - Color temperature (warm/cool white), Kelvin scale (2000K-6500K)

HS color and color temperature modes are mutually exclusive. If both are available, HS is preferred.

If a light exposes `lightScenes.light`, it can also be controlled through the light `effect` field.

**Note**: Devices with dimming or color capabilities are created as lights, not switches.


---

## Switches

**Capabilities**
- `onoff` - On/off control
- `onoff.output1`, `onoff.output2`, etc. - Multi-channel switches (sub-capabilities)

**Multi-Channel Support**: Devices with multiple outputs (e.g., Shelly Plus 2 PM, Fibaro Double Switch) create separate switch entities for each channel.


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
- `measure_co2` - CO2 (ppm)
- `measure_co` - CO (ppm)
- `measure_distance` - Distance (cm), for ultrasonic/ToF presence sensors
- `measure_noise` - Sound pressure (dB)
- `measure_rain` - Rainfall (mm)
- `measure_wind_strength` - Wind speed (m/s)
- `measure_wind_angle` - Wind direction (°)
- `measure_ultraviolet` - UV index
- `measure_pm25` - PM2.5 air quality (µg/m³)
- `measure_pm10` - PM10 air quality (µg/m³)
- `measure_voc` - Volatile Organic Compounds (µg/m³)
- `measure_aqi` - Air Quality Index
- `measure_frequency` - Frequency (Hz)
- `measure_gas` - Gas (ppm)
- `measure_soil_moisture` - Soil moisture (%)
- `measure_soil_temperature` - Soil temperature (°C)
- `measure_energy` - Energy consumption (kWh)
- `meter_power` - Energy meter (kWh), Energy Dashboard compatible
- `meter_power.imported` - Imported energy (kWh), Energy Dashboard compatible
- `meter_power.exported` - Exported energy (kWh), Energy Dashboard compatible
- `meter_power.output1`, `meter_power.output2`, etc. - Multi-channel energy meters, Energy Dashboard compatible
- `meter_water` - Water meter (m³)
- `meter_gas` - Gas meter (m³)
- `measure_price_total` - Total electricity price (currency/kWh), Energy Dashboard compatible
- `measure_price_lowest` - Lowest electricity price (currency/kWh)
- `measure_price_highest` - Highest electricity price (currency/kWh)
- `accumulatedCost` - Accumulated energy cost (currency)

**Sub-Capability Support**: Capabilities with dots (e.g., `measure_temperature.inside`, `measure_power.output1`) create separate sensor entities with descriptive names.

**Generic Sensor Support**: Any `measure_*` or `meter_*` capability is automatically created as a sensor, even if not explicitly listed.


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
- `button` - Physical button press detection
- `vibration` - Vibration detection
- `thermofloor_onoff` - Thermostat heating active/idle status (read-only)

**Generic Binary Sensor Support**: Any boolean-type capability is automatically created as a binary sensor (excluding buttons). Includes device-specific capabilities like `circulation_pump`, `comfort_program`, `eco_program`, `hot_water`, `compressor_active`, etc.


---

## Covers

**Capabilities**
- `windowcoverings_state` - Window covering position (0-100%)
- `windowcoverings_set` - Alternative window covering position capability
- `windowcoverings_tilt_up` / `windowcoverings_tilt_down` - Tilt control
- `garagedoor_closed` - Garage door state (open/closed)

Both `windowcoverings_state` and `windowcoverings_set` are supported.

**Legacy Fibaro / dim-based shutters**

Some older Fibaro Z-Wave roller shutters (and similar drivers) expose position through the `dim` capability (0–1) instead of `windowcoverings_state` or `windowcoverings_set`. When the Homey device class is a window covering (`blind`, `shutter`, `windowcoverings`, etc.) or the Fibaro driver indicates a roller/shutter, the integration creates a `cover.*` entity that maps open/close/position to `dim`.


---

## Climate

**Capabilities**
- `target_temperature` - Target temperature control (°C)
- `target_humidity` - Target humidity control (%)
- `measure_temperature` - Current temperature (°C)
- `measure_humidity` - Current humidity (%)
- `thermostat_mode` - HVAC mode control (off, heat, cool, auto)
- `thermostat_mode_off`, `thermostat_mode_heat`, `thermostat_mode_cool`, `thermostat_mode_auto` - Mode capabilities
- `thermofloor_mode` - Custom thermostat mode (e.g., ThermoFloor: Heat, Energy Save Heat, Off, Cool)
- `*_mode` - Any enum capability ending with `_mode` is automatically detected

**Supported HVAC Modes**: OFF, HEAT, COOL, AUTO, HEAT_COOL (detected from available capabilities)

**Custom Thermostat Support**: Custom mode values map to standard HVAC modes (Off, Heat, Cool, Energy Save Heat/Auto).

**Turn On/Off**: If the device has a settable `onoff` capability, it is used. Otherwise, `turn_on` sets the first non-OFF mode and `turn_off` sets OFF.


---

## Fans

**Capabilities**
- `fan_speed` - Fan speed control (0-100%)
- `onoff` - On/off control


---

## Locks

**Capabilities**
- `locked` - Lock state and control


---

## Media Players

**Capabilities**
- `volume_set` - Volume control (0-100%)
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


---

## Scenes and Moods

**Scenes**: All Homey scenes appear as Scene entities. Activate directly from Home Assistant.

**Moods**: All Homey moods appear as Scene entities with a distinct icon. Activate directly from Home Assistant.


---

## Buttons

**Capabilities**
- `button` - Virtual button (Homey Virtual Devices) or single-button device
- `button.1`, `button.2`, etc. - Multi-button devices
- Physical device buttons appear as Button entities for automation triggers
- Device-specific buttons (e.g., `gardena_button.park`, `gardena_button.start`) are automatically detected


---

## Select Entities

**Generic Enum Support**: Any enum-type capability is automatically created as a select entity.

**Examples**
- `thermofloor_mode` - Thermostat mode (Heat, Energy Save Heat, Off, Cool)
- `measure_price_level` - Price level (VERY_CHEAP, CHEAP, NORMAL, EXPENSIVE)
- `measure_price_info_level` - Price info level
- `price_level` - Price level indicator
- `operating_program` - Heat pump operating program

Any capability with `values` or `options` (enum type) is automatically created as a select entity.


---

## Number Entities

**Capabilities**
- Any settable numeric capability not handled by another platform
- `target_temperature.*` sub-capabilities (normal, comfort, reduced, dhw, dhw2) for heat pumps
- Pattern-based detection for numeric sub-capabilities


---

## Text Entities

**Capabilities**
- Settable string capabilities without predefined options
- Requires "Expose string capabilities as editable text inputs" enabled in integration options
- Read-only string capabilities appear as sensors by default (can be disabled)


---

## Vacuum Cleaners

**Device Class**: `vacuumcleaner`

**Control Capabilities**
- `clean_full` - Start cleaning (all rooms)
- `pause_clean` - Pause/resume cleaning
- `dock` - Return to dock
- `suction_power` - Fan speed (select entity)
- `is_cleaning` - Cleaning state
- `measure_battery` - Battery level (%)
- `battery_charging_state` - Charging state

**Sensors**
- `clean_time` - Cleaning time (hours)
- `clean_area` - Cleaning area (m²)
- `clean_last` - Last cleaning task (hours ago)
- `position_x` / `position_y` - Position coordinates

**Binary Sensors**
- `alarm_problem` - Problem detected
- `alarm_stuck` - Vacuum stuck
- `alarm_battery` - Low battery
- `water_box_attached` - Water box attached
- `mop_attached` - Mop attached
- `mop_dry_status` - Mop drying status

**Select Entities**
- `suction_power` - Vacuum intensity (quiet, balanced, turbo, max, off, max+)
- `clean_mode` - Clean mode (vacuum & mop, vacuum only, mop only)
- `mop_route` - Mop route (standard, deep, deep+, fast)
- `scrub_intensity` - Mop intensity (off, mild, moderate, intense)
- `active_map` - Active map selection


---

## Battery Devices

**Device Class**: `battery`

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

**Device Class**: `other` with Gardena capabilities

**Buttons**
- `gardena_button.park` - Park the mower
- `gardena_button.start` - Start mowing

**Sensors**
- `measure_battery` - Battery level (%)
- `gardena_wireless_quality` - Wireless signal quality (%)
- `gardena_mower_state` - Mower state (string)
- `gardena_operating_hours` - Operating hours


---

## Heat Pumps

**Device Class**: `heatpump`

**Climate Entity**
- `target_temperature` - Main target temperature (°C)
- `thermostat_mode` - HVAC mode (dhw, dhwAndHeating, standby)
- `measure_temperature` - Current temperature (°C)
- `measure_temperature.*` sub-capabilities (normal, comfort, reduced, outside, supply, dhw, dhw_outlet, return, dhw_top, dhw_bottom)

**Number Entities**
- `target_temperature.normal` - Day temperature target (°C)
- `target_temperature.comfort` - Comfort temperature target (°C)
- `target_temperature.reduced` - Night temperature target (°C)
- `target_temperature.dhw` - Hot water temperature target (°C)
- `target_temperature.dhw2` - Hot water temperature 2 target (°C)

**Select Entities**
- `operating_program` - Heating program (comfort, eco, fixed, normal, reduced, heatpump, standby)

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

**Device Class**: `solarpanel`

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

## Generic Capability Support

The integration automatically detects and creates entities for:

| Type | Pattern | Platform |
|------|---------|----------|
| Sensors | `measure_*`, `meter_*` | sensor |
| Binary sensors | Boolean capabilities (excluding buttons) | binary_sensor |
| Select entities | Enum capabilities (`values` or `options`) | select |
| Number entities | Settable numeric sub-capabilities | number |

This ensures support for new device types and capabilities without code changes.
