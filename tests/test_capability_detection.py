from __future__ import annotations

import importlib.util
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
_CONST_PATH = _ROOT / "custom_components" / "homey_hass" / "const.py"


def _load_const_module():
    spec = importlib.util.spec_from_file_location("homey_const_under_test", _CONST_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_const = _load_const_module()
is_capability_supported = _const.is_capability_supported
is_generic_enum_select_capability = _const.is_generic_enum_select_capability
CAPABILITY_TO_PLATFORM = _const.CAPABILITY_TO_PLATFORM

_LOCK_MODE = {
    "id": "lock_mode",
    "type": "enum",
    "getable": True,
    "setable": True,
    "values": [
        {"id": "normal", "title": "Normal"},
        {"id": "no_remote_lock_unlock", "title": "No remote"},
    ],
    "value": "normal",
}


def test_measure_current_is_supported() -> None:
    assert is_capability_supported("measure_current")


def test_measure_subcapability_is_supported() -> None:
    assert is_capability_supported("measure_power.phase")


def test_meter_and_alarm_prefixes_are_supported() -> None:
    assert is_capability_supported("meter_power")
    assert is_capability_supported("alarm_custom_sensor")


def test_mapped_capability_is_supported() -> None:
    assert is_capability_supported("onoff")
    assert is_capability_supported("dim")


def test_unknown_capability_is_not_supported() -> None:
    assert not is_capability_supported("vendor_custom_metric")
    assert not is_capability_supported("test_capability")


def test_dyson_fan_capabilities_are_supported() -> None:
    assert is_capability_supported("oscillate")
    assert is_capability_supported("less_air")
    assert is_capability_supported("more_air")


def test_nest_thermostat_capabilities_are_supported() -> None:
    assert is_capability_supported("nest_thermostat_eco")
    assert is_capability_supported("nest_thermostat_hvac")
    assert is_capability_supported("nest_thermostat_mode")


def test_lock_mode_is_mapped_to_select() -> None:
    assert CAPABILITY_TO_PLATFORM.get("lock_mode") == "select"
    assert is_capability_supported("lock_mode")


def test_lock_mode_enum_payload_is_supported_as_select() -> None:
    assert is_generic_enum_select_capability("lock_mode", _LOCK_MODE)
    assert is_capability_supported("lock_mode", _LOCK_MODE)


def test_generic_enum_without_mapping_is_supported_when_payload_present() -> None:
    """select.py already creates these; do not open GitHub issues for them."""
    payload = {
        "type": "enum",
        "values": [{"id": "a", "title": "A"}, {"id": "b", "title": "B"}],
        "setable": True,
        "getable": True,
    }
    assert is_capability_supported("vendor_lock_profile", payload)
    assert not is_capability_supported("vendor_lock_profile")


def test_windowcoverings_state_enum_is_not_generic_select() -> None:
    payload = {
        "type": "enum",
        "values": [
            {"id": "up", "title": "Up"},
            {"id": "idle", "title": "Idle"},
            {"id": "down", "title": "Down"},
        ],
    }
    assert not is_generic_enum_select_capability("windowcoverings_state", payload)
