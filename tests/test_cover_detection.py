from __future__ import annotations

import importlib.util
import sys
import types
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
_COMPONENT = _ROOT / "custom_components" / "homey"


def _ensure_package(name: str) -> types.ModuleType:
    if name not in sys.modules:
        sys.modules[name] = types.ModuleType(name)
    return sys.modules[name]


def _load_module(module_name: str, path: Path):
    spec = importlib.util.spec_from_file_location(module_name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


_ensure_package("custom_components")
_ensure_package("custom_components.homey")
_load_module("custom_components.homey.const", _COMPONENT / "const.py")
_device_info = _load_module(
    "custom_components.homey.device_info",
    _COMPONENT / "device_info.py",
)

get_device_type = _device_info.get_device_type
has_standard_cover_capabilities = _device_info.has_standard_cover_capabilities
is_legacy_dim_cover = _device_info.is_legacy_dim_cover
should_create_cover_entity = _device_info.should_create_cover_entity


def _fibaro_roller_capabilities() -> dict:
    return {
        "dim": {"type": "number", "setable": True, "value": 0.42},
        "measure_power": {"type": "number", "setable": False, "value": 12.3},
        "meter_power": {"type": "number", "setable": False, "value": 45.6},
    }


def test_standard_windowcoverings_set_is_cover() -> None:
    capabilities = {
        "windowcoverings_set": {"type": "number", "setable": True, "value": 0.5},
    }
    assert has_standard_cover_capabilities(capabilities)
    assert should_create_cover_entity(capabilities, "windowcoverings")


def test_fibaro_roller_with_dim_and_cover_class_is_legacy_cover() -> None:
    capabilities = _fibaro_roller_capabilities()
    assert not has_standard_cover_capabilities(capabilities)
    assert is_legacy_dim_cover(capabilities, "blind", "com.fibaro.fgr223")
    assert should_create_cover_entity(capabilities, "blind", "com.fibaro.fgr223")
    assert get_device_type(capabilities, "com.fibaro.fgr223", "blind") == "cover"


def test_fibaro_roller_without_cover_class_uses_driver_heuristic() -> None:
    capabilities = _fibaro_roller_capabilities()
    assert is_legacy_dim_cover(
        capabilities,
        "other",
        "com.fibaro.fgr223",
        driver_id="homey:app:com.fibaro:fgw223",
    )
    assert should_create_cover_entity(
        capabilities,
        "other",
        "com.fibaro.fgr223",
        driver_id="homey:app:com.fibaro:fgw223",
    )


def test_dimmer_with_onoff_and_dim_is_not_legacy_cover_without_cover_class() -> None:
    capabilities = {
        "onoff": {"type": "boolean", "setable": True, "value": True},
        "dim": {"type": "number", "setable": True, "value": 0.8},
    }
    assert not is_legacy_dim_cover(capabilities, "light")
    assert get_device_type(capabilities, device_class="light") == "light"


def test_dim_with_light_hue_is_not_legacy_cover() -> None:
    capabilities = {
        "dim": {"type": "number", "setable": True, "value": 0.5},
        "light_hue": {"type": "number", "setable": True, "value": 0.2},
    }
    assert not is_legacy_dim_cover(capabilities, "blind")


def test_non_setable_dim_is_not_legacy_cover() -> None:
    capabilities = {
        "dim": {"type": "number", "setable": False, "value": 0.5},
    }
    assert not is_legacy_dim_cover(capabilities, "blind")
