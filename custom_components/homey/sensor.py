"""Support for Homey sensors."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    UnitOfEnergy,
    UnitOfPower,
    UnitOfPressure,
    UnitOfTemperature,
    UnitOfFrequency,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    CONF_EXPOSE_READONLY_STRINGS,
    CONF_EXPOSE_SETTABLE_TEXT,
    CONF_USE_CAPABILITY_TITLES,
    DEFAULT_EXPOSE_READONLY_STRINGS,
    DEFAULT_EXPOSE_SETTABLE_TEXT,
    DOMAIN,
)
from .coordinator import HomeyDataUpdateCoordinator
from .device_info import build_entity_unique_id, get_device_info

_LOGGER = logging.getLogger(__name__)

# Mapping of Homey capabilities to HA sensor attributes
CAPABILITY_TO_SENSOR = {
    "measure_temperature": {
        "device_class": SensorDeviceClass.TEMPERATURE,
        "state_class": SensorStateClass.MEASUREMENT,
        "unit": UnitOfTemperature.CELSIUS,
    },
    "measure_humidity": {
        "device_class": SensorDeviceClass.HUMIDITY,
        "state_class": SensorStateClass.MEASUREMENT,
        "unit": "%",
    },
    "measure_pressure": {
        "device_class": SensorDeviceClass.PRESSURE,
        "state_class": SensorStateClass.MEASUREMENT,
        "unit": UnitOfPressure.HPA,
    },
    "measure_power": {
        "device_class": SensorDeviceClass.POWER,
        "state_class": SensorStateClass.MEASUREMENT,
        "unit": UnitOfPower.WATT,
    },
    "measure_voltage": {
        "device_class": SensorDeviceClass.VOLTAGE,
        "state_class": SensorStateClass.MEASUREMENT,
        "unit": "V",  # Volts - UnitOfVoltage may not be available in all HA versions
    },
    "measure_current": {
        "device_class": SensorDeviceClass.CURRENT,
        "state_class": SensorStateClass.MEASUREMENT,
        "unit": "A",
    },
    "measure_luminance": {
        "device_class": SensorDeviceClass.ILLUMINANCE,
        "state_class": SensorStateClass.MEASUREMENT,
        "unit": "lx",
    },
    "measure_co2": {
        "device_class": SensorDeviceClass.CO2,
        "state_class": SensorStateClass.MEASUREMENT,
        "unit": "ppm",
    },
    "measure_co": {
        "device_class": SensorDeviceClass.CO,
        "state_class": SensorStateClass.MEASUREMENT,
        "unit": "ppm",
    },
    "measure_distance": {
        "device_class": SensorDeviceClass.DISTANCE,
        "state_class": SensorStateClass.MEASUREMENT,
        "unit": "cm",  # Common for ultrasonic/ToF presence sensors
    },
    # Additional sensor capabilities
    "measure_noise": {
        "device_class": SensorDeviceClass.SOUND_PRESSURE,
        "state_class": SensorStateClass.MEASUREMENT,
        "unit": "dB",
    },
    "measure_rain": {
        "device_class": None,  # Generic sensor
        "state_class": SensorStateClass.MEASUREMENT,
        "unit": "mm",
    },
    "measure_wind_strength": {
        "device_class": None,  # Generic sensor
        "state_class": SensorStateClass.MEASUREMENT,
        "unit": "m/s",
    },
    "measure_wind_angle": {
        "device_class": None,  # Generic sensor
        "state_class": SensorStateClass.MEASUREMENT,
        "unit": "°",
    },
    "measure_ultraviolet": {
        "device_class": None,  # Generic sensor
        "state_class": SensorStateClass.MEASUREMENT,
        "unit": "UV index",
    },
    "measure_pm25": {
        "device_class": SensorDeviceClass.PM25,
        "state_class": SensorStateClass.MEASUREMENT,
        "unit": "µg/m³",
    },
    "measure_pm10": {
        "device_class": SensorDeviceClass.PM10,
        "state_class": SensorStateClass.MEASUREMENT,
        "unit": "µg/m³",
    },
    "measure_voc": {
        "device_class": None,  # Generic sensor
        "state_class": SensorStateClass.MEASUREMENT,
        "unit": "µg/m³",
    },
    "measure_aqi": {
        "device_class": None,  # Generic sensor
        "state_class": SensorStateClass.MEASUREMENT,
        "unit": "AQI",
    },
    "measure_frequency": {
        "device_class": None,  # Generic sensor
        "state_class": SensorStateClass.MEASUREMENT,
        "unit": UnitOfFrequency.HERTZ,
    },
    "measure_gas": {
        "device_class": None,  # Generic sensor
        "state_class": SensorStateClass.MEASUREMENT,
        "unit": "ppm",
    },
    "measure_soil_moisture": {
        "device_class": SensorDeviceClass.MOISTURE,
        "state_class": SensorStateClass.MEASUREMENT,
        "unit": "%",
    },
    "measure_moisture": {
        "device_class": SensorDeviceClass.MOISTURE,
        "state_class": SensorStateClass.MEASUREMENT,
        "unit": "%",
    },
    "measure_soil_temperature": {
        "device_class": SensorDeviceClass.TEMPERATURE,
        "state_class": SensorStateClass.MEASUREMENT,
        "unit": UnitOfTemperature.CELSIUS,
    },
    "measure_energy": {
        "device_class": SensorDeviceClass.ENERGY,
        "state_class": SensorStateClass.TOTAL_INCREASING,  # For energy consumption
        "unit": UnitOfEnergy.KILO_WATT_HOUR,
    },
    # Meter capabilities (energy/utility meters)
    # Reference: https://apps.developer.homey.app/the-basics/devices/capabilities
    "meter_power": {
        "device_class": SensorDeviceClass.ENERGY,
        "state_class": SensorStateClass.TOTAL_INCREASING,  # Cumulative energy consumption
        "unit": UnitOfEnergy.KILO_WATT_HOUR,
    },
    "meter_water": {
        "device_class": None,  # Generic sensor - water meter
        "state_class": SensorStateClass.TOTAL_INCREASING,  # Cumulative water consumption
        "unit": "m³",  # Cubic meters
    },
    "meter_gas": {
        "device_class": None,  # Generic sensor - gas meter
        "state_class": SensorStateClass.TOTAL_INCREASING,  # Cumulative gas consumption
        "unit": "m³",  # Cubic meters
    },
    # Additional measure_* capabilities that might exist
    "measure_battery": {
        "device_class": SensorDeviceClass.BATTERY,
        "state_class": SensorStateClass.MEASUREMENT,
        "unit": "%",
    },
    # Battery-specific capabilities
    "measure_capacity": {
        "device_class": SensorDeviceClass.ENERGY,  # Battery capacity in kWh
        "state_class": SensorStateClass.MEASUREMENT,
        "unit": UnitOfEnergy.KILO_WATT_HOUR,
    },
    "measure_max_charging_power": {
        "device_class": SensorDeviceClass.POWER,
        "state_class": SensorStateClass.MEASUREMENT,
        "unit": UnitOfPower.WATT,
    },
    "measure_max_discharging_power": {
        "device_class": SensorDeviceClass.POWER,
        "state_class": SensorStateClass.MEASUREMENT,
        "unit": UnitOfPower.WATT,
    },
    "measure_emergency_power_reserve": {
        "device_class": SensorDeviceClass.ENERGY,  # Emergency reserve in Wh/kWh
        "state_class": SensorStateClass.MEASUREMENT,
        "unit": None,  # Will use unit from capability data (Wh or kWh)
    },
    "measure_wind_speed": {  # Alternative name for wind_strength
        "device_class": None,
        "state_class": SensorStateClass.MEASUREMENT,
        "unit": "m/s",
    },
    "measure_wind_direction": {  # Alternative name for wind_angle
        "device_class": None,
        "state_class": SensorStateClass.MEASUREMENT,
        "unit": "°",
    },
    "measure_light": {  # Alternative name for luminance
        "device_class": SensorDeviceClass.ILLUMINANCE,
        "state_class": SensorStateClass.MEASUREMENT,
        "unit": "lx",
    },
    "measure_illuminance": {  # Alternative name for luminance
        "device_class": SensorDeviceClass.ILLUMINANCE,
        "state_class": SensorStateClass.MEASUREMENT,
        "unit": "lx",
    },
    # Tibber price sensors
    "measure_price_level": {
        "device_class": None,  # Price level (low/normal/high)
        "state_class": SensorStateClass.MEASUREMENT,
        "unit": None,  # Unitless - just a level indicator
    },
    "measure_price_info_level": {
        "device_class": None,  # Price info level
        "state_class": SensorStateClass.MEASUREMENT,
        "unit": None,  # Unitless
    },
    "measure_price_lowest": {
        "device_class": None,  # Lowest price
        "state_class": SensorStateClass.MEASUREMENT,
        "unit": None,  # Will be set from capability data (e.g., SEK/kWh)
    },
    "measure_price_highest": {
        "device_class": None,  # Highest price
        "state_class": SensorStateClass.MEASUREMENT,
        "unit": None,  # Will be set from capability data (e.g., SEK/kWh)
    },
    "measure_price_total": {
        "device_class": None,  # Total price
        "state_class": SensorStateClass.MEASUREMENT,
        "unit": None,  # Will be set from capability data (e.g., SEK/kWh)
    },
    # Tibber cost/energy sensors
    "accumulatedCost": {
        "device_class": None,  # Accumulated cost
        "state_class": SensorStateClass.TOTAL_INCREASING,  # Cumulative cost
        "unit": None,  # Will be set from capability data (e.g., SEK, ¤)
    },
    # Heat pump / compressor counters
    "compressor_hours": {
        "device_class": None,
        "state_class": SensorStateClass.TOTAL_INCREASING,
        "unit": "h",
    },
    "compressor_starts": {
        "device_class": None,
        "state_class": SensorStateClass.TOTAL_INCREASING,
        "unit": None,
    },
}

# Capabilities to exclude from generic sensor creation
# (handled by other platforms or noisy/duplicate)
GENERIC_SENSOR_EXCLUDE = {
    "device_name",
    "dim",
    "onoff",
    "light_hue",
    "light_saturation",
    "light_temperature",
    "target_temperature",
    "target_humidity",
    "thermostat_mode",
    "windowcoverings_state",
    "windowcoverings_set",
    "garagedoor_closed",
    "locked",
    "fan_speed",
    "volume_set",
    "speaker_playing",
    "speaker_next",
    "speaker_prev",
    "speaker_shuffle",
    "speaker_repeat",
    "clean_time",
    "clean_area",
    "clean_last",
    "position_x",
    "position_y",
}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Homey sensors from a config entry."""
    coordinator: HomeyDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    api = hass.data[DOMAIN][entry.entry_id]["api"]
    zones = hass.data[DOMAIN][entry.entry_id].get("zones", {})
    multi_homey = hass.data[DOMAIN][entry.entry_id].get("multi_homey", False)
    homey_id = hass.data[DOMAIN][entry.entry_id].get("homey_id")

    entities = []
    expose_readonly_strings = entry.options.get(
        CONF_EXPOSE_READONLY_STRINGS,
        entry.data.get(CONF_EXPOSE_READONLY_STRINGS, DEFAULT_EXPOSE_READONLY_STRINGS),
    )
    expose_settable_text = entry.options.get(
        CONF_EXPOSE_SETTABLE_TEXT,
        entry.data.get(CONF_EXPOSE_SETTABLE_TEXT, DEFAULT_EXPOSE_SETTABLE_TEXT),
    )
    use_titles = entry.options.get(
        CONF_USE_CAPABILITY_TITLES, entry.data.get(CONF_USE_CAPABILITY_TITLES)
    )
    # Use coordinator data if available (more up-to-date), otherwise fetch fresh
    devices = coordinator.data if coordinator.data else await api.get_devices()
    
    # Filter devices if device_filter is configured
    from . import filter_devices
    devices = filter_devices(devices, entry.data.get("device_filter"))
    
    # Track devicegroups groups we've logged (to avoid logging multiple times per device)
    logged_devicegroups = set()

    for device_id, device in devices.items():
        capabilities = device.get("capabilitiesObj", {})
        driver_id = device.get("driverId", "")
        device_name = device.get("name", "Unknown")
        device_class = device.get("class", "")
        
        # Check if this is a devicegroups group (log once per device, not per capability)
        is_devicegroups_group = driver_id.startswith("homey:app:com.swttt.devicegroups:")
        if is_devicegroups_group and device_id not in logged_devicegroups:
            logged_devicegroups.add(device_id)
            _LOGGER.debug(
                "Found devicegroups group in sensor platform: %s (id: %s, class: %s, driverId: %s, capabilities: %s)",
                device_name,
                device_id,
                device_class,
                driver_id,
                list(capabilities.keys())
            )
        
        # First, handle explicitly mapped capabilities
        for capability_id in CAPABILITY_TO_SENSOR:
            if capability_id in capabilities:
                entities.append(
                    HomeySensor(
                        coordinator,
                        device_id,
                        device,
                        capability_id,
                        api,
                        zones,
                        homey_id,
                        multi_homey,
                        use_titles,
                    )
                )
        
        # Then, handle ALL measure_* and meter_* capabilities generically (including unknown ones)
        # This ensures we support new device types and capabilities automatically
        # Reference: https://apps.developer.homey.app/the-basics/devices/capabilities#sub-capabilities-using-the-same-capability-more-than-once
        for capability_id in capabilities:
            # Skip if already handled above
            if capability_id in CAPABILITY_TO_SENSOR:
                continue
            
            # Skip enum-type capabilities - they should be select entities, not sensors
            cap_data = capabilities.get(capability_id, {})
            if cap_data.get("type") == "enum":
                _LOGGER.debug("Skipping enum capability %s - should be handled by select platform", capability_id)
                continue
            
            # Check if this is a measure_* or meter_* capability (including sub-capabilities)
            # Also handle vacuum-specific capabilities: clean_time, clean_area, clean_last, position_x, position_y
            is_measure = capability_id.startswith("measure_")
            is_meter = capability_id.startswith("meter_")
            is_accumulated_cost = capability_id == "accumulatedCost"
            is_vacuum_sensor = capability_id in ["clean_time", "clean_area", "clean_last", "position_x", "position_y"]
            
            if is_measure or is_meter or is_accumulated_cost or is_vacuum_sensor:
                # Skip internal Homey maintenance buttons (same logic as button.py)
                capability_lower = capability_id.lower()
                if any(keyword in capability_lower for keyword in ["migrate", "reset", "identify"]):
                    _LOGGER.debug("Skipping internal Homey maintenance capability: %s", capability_id)
                    continue
                
                # Check if it's a sub-capability of a known capability
                if "." in capability_id:
                    base_capability = capability_id.split(".")[0]
                    # If base is known, use its config; otherwise create generic sensor
                    if base_capability in CAPABILITY_TO_SENSOR:
                        entities.append(
                            HomeySensor(
                                coordinator,
                                device_id,
                                device,
                                capability_id,
                                api,
                                zones,
                                homey_id,
                                multi_homey,
                                use_titles,
                            )
                        )
                    else:
                        # Unknown base capability - create generic sensor
                        entities.append(
                            HomeySensor(
                                coordinator,
                                device_id,
                                device,
                                capability_id,
                                api,
                                zones,
                                homey_id,
                                multi_homey,
                                use_titles,
                            )
                        )
                else:
                    # Unknown top-level capability - create generic sensor
                    entities.append(
                        HomeySensor(
                            coordinator,
                            device_id,
                            device,
                            capability_id,
                            api,
                            zones,
                            homey_id,
                            multi_homey,
                            use_titles,
                        )
                    )

        # Finally, handle other getable, non-setable numeric/string capabilities
        # This covers counters and informational fields like firmware_version or charge_time
        for capability_id, cap_data in capabilities.items():
            # Skip if already handled or explicitly excluded
            if capability_id in CAPABILITY_TO_SENSOR or capability_id in GENERIC_SENSOR_EXCLUDE:
                continue
            # Skip measure_*, meter_*, etc. - already handled in loop 2 above
            if (
                capability_id.startswith("measure_")
                or capability_id.startswith("meter_")
                or capability_id == "accumulatedCost"
                or capability_id in ("clean_time", "clean_area", "clean_last", "position_x", "position_y")
            ):
                continue

            cap_type = cap_data.get("type")
            is_getable = cap_data.get("getable", False)
            is_setable = cap_data.get("setable", False)

            # Skip if not a readable capability
            if not is_getable:
                continue

            # Skip settable values unless explicitly exposed as read-only strings
            if is_setable:
                if not expose_readonly_strings or cap_type != "string" or expose_settable_text:
                    continue

            # Skip enums (handled by select)
            if cap_type == "enum":
                continue

            # Only create for numeric or string data
            if cap_type in ("number", "string"):
                if cap_type == "string" and ("values" in cap_data or "options" in cap_data):
                    continue
                entities.append(
                    HomeySensor(
                        coordinator,
                        device_id,
                        device,
                        capability_id,
                        api,
                        zones,
                        homey_id,
                        multi_homey,
                        use_titles,
                    )
                )

    # Deduplicate by unique_id (prevents "Platform does not generate unique IDs" errors)
    seen_ids: set[str] = set()
    deduped: list[HomeySensor] = []
    for e in entities:
        if e.unique_id in seen_ids:
            continue
        seen_ids.add(e.unique_id)
        deduped.append(e)

    async_add_entities(deduped)


