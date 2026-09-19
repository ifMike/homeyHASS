"""Tests for Nest / Homey climate mode mapping (#36)."""
from __future__ import annotations

import importlib.util
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
_MODES_PATH = _ROOT / "custom_components" / "homey_hass" / "climate_modes.py"
_CONST_PATH = _ROOT / "custom_components" / "homey_hass" / "const.py"


def _load_modes():
    spec = importlib.util.spec_from_file_location("climate_modes_under_test", _MODES_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_modes = _load_modes()
map_homey_mode_id = _modes.map_homey_mode_id
map_homey_hvac_action_id = _modes.map_homey_hvac_action_id
find_custom_mode_capability = _modes.find_custom_mode_capability
HVAC_OFF = _modes.HVAC_OFF
HVAC_HEAT = _modes.HVAC_HEAT
HVAC_COOL = _modes.HVAC_COOL
HVAC_AUTO = _modes.HVAC_AUTO
HVAC_HEAT_COOL = _modes.HVAC_HEAT_COOL
ACTION_COOLING = _modes.ACTION_COOLING
ACTION_HEATING = _modes.ACTION_HEATING
ACTION_OFF = _modes.ACTION_OFF


def test_heatcool_maps_to_heat_cool_not_heat() -> None:
    assert map_homey_mode_id("heatcool") == HVAC_HEAT_COOL
    assert map_homey_mode_id("HeatCool") == HVAC_HEAT_COOL


def test_nest_modes() -> None:
    assert map_homey_mode_id("off") == HVAC_OFF
    assert map_homey_mode_id("heat") == HVAC_HEAT
    assert map_homey_mode_id("cool") == HVAC_COOL


def test_thermofloor_energy_save_heat_is_auto() -> None:
    assert map_homey_mode_id("Energy Save Heat") == HVAC_AUTO
    assert map_homey_mode_id("Heat") == HVAC_HEAT


def test_nest_hvac_action() -> None:
    assert map_homey_hvac_action_id("cooling") == ACTION_COOLING
    assert map_homey_hvac_action_id("heating") == ACTION_HEATING
    assert map_homey_hvac_action_id("off") == ACTION_OFF


def test_prefer_nest_mode_capability() -> None:
    caps = {
        "other_mode": {"type": "enum", "values": []},
        "nest_thermostat_mode": {"type": "enum", "values": []},
    }
    assert find_custom_mode_capability(caps) == "nest_thermostat_mode"


def test_nest_capabilities_are_supported() -> None:
    const_spec = importlib.util.spec_from_file_location("const_nest", _CONST_PATH)
    assert const_spec and const_spec.loader
    const_mod = importlib.util.module_from_spec(const_spec)
    const_spec.loader.exec_module(const_mod)
    assert const_mod.is_capability_supported("nest_thermostat_eco")
    assert const_mod.is_capability_supported("nest_thermostat_hvac")
    assert const_mod.is_capability_supported("nest_thermostat_mode")
    assert const_mod.CAPABILITY_TO_PLATFORM["nest_thermostat_eco"] == "switch"
    assert const_mod.CAPABILITY_TO_PLATFORM["nest_thermostat_mode"] == "climate"
