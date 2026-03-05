# Supported Devices

The integration supports devices with the following capabilities:

## Lights
- `onoff` - Basic on/off control
- `dim` - Brightness control (0-100%)
- `light_hue` - Color hue control (0-360°)
- `light_saturation` - Color saturation control (0-100%)
- `light_temperature` - Color temperature control (Kelvin)

**Supported Color Modes**:
- `onoff` - Simple on/off
- `brightness` - Dimming only
- `hs` - Hue and saturation (full color) - **Full color control now working!**
- `color_temp` - Color temperature (warm/cool white) - Uses Kelvin scale (2000K-6500K)

**Note**: HS color and color temperature modes are mutually exclusive. If both are available, HS color mode is preferred.

**Color Control**: The integration automatically converts between Home Assistant's color format (hue 0-360°, saturation 0-100%) and Homey's normalized format (0-1). Color changes work reliably for all supported lights, and colors sync correctly on startup by refreshing device state when entities are first added.

## Switches
- `onoff` - On/off control
- `onoff.output1`, `onoff.output2`, etc. - Multi-channel switches (sub-capabilities)

**Multi-Channel Support**: Devices with multiple outputs (e.g., Shelly Plus 2 PM, Fibaro Double Switch) create separate switch entities for each output channel. Each channel gets its own entity with a descriptive name (e.g., "Device Name Output 1", "Device Name Output 2").

**Note**: Devices with dimming or color capabilities are created as lights, not switches.

## Sensors
- `measure_temperature` - Temperature sensor (°C)
- `measure_temperature.inside`, `measure_temperature.outside`, etc. - Sub-capability temperature sensors
- `measure_humidity` - Humidity sensor (%)
- `measure_pressure` - Pressure sensor (hPa)
- `measure_power` - Power consumption sensor (W)
- `measure_power.output1`, `measure_power.output2`, etc. - Multi-channel power sensors
- `measure_voltage` - Voltage sensor (V)
- `measure_current` - Current sensor (A)
- `measure_luminance` - Light level sensor (lux)
- `measure_co2` - CO2 sensor (ppm)
- `measure_co` - CO sensor (ppm)
- `measure_noise` - Sound pressure sensor (dB)
- `measure_rain` - Rainfall sensor (mm)
- `measure_wind_strength` - Wind speed sensor (m/s)
- `measure_wind_angle` - Wind direction sensor (°)
- `measure_ultraviolet` - UV index sensor
- `measure_pm25` - PM2.5 air quality sensor (µg/m³)
- `measure_pm10` - PM10 air quality sensor (µg/m³)
- `measure_voc` - Volatile Organic Compounds sensor (µg/m³)
- `measure_aqi` - Air Quality Index sensor
- `measure_frequency` - Frequency sensor (Hz)
- `measure_gas` - Gas sensor (ppm)
- `measure_soil_moisture` - Soil moisture sensor (%)
- `measure_soil_temperature` - Soil temperature sensor (°C)
- `measure_energy` - Energy consumption sensor (kWh) with proper state class for energy tracking
- `meter_power` - Energy meter (kWh) with `TOTAL_INCREASING` state class - **Energy Dashboard compatible**
- `meter_power.imported` - Imported energy meter (kWh) - **Energy Dashboard compatible**
- `meter_power.exported` - Exported energy meter (kWh) - **Energy Dashboard compatible**
- `meter_power.output1`, `meter_power.output2`, etc. - Multi-channel energy meters - **Energy Dashboard compatible**
- `meter_water` - Water meter (m³) with `TOTAL_INCREASING` state class
- `meter_gas` - Gas meter (m³) with `TOTAL_INCREASING` state class
- `measure_price_total` - Total electricity price (currency/kWh, e.g., SEK/kWh) - **Energy Dashboard compatible**
- `measure_price_lowest` - Lowest electricity price (currency/kWh)
- `measure_price_highest` - Highest electricity price (currency/kWh)
- `accumulatedCost` - Accumulated energy cost (currency, e.g., SEK) - Auto-detects currency from price sensors

**Sub-Capability Support**: The integration fully supports sub-capabilities (capabilities with dots, e.g., `measure_temperature.inside`, `measure_power.output1`). Each sub-capability creates its own sensor entity with a descriptive name.

**Energy Dashboard Compatibility**: All energy sensors (`meter_power` and sub-capabilities) are configured with proper `device_class: energy` and `state_class: total_increasing` for Home Assistant's Energy dashboard. This allows you to track individual device energy consumption in the Energy dashboard.

**Generic Sensor Support**: The integration automatically creates sensor entities for ANY `measure_*` or `meter_*` capability, even if not explicitly listed above. This ensures support for new device types and capabilities without code changes.

## Binary Sensors
- `alarm_motion` - Motion detector
- `alarm_contact` - Door/window contact sensor
- `alarm_tamper` - Tamper sensor
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
- `thermofloor_onoff` - Thermostat heating active/idle status (read-only status indicator)