class HomeySensor(CoordinatorEntity, SensorEntity):
    """Representation of a Homey sensor."""

    def __init__(
        self,
        coordinator: HomeyDataUpdateCoordinator,
        device_id: str,
        device: dict[str, Any],
        capability_id: str,
        api,
        zones: dict[str, dict[str, Any]] | None = None,
        homey_id: str | None = None,
        multi_homey: bool = False,
        use_titles: bool | None = None,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._device_id = device_id
        self._device = device
        self._capability_id = capability_id
        self._api = api
        self._homey_id = homey_id
        self._multi_homey = multi_homey
        self._capability_type = device.get("capabilitiesObj", {}).get(capability_id, {}).get("type")

        # Handle sub-capabilities (e.g., measure_temperature.inside, meter_power.imported)
        base_capability = capability_id.split(".")[0] if "." in capability_id else capability_id
        sensor_config = CAPABILITY_TO_SENSOR.get(base_capability)
        
        if not sensor_config:
            # Unknown capability - create generic sensor
            # This is expected behavior - we create sensors for all measure_* and meter_* capabilities
            _LOGGER.debug("Creating generic sensor for unknown capability: %s for device %s", capability_id, device_id)
            
            # Special handling for meter_* sub-capabilities (e.g., meter_power.imported, meter_power.exported)
            # These should be energy sensors for Energy dashboard compatibility
            if base_capability == "meter_power":
                sensor_config = {
                    "device_class": SensorDeviceClass.ENERGY,
                    "state_class": SensorStateClass.TOTAL_INCREASING,  # Cumulative energy
                    "unit": UnitOfEnergy.KILO_WATT_HOUR,
                }
            else:
                sensor_config = {
                    "device_class": None,
                    "state_class": SensorStateClass.MEASUREMENT,
                    "unit": None,
                }
        
        capability_data = device.get("capabilitiesObj", {}).get(capability_id, {})
        # Generate entity name - handle sub-capabilities
        if use_titles is True and capability_data.get("title"):
            self._attr_name = f"{device.get('name', 'Unknown')} {capability_data.get('title')}"
        elif "." in capability_id:
            # Sub-capability: "measure_temperature.inside" -> "Inside Temperature"
            parts = capability_id.split(".")
            base_cap = parts[0]
            # Special handling: meter_power should be labeled as "Energy", not "Power"
            if base_cap == "meter_power":
                base_name = "Energy"
            else:
                base_name = base_cap.replace("measure_", "").replace("meter_", "").replace("_", " ").title()
            sub_name = parts[1].replace("_", " ").title()
            self._attr_name = f"{device.get('name', 'Unknown')} {sub_name} {base_name}"
        else:
            # Regular capability
            # Special handling: meter_power should be labeled as "Energy", not "Power"
            if capability_id == "meter_power":
                display_name = "Energy"
            else:
                display_name = capability_id.replace("measure_", "").replace("meter_", "").replace("_", " ").title()
            self._attr_name = f"{device.get('name', 'Unknown')} {display_name}"
        
        self._attr_unique_id = build_entity_unique_id(
            homey_id, device_id, capability_id, multi_homey
        )
        self._attr_device_class = sensor_config.get("device_class")
        self._attr_state_class = sensor_config.get("state_class")
        self._attr_native_unit_of_measurement: str | None = None
        
        # Get unit from capability data if available (important for price sensors, etc.)
        # This ensures sensors like Tibber price sensors get their units (e.g., SEK/kWh) from Homey
        capabilities = device.get("capabilitiesObj", {})
        capability_data = capabilities.get(capability_id, {})
        unit_from_capability = capability_data.get("units")
        
        # Check if this is a price sensor that needs energy price format (currency/kWh)
        is_price_sensor = capability_id in ["measure_price_total", "measure_price_lowest", "measure_price_highest"]
        # Check if this is an accumulated cost sensor that needs currency code (not symbol)
        is_accumulated_cost = capability_id == "accumulatedCost"
        
        # Use unit from capability data if available, otherwise use configured unit
        if unit_from_capability:
            if is_price_sensor:
                # Convert currency symbol to currency code + /kWh format for Energy dashboard
                unit_normalized = self._normalize_price_unit(unit_from_capability)
                self._attr_native_unit_of_measurement = unit_normalized
            elif is_accumulated_cost:
                # Try to detect currency from other price sensors on the same device first
                detected_currency = self._detect_currency_from_device(device, capabilities)
                if detected_currency:
                    # Use detected currency from price sensors
                    self._attr_native_unit_of_measurement = detected_currency
                else:
                    # Only normalize if we have a specific currency symbol (not generic "¤")
                    # If it's "¤" or unknown, leave unit empty so user can customize it
                    if unit_from_capability and unit_from_capability.strip() != "¤":
                        unit_normalized = self._normalize_currency_unit(unit_from_capability)
                        # Only set if we got a valid currency code (not the generic fallback)
                        if len(unit_normalized) == 3 and unit_normalized.isalpha() and unit_normalized.isupper():
                            self._attr_native_unit_of_measurement = unit_normalized
                        else:
                            # Unknown currency, leave empty
                            self._attr_native_unit_of_measurement = None
                    else:
                        # Generic currency symbol or no unit - leave empty for user customization
                        self._attr_native_unit_of_measurement = None
            elif self._attr_device_class == SensorDeviceClass.ENERGY:
                # For energy sensors, ensure unit is compatible with Energy dashboard
                # Accept kWh, Wh, or other energy units
                unit_lower = unit_from_capability.lower()
                if "kwh" in unit_lower:
                    # Already in kWh - use as is
                    self._attr_native_unit_of_measurement = unit_from_capability
                elif "wh" in unit_lower and "kwh" not in unit_lower:
                    # Wh (watt-hours) - use as is (Home Assistant supports Wh)
                    self._attr_native_unit_of_measurement = unit_from_capability
                elif base_capability == "meter_power":
                    # meter_power.* defaults to kWh for Energy dashboard compatibility
                    self._attr_native_unit_of_measurement = UnitOfEnergy.KILO_WATT_HOUR
                else:
                    # Other energy sensors - use unit from capability
                    self._attr_native_unit_of_measurement = unit_from_capability
            else:
                self._attr_native_unit_of_measurement = unit_from_capability
        else:
            self._attr_native_unit_of_measurement = sensor_config.get("unit")

        # String sensors should not report a numeric state class or units
        if self._capability_type == "string":
            self._attr_state_class = None
            self._attr_device_class = None
            self._attr_native_unit_of_measurement = None

        self._attr_device_info = get_device_info(
            self._homey_id, device_id, device, zones, self._multi_homey
        )
    
    def _normalize_price_unit(self, unit: str) -> str:
        """Normalize price sensor units to currency/kWh format for Home Assistant Energy dashboard.
        
        Converts currency symbols to currency codes and appends /kWh.
        Examples:
        - "¤" -> "SEK/kWh" (generic currency symbol, default to SEK)
        - "€" -> "EUR/kWh"
        - "$" -> "USD/kWh"
        - "kr" -> "SEK/kWh" (Swedish/Norwegian/Danish krone)
        - "SEK" -> "SEK/kWh" (already a code)
        - "SEK/kWh" -> "SEK/kWh" (already formatted)
        """
        if not unit:
            return "SEK/kWh"  # Default fallback
        
        unit = unit.strip()
        
        # If already in currency/kWh format, return as-is
        if "/kWh" in unit or "/Wh" in unit:
            return unit
        
        # Map currency symbols to currency codes
        currency_map = {
            "¤": "SEK",  # Generic currency symbol - default to SEK (common for Tibber users)
            "€": "EUR",
            "$": "USD",
            "£": "GBP",
            "¥": "JPY",
            "kr": "SEK",  # Swedish/Norwegian/Danish krone
            "SEK": "SEK",
            "EUR": "EUR",
            "USD": "USD",
            "GBP": "GBP",
            "NOK": "NOK",
            "DKK": "DKK",
        }
        
        # Convert symbol to code
        currency_code = currency_map.get(unit, unit.upper())
        
        # Append /kWh for Energy dashboard compatibility
        return f"{currency_code}/kWh"
    
    def _normalize_currency_unit(self, unit: str) -> str:
        """Normalize currency units by converting symbols to currency codes.
        
        Converts currency symbols to currency codes for better display in Home Assistant.
        Examples:
        - "€" -> "EUR"
        - "$" -> "USD"
        - "kr" -> "SEK" (Swedish/Norwegian/Danish krone)
        - "SEK" -> "SEK" (already a code)
        
        Note: Generic currency symbol "¤" is NOT normalized here - caller should handle it.
        
        Args:
            unit: Currency unit string from Homey (symbol or code)
            
        Returns:
            Currency code (e.g., "EUR", "USD", "SEK") or original unit if unknown
        """
        if not unit:
            return unit
        
        unit = unit.strip()
        
        # Map currency symbols to currency codes (excluding generic "¤")
        currency_map = {
            "€": "EUR",
            "$": "USD",
            "£": "GBP",
            "¥": "JPY",
            "kr": "SEK",  # Swedish/Norwegian/Danish krone
            "SEK": "SEK",
            "EUR": "EUR",
            "USD": "USD",
            "GBP": "GBP",
            "JPY": "JPY",
            "CHF": "CHF",
            "CAD": "CAD",
            "AUD": "AUD",
            "NZD": "NZD",
            "DKK": "DKK",  # Danish krone
            "NOK": "NOK",  # Norwegian krone
            "PLN": "PLN",  # Polish zloty
            "CZK": "CZK",  # Czech koruna
            "HUF": "HUF",  # Hungarian forint
            "RUB": "RUB",  # Russian ruble
            "TRY": "TRY",  # Turkish lira
            "BRL": "BRL",  # Brazilian real
            "MXN": "MXN",  # Mexican peso
            "ZAR": "ZAR",  # South African rand
            "INR": "INR",  # Indian rupee
            "CNY": "CNY",  # Chinese yuan
        }
        
        # Check if the unit is a known currency symbol or code
        if unit in currency_map:
            return currency_map[unit]
        
        # If it's already a 3-letter uppercase code, assume it's valid
        if len(unit) == 3 and unit.isalpha() and unit.isupper():
            return unit
        
        # Fallback: try case-insensitive match
        unit_upper = unit.upper()
        for symbol, code in currency_map.items():
            if symbol.upper() == unit_upper:
                return code
        
        # Final fallback - return as-is if we can't determine
        return unit
    
    def _detect_currency_from_device(self, device: dict[str, Any], capabilities: dict[str, Any]) -> str | None:
        """Detect currency code from other price sensors on the same device.
        
        Looks for measure_price_* sensors on the same device and extracts the currency code
        from their units (e.g., "SEK/kWh" -> "SEK").
        
        Args:
            device: Device dictionary from Homey
            capabilities: Capabilities dictionary from device
            
        Returns:
            Currency code (e.g., "SEK", "EUR", "USD") if detected, None otherwise
        """
        # Check price sensors on the same device
        price_sensor_ids = ["measure_price_total", "measure_price_lowest", "measure_price_highest"]
        
        for price_sensor_id in price_sensor_ids:
            price_capability = capabilities.get(price_sensor_id)
            if price_capability:
                price_unit = price_capability.get("units")
                if price_unit:
                    # Extract currency code from price unit (e.g., "SEK/kWh" -> "SEK")
                    if "/" in price_unit:
                        currency_code = price_unit.split("/")[0].strip()
                        # Validate it's a currency code (3 letters, uppercase)
                        if len(currency_code) == 3 and currency_code.isalpha() and currency_code.isupper():
                            return currency_code
                    # If it's already a currency code without /kWh, use it
                    elif len(price_unit) == 3 and price_unit.isalpha() and price_unit.isupper():
                        return price_unit
                    # Try to normalize it (might be a symbol)
                    else:
                        normalized = self._normalize_currency_unit(price_unit)
                        # If normalization worked and returned a valid code, use it
                        if len(normalized) == 3 and normalized.isalpha() and normalized.isupper():
                            return normalized
        
        return None

    @property
    def native_value(self) -> float | str | None:
        """Return the state of the sensor."""
        device_data = self.coordinator.data.get(self._device_id, self._device)
        capabilities = device_data.get("capabilitiesObj", {})
        capability = capabilities.get(self._capability_id, {})
        value = capability.get("value")
        if value is None:
            return None

        if self._capability_type == "string":
            return str(value)
        
        try:
            value_float = float(value)
            
            # Check if this is a percentage sensor that might be normalized
            # measure_humidity, measure_soil_moisture, measure_moisture,
            # and measure_battery might return normalized 0-1
            base_capability = self._capability_id.split(".")[0] if "." in self._capability_id else self._capability_id
            if base_capability in (
                "measure_humidity",
                "measure_soil_moisture",
                "measure_moisture",
                "measure_battery",
            ):
                # Check capability max to determine if normalized
                cap_max = capability.get("max", 100)
                if cap_max <= 1.0:
                    # Normalized value (0-1), convert to percentage (0-100)
                    value_float = value_float * 100.0
            
            return value_float
        except (ValueError, TypeError):
            return None

