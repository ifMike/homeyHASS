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
