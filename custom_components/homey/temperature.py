"""Temperature unit parsing and conversion for Homey capabilities."""
from __future__ import annotations

from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfTemperature
from homeassistant.util.unit_conversion import TemperatureConverter

from .const import CONF_TEMPERATURE_UNIT_OVERRIDES

TEMPERATURE_OVERRIDE_AUTO = "auto"
TEMPERATURE_OVERRIDE_CELSIUS = "celsius"
TEMPERATURE_OVERRIDE_FAHRENHEIT = "fahrenheit"


def parse_homey_temperature_unit(units: str | None) -> str | None:
    """Parse a Homey capability ``units`` string into an HA temperature unit."""
    if not units:
        return None
    normalized = units.strip().replace("°", "").upper()
    if normalized in ("F", "FAHRENHEIT"):
        return UnitOfTemperature.FAHRENHEIT
    if normalized in ("C", "CELSIUS"):
        return UnitOfTemperature.CELSIUS
    return None


def normalize_temperature_override(value: str | None) -> str | None:
    """Normalize a user override to celsius/fahrenheit, or None for automatic."""
    if not value:
        return None
    normalized = value.strip().lower()
    if normalized in (TEMPERATURE_OVERRIDE_AUTO, "automatic", "homey"):
        return None
    if normalized in (TEMPERATURE_OVERRIDE_CELSIUS, "c", "°c"):
        return UnitOfTemperature.CELSIUS
    if normalized in (TEMPERATURE_OVERRIDE_FAHRENHEIT, "f", "°f"):
        return UnitOfTemperature.FAHRENHEIT
    return None


def resolve_temperature_unit(*capability_data: dict[str, Any]) -> str:
    """Resolve unit from Homey capability metadata only (no guessing)."""
    for cap_data in capability_data:
        if not cap_data:
            continue
        declared = parse_homey_temperature_unit(cap_data.get("units"))
        if declared:
            return declared
    return UnitOfTemperature.CELSIUS


def get_device_temperature_unit(
    config_entry: ConfigEntry,
    device_id: str,
    *capability_data: dict[str, Any],
) -> str:
    """Unit for values from Homey: user override, else capability ``units``, else °C."""
    overrides = config_entry.options.get(CONF_TEMPERATURE_UNIT_OVERRIDES, {})
    override = normalize_temperature_override(overrides.get(device_id))
    if override:
        return override
    return resolve_temperature_unit(*capability_data)


def convert_temperature(value: float, from_unit: str, to_unit: str) -> float:
    """Convert a temperature between HA unit constants."""
    if from_unit == to_unit:
        return value
    return TemperatureConverter.convert(value, from_unit, to_unit)


def to_homey_temperature(
    value: float, homey_unit: str, source_unit: str
) -> float:
    """Convert a temperature into the unit expected by the Homey device."""
    return convert_temperature(value, source_unit, homey_unit)


def from_homey_temperature(
    value: float, homey_unit: str, target_unit: str
) -> float:
    """Convert a Homey temperature reading into the target unit."""
    return convert_temperature(value, homey_unit, target_unit)
