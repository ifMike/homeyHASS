from __future__ import annotations

import importlib.util
import sys
import types
from pathlib import Path
from types import SimpleNamespace

_ROOT = Path(__file__).resolve().parents[1]
_TEMPERATURE_PATH = _ROOT / "custom_components" / "homey_hass" / "temperature.py"
_CONST_PATH = _ROOT / "custom_components" / "homey_hass" / "const.py"


def _load_temperature_module(path: Path):
    spec = importlib.util.spec_from_file_location(
        "custom_components.homey_hass.temperature",
        path,
        submodule_search_locations=[str(path.parent)],
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    module.__package__ = "custom_components.homey_hass"
    spec.loader.exec_module(module)
    return module


def _load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_const = _load_module(_CONST_PATH, "homey_const_under_test")
_homey_hass_pkg = types.ModuleType("custom_components.homey_hass")
sys.modules.setdefault("custom_components", types.ModuleType("custom_components"))
sys.modules["custom_components.homey_hass"] = _homey_hass_pkg
sys.modules["custom_components.homey_hass.const"] = _const
_temp = _load_temperature_module(_TEMPERATURE_PATH)

resolve_temperature_unit = _temp.resolve_temperature_unit
parse_homey_temperature_unit = _temp.parse_homey_temperature_unit
get_device_temperature_unit = _temp.get_device_temperature_unit
convert_temperature = _temp.convert_temperature
normalize_temperature_override = _temp.normalize_temperature_override
CELSIUS = "°C"
FAHRENHEIT = "°F"
CONF_TEMPERATURE_UNIT_OVERRIDES = _const.CONF_TEMPERATURE_UNIT_OVERRIDES


def test_parse_fahrenheit_units() -> None:
    assert parse_homey_temperature_unit("°F") == FAHRENHEIT
    assert parse_homey_temperature_unit("F") == FAHRENHEIT


def test_resolve_uses_homey_units_only() -> None:
    cap = {"min": -20, "max": 90, "units": "°C", "value": 25}
    assert resolve_temperature_unit(cap) == CELSIUS


def test_resolve_defaults_to_celsius_when_units_missing() -> None:
    cap = {"min": 41, "max": 90, "value": 69}
    assert resolve_temperature_unit(cap) == CELSIUS


def test_user_override_fahrenheit() -> None:
    entry = SimpleNamespace(
        options={
            CONF_TEMPERATURE_UNIT_OVERRIDES: {
                "device-1": "fahrenheit",
            }
        }
    )
    cap = {"units": "°C", "value": 69}
    assert get_device_temperature_unit(entry, "device-1", cap) == FAHRENHEIT


def test_user_override_auto_uses_homey() -> None:
    entry = SimpleNamespace(options={CONF_TEMPERATURE_UNIT_OVERRIDES: {}})
    cap = {"units": "°F", "value": 69}
    assert get_device_temperature_unit(entry, "device-1", cap) == FAHRENHEIT


def test_convert_celsius_to_fahrenheit() -> None:
    assert convert_temperature(0, CELSIUS, FAHRENHEIT) == 32.0
    assert convert_temperature(20, CELSIUS, FAHRENHEIT) == 68.0


def test_normalize_override() -> None:
    assert normalize_temperature_override("auto") is None
    assert normalize_temperature_override("fahrenheit") == FAHRENHEIT
