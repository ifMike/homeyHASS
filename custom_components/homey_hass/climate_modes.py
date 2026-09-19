"""Pure Homey climate mode helpers (no Home Assistant imports)."""
from __future__ import annotations

from typing import Any

# Prefer these enum caps over generic *_mode discovery (Nest, etc.).
PREFERRED_MODE_CAPABILITIES = ("nest_thermostat_mode",)

# Read-only HVAC action enums owned by the climate entity.
HVAC_ACTION_CAPABILITIES = ("nest_thermostat_hvac",)

# String values matching homeassistant.components.climate.HVACMode
HVAC_OFF = "off"
HVAC_HEAT = "heat"
HVAC_COOL = "cool"
HVAC_AUTO = "auto"
HVAC_HEAT_COOL = "heat_cool"

# String values matching HVACAction where applicable
ACTION_OFF = "off"
ACTION_IDLE = "idle"
ACTION_HEATING = "heating"
ACTION_COOLING = "cooling"
ACTION_DRYING = "drying"
ACTION_FAN_ONLY = "fan_only"


def extract_mode_id(mode_value: Any) -> str | None:
    """Extract a mode id/title from Homey enum value payloads."""
    if mode_value is None:
        return None
    if isinstance(mode_value, dict):
        extracted = mode_value.get("id", mode_value.get("title", mode_value))
        return None if extracted is None else str(extracted)
    return str(mode_value)


def map_homey_mode_id(mode_id: str) -> str | None:
    """Map a Homey thermostat mode id/title to an HVACMode value string.

    Order matters: ``heatcool`` must be checked before ``heat`` / ``cool``.
    """
    mode_id_lower = str(mode_id).lower().strip()
    normalized = mode_id_lower.replace("_", "").replace("-", "").replace(" ", "")

    if normalized in ("heatcool",) or "heatcool" in normalized:
        return HVAC_HEAT_COOL
    if mode_id_lower == "off" or normalized == "off":
        return HVAC_OFF
    if (
        "off" in mode_id_lower
        and "heat" not in mode_id_lower
        and "cool" not in mode_id_lower
    ):
        return HVAC_OFF
    # ThermoFloor "Energy Save Heat" / "Energy Save" → AUTO (before plain heat)
    if "energy" in mode_id_lower or (
        "save" in mode_id_lower and "heat" in mode_id_lower
    ):
        return HVAC_AUTO
    if mode_id_lower in ("heat", "heating") or (
        "heat" in mode_id_lower and "cool" not in mode_id_lower
    ):
        return HVAC_HEAT
    if mode_id_lower in ("cool", "cooling") or (
        "cool" in mode_id_lower and "heat" not in mode_id_lower
    ):
        return HVAC_COOL
    if "auto" in mode_id_lower or "save" in mode_id_lower:
        return HVAC_AUTO
    return None


def map_homey_hvac_action_id(value: str) -> str | None:
    """Map Nest/Homey HVAC action strings to HVACAction value strings."""
    key = str(value).lower().strip()
    if key in ("off",):
        return ACTION_OFF
    if key in ("idle",):
        return ACTION_IDLE
    if key in ("heating", "heat"):
        return ACTION_HEATING
    if key in ("cooling", "cool"):
        return ACTION_COOLING
    if key in ("drying", "dry"):
        return ACTION_DRYING
    if key in ("fan", "fan_only"):
        return ACTION_FAN_ONLY
    return None


def find_custom_mode_capability(capabilities: dict[str, Any]) -> str | None:
    """Return the best enum mode capability id for climate control."""
    for preferred in PREFERRED_MODE_CAPABILITIES:
        cap = capabilities.get(preferred)
        if cap and cap.get("type") == "enum":
            return preferred
    for cap_id, cap_data in capabilities.items():
        if (
            cap_id.endswith("_mode")
            and cap_id != "thermostat_mode"
            and cap_data.get("type") == "enum"
        ):
            return cap_id
    return None
