"""Tests for multi-hub unique_id migration helpers (#35)."""
from __future__ import annotations

import importlib.util
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
_CONST_PATH = _ROOT / "custom_components" / "homey_hass" / "const.py"
_DEVICE_INFO_PATH = _ROOT / "custom_components" / "homey_hass" / "device_info.py"


def _load_device_info():
    const_spec = importlib.util.spec_from_file_location("const_for_uid_mig", _CONST_PATH)
    assert const_spec is not None and const_spec.loader is not None
    const_mod = importlib.util.module_from_spec(const_spec)
    const_spec.loader.exec_module(const_mod)

    import sys

    sys.modules["custom_components.homey_hass.const"] = const_mod

    spec = importlib.util.spec_from_file_location(
        "device_info_for_uid_mig",
        _DEVICE_INFO_PATH,
        submodule_search_locations=[str(_DEVICE_INFO_PATH.parent)],
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    module.__package__ = "custom_components.homey_hass"
    spec.loader.exec_module(module)
    return module, const_mod


_device_info, _const = _load_device_info()
build_entity_unique_id = _device_info.build_entity_unique_id
UNIQUE_ID_PREFIX = _const.UNIQUE_ID_PREFIX


def _migrate_unique_id(unique_id: str, homey_id: str) -> str | None:
    """Mirror the multi-hub unique_id rewrite rule used in __init__.py."""
    scoped_prefix = f"{UNIQUE_ID_PREFIX}{homey_id}_"
    if not unique_id.startswith(UNIQUE_ID_PREFIX):
        return None
    if unique_id.startswith(scoped_prefix):
        return None  # already migrated
    suffix = unique_id[len(UNIQUE_ID_PREFIX) :]
    return f"{scoped_prefix}{suffix}"


def test_single_hub_unique_id_unchanged_by_builder() -> None:
    uid = build_entity_unique_id("hub1", "dev1", "onoff", multi_homey=False)
    assert uid == "homey_hass_dev1_onoff"
    assert _migrate_unique_id(uid, "hub1") == "homey_hass_hub1_dev1_onoff"


def test_multi_hub_builder_matches_migration_target() -> None:
    multi = build_entity_unique_id("hub1", "dev1", "onoff", multi_homey=True)
    single = build_entity_unique_id(None, "dev1", "onoff", multi_homey=False)
    assert _migrate_unique_id(single, "hub1") == multi


def test_already_scoped_unique_id_is_not_rewritten() -> None:
    uid = build_entity_unique_id("hub1", "dev1", "onoff", multi_homey=True)
    assert _migrate_unique_id(uid, "hub1") is None


def test_migration_does_not_apply_to_other_prefixes() -> None:
    assert _migrate_unique_id("homey_dev1_onoff", "hub1") is None
    assert _migrate_unique_id("other_dev1_onoff", "hub1") is None


def test_config_flow_version_is_3() -> None:
    """VERSION bump must match async_migrate_entry early-return (>= 3)."""
    flow_path = _ROOT / "custom_components" / "homey_hass" / "config_flow.py"
    text = flow_path.read_text(encoding="utf-8")
    assert "VERSION = 3" in text


def test_migrate_entry_uses_async_update_entry_for_version() -> None:
    """HA rejects direct entry.version assignment — migrate must use async_update_entry."""
    init_path = _ROOT / "custom_components" / "homey_hass" / "__init__.py"
    text = init_path.read_text(encoding="utf-8")
    assert "entry.version = " not in text
    assert "async_update_entry(entry, data=new_data, version=3)" in text
    assert "async_update_entry(entry, version=3)" in text