**Generic Binary Sensor Support**: The integration automatically creates binary sensor entities for ANY boolean-type capability, not just `alarm_*` capabilities. This includes device-specific boolean capabilities like `circulation_pump`, `comfort_program`, `eco_program`, `hot_water`, `compressor_active`, etc.

## Covers
- `windowcoverings_state` - Window covering position (0-100%)
- `windowcoverings_set` - Alternative window covering position capability (some devices use this instead of `windowcoverings_state`)
- `windowcoverings_tilt_up` / `windowcoverings_tilt_down` - Tilt control
- `garagedoor_closed` - Garage door state (open/closed)

**Note**: The integration supports both `windowcoverings_state` and `windowcoverings_set` capabilities. Devices using either capability will be correctly detected as covers.

## Climate
- `target_temperature` - Target temperature control (°C)
- `target_humidity` - Target humidity control (%)
- `measure_temperature` - Current temperature reading (°C)
- `measure_humidity` - Current humidity reading (%)
- `thermostat_mode` - HVAC mode control (off, heat, cool, auto)
- `thermostat_mode_off` - Off mode capability
- `thermostat_mode_heat` - Heat mode capability
- `thermostat_mode_cool` - Cool mode capability
- `thermostat_mode_auto` - Auto mode capability
- `thermofloor_mode` - Custom thermostat mode (e.g., ThermoFloor: Heat, Energy Save Heat, Off, Cool)
- `*_mode` - Any custom enum capability ending with `_mode` is automatically detected and supported

**Supported HVAC Modes**: OFF, HEAT, COOL, AUTO, HEAT_COOL (automatically detected based on available capabilities)

**Custom Thermostat Support**: The integration automatically detects and supports custom thermostat mode capabilities (e.g., `thermofloor_mode`). Custom mode values are mapped to standard HVAC modes:
- "Off" → OFF
- "Heat" → HEAT
- "Cool" → COOL
- "Energy Save Heat" / "Auto" → AUTO

**Turn On/Off Support**: Climate entities support `turn_on` and `turn_off` actions:
- If device has a settable `onoff` capability, it's used for control
- Otherwise, `turn_on` sets to first non-OFF mode, `turn_off` sets to OFF mode

## Fans
- `fan_speed` - Fan speed control (0-100%)
- `onoff` - On/off control

## Locks
- `locked` - Lock state and control

## Media Players
- `volume_set` - Volume control (0-100%)
- `volume_mute` - Mute control
- `speaker_playing` - Play/pause control
- `speaker_next` - Next track control
- `speaker_prev` - Previous track control
- `speaker_artist` - Current artist name
- `speaker_album` - Current album name
- `speaker_track` - Current track title
- `speaker_duration` - Track duration (seconds)
- `speaker_position` - Current playback position (seconds)
- `speaker_shuffle` - Shuffle state
- `speaker_repeat` - Repeat state

## Scenes
- All Homey scenes appear as Scene entities
- Activate scenes directly from Home Assistant

## Moods
- All Homey moods appear as Scene entities (with distinct icon)
- Activate moods directly from Home Assistant

## Buttons
- `button` - Virtual button (Homey Virtual Devices) or single button device
- `button.1`, `button.2`, etc. - Multi-button devices
- Physical device buttons appear as Button entities for automation triggers
- Device-specific buttons (e.g., `gardena_button.park`, `gardena_button.start`) are automatically detected

## Select Entities
- **Generic Enum Support**: Automatically creates select entities for ANY enum-type capability
- `thermofloor_mode` - Thermostat mode selection (Heat, Energy Save Heat, Off, Cool)
- `measure_price_level` - Price level selection (e.g., VERY_CHEAP, CHEAP, NORMAL, EXPENSIVE)
- `measure_price_info_level` - Price info level selection
- `price_level` - Price level indicator
- `operating_program` - Heat pump operating program
- Any capability with `values` or `options` (enum type) is automatically created as a select entity

**Note**: Enum capabilities are automatically detected and converted to select entities. This ensures support for new device types and capabilities without code changes.

## Number Entities
- Any numeric capability that's settable and not handled by another platform
- `target_temperature.*` sub-capabilities (normal, comfort, reduced, dhw, dhw2) for heat pumps
- Pattern-based detection for numeric sub-capabilities

## Vacuum Cleaners
- `class: "vacuumcleaner"` - Full vacuum cleaner support

**Vacuum Entity Features**:
- `clean_full` - Start cleaning (all rooms)
- `pause_clean` - Pause/resume cleaning
- `dock` - Return to dock
- `suction_power` - Fan speed control (select entity)
- `is_cleaning` - Cleaning state detection
- `measure_battery` - Battery level (%)
- `battery_charging_state` - Charging state (charging/discharging/idle)

**Vacuum Sensors**:
- `clean_time` - Cleaning time (hours)
- `clean_area` - Cleaning area (m²)
- `clean_last` - Last cleaning task (hours ago)
- `position_x` / `position_y` - Vacuum position coordinates

