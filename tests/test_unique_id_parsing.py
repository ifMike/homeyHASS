from __future__ import annotations

import importlib.util
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
_DEVICE_INFO_PATH = _ROOT / "custom_components" / "homey_hass" / "device_info.py"
_CONST_PATH = _ROOT / "custom_components" / "homey_hass" / "const.py"


def _load_device_info():
    const_spec = importlib.util.spec_from_file_location("const_for_unique_id", _CONST_PATH)
    assert const_spec is not None and const_spec.loader is not None
    const_mod = importlib.util.module_from_spec(const_spec)
    const_spec.loader.exec_module(const_mod)

    spec = importlib.util.spec_from_file_location(
        "device_info_for_unique_id",
        _DEVICE_INFO_PATH,
        submodule_search_locations=[str(_DEVICE_INFO_PATH.parent)],
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    module.__package__ = "custom_components.homey_hass"
    import sys

    sys.modules["custom_components.homey_hass.const"] = const_mod
    spec.loader.exec_module(module)
    return module


_device_info = _load_device_info()
build_entity_unique_id = _device_info.build_entity_unique_id
extract_unique_id_primary = _device_info.extract_unique_id_primary


def test_flow_unique_id_roundtrip_single_hub() -> None:
    flow_id = "my_flow_with_underscores"
    unique_id = build_entity_unique_id(None, flow_id, "flow", multi_homey=False)
    assert unique_id == f"homey_hass_{flow_id}_flow"
    assert extract_unique_id_primary(unique_id, "flow") == flow_id


def test_flow_unique_id_roundtrip_multi_hub() -> None:
    homey_id = "hub-123"
    flow_id = "flow_abc"
    unique_id = build_entity_unique_id(homey_id, flow_id, "flow", multi_homey=True)
    assert unique_id == f"homey_hass_{homey_id}_{flow_id}_flow"
    assert (
        extract_unique_id_primary(
            unique_id,
            "flow",
            homey_id=homey_id,
            multi_homey=True,
        )
        == flow_id
    )


def test_legacy_homey_prefix_does_not_parse() -> None:
    assert extract_unique_id_primary("homey_old_flow_id_flow", "flow") is None