**Vacuum Binary Sensors**:
- `alarm_problem` - Problem detected
- `alarm_stuck` - Vacuum stuck
- `alarm_battery` - Low battery alarm
- `water_box_attached` - Water box attached
- `mop_attached` - Mop attached
- `mop_dry_status` - Mop drying status

**Vacuum Select Entities**:
- `suction_power` - Vacuum intensity (quiet, balanced, turbo, max, off, max+)
- `clean_mode` - Clean mode (vacuum & mop, vacuum only, mop only)
- `mop_route` - Mop route (standard, deep, deep+, fast)
- `scrub_intensity` - Mop intensity (off, mild, moderate, intense)
- `active_map` - Active map selection

## Battery Devices
- `class: "battery"` - Battery storage systems

**Battery Sensors**:
- `measure_battery` - Battery level (%)
- `measure_capacity` - Battery capacity (kWh)
- `measure_voltage` - Battery voltage (V)
- `measure_temperature` - Battery temperature (°C)
- `measure_temperature_max` / `measure_temperature_min` - Cell temperature range (°C)
- `measure_power` - Current power (W)
- `meter_power.charged` - Total energy charged (kWh) - **Energy Dashboard compatible**
- `meter_power.discharged` - Total energy discharged (kWh) - **Energy Dashboard compatible**
- `measure_max_charging_power` - Max charging power (W)
- `measure_max_discharging_power` - Max discharging power (W)
- `measure_emergency_power_reserve` - Emergency reserve (Wh/kWh)
- `measure_dcbcount` - Module count

**Energy Dashboard Compatibility**: Battery energy sensors (`meter_power.charged`, `meter_power.discharged`) are configured for Home Assistant's Energy dashboard.

## Lawn Mowers
- `class: "other"` with Gardena capabilities - Lawn mower support

**Lawn Mower Buttons**:
- `gardena_button.park` - Park the mower
- `gardena_button.start` - Start mowing

**Lawn Mower Sensors**:
- `measure_battery` - Battery level (%)
- `gardena_wireless_quality` - Wireless signal quality (%)
- `gardena_mower_state` - Mower state (string)
- `gardena_operating_hours` - Operating hours

**Note**: Generic button pattern matching supports device-specific buttons like `gardena_button.*`.

## Heat Pumps
- `class: "heatpump"` - Heat pump support

**Heat Pump Climate Entity**:
- `target_temperature` - Main target temperature control (°C)
- `thermostat_mode` - HVAC mode (dhw, dhwAndHeating, standby)
- `measure_temperature` - Current temperature (°C)
- All `measure_temperature.*` sub-capabilities (normal, comfort, reduced, outside, supply, dhw, dhw_outlet, return, dhw_top, dhw_bottom)

**Heat Pump Number Entities**:
- `target_temperature.normal` - Day temperature target (°C)
- `target_temperature.comfort` - Comfort temperature target (°C)
- `target_temperature.reduced` - Night temperature target (°C)
- `target_temperature.dhw` - Hot water temperature target (°C)
- `target_temperature.dhw2` - Hot water temperature 2 target (°C)

**Heat Pump Select Entities**:
- `operating_program` - Heating program (comfort, eco, fixed, normal, reduced, heatpump, standby)

**Heat Pump Binary Sensors**:
- `circulation_pump` - Circulation pump status
- `comfort_program` - Comfort program active
- `eco_program` - Eco program active
- `hot_water` - Hot water heating active
- `compressor_active` - Compressor running

**Heat Pump Sensors**:
- `compressor_hours` - Compressor operating hours
- `compressor_starts` - Compressor start count

## Solar Panels
- `class: "solarpanel"` - Solar panel/inverter support

**Solar Panel Sensors**:
- `measure_power` - Current power generation (W)
- `meter_power` - Total energy generated (kWh) - **Energy Dashboard compatible**
- `measure_grid_delivery` - Grid power delivery (W)
- `measure_battery_delivery` - Battery power delivery (W)
- `measure_house_consumption` - House consumption (W)
- `measure_battery` - Battery level (%)
- `firmware_version` - Firmware version (string)
- `charge_time` - Charge/discharge time estimate (string)

**Solar Panel Binary Sensors**:
- `external_power_delivery_connected` - External power source connected

**Energy Dashboard Compatibility**: Solar panel energy sensors (`meter_power`) are configured for Home Assistant's Energy dashboard.

---

## Generic Capability Support

The integration includes automatic detection for many capability types:

- **Generic Sensors**: Any `measure_*` or `meter_*` capability is automatically created as a sensor
- **Generic Binary Sensors**: Any boolean-type capability is automatically created as a binary sensor (excluding buttons)
- **Generic Select Entities**: Any enum-type capability is automatically created as a select entity
- **Generic Number Entities**: Numeric sub-capabilities (e.g., `target_temperature.*`) are automatically detected

This ensures that new device types and capabilities are supported without requiring code changes.
