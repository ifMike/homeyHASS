"""Tests for multi-hub enablement decision (#35 / #37)."""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
_CONST_PATH = _ROOT / "custom_components" / "homey_hass" / "const.py"
_MULTI_HOMEY_PATH = _ROOT / "custom_components" / "homey_hass" / "multi_homey.py"
_INIT_PATH = _ROOT / "custom_components" / "homey_hass" / "__init__.py"
_SENSOR_PATH = _ROOT / "custom_components" / "homey_hass" / "sensor.py"
_TEXT_PATH = _ROOT / "custom_components" / "homey_hass" / "text.py"

HUB = "64a800e59e98a40b8d6a18d5"
DEVICE = "81ac96a5-0518-4222-a6f1-f68b2f21f410"


def _load_multi_homey():
    const_spec = importlib.util.spec_from_file_location("const_for_multi", _CONST_PATH)
    assert const_spec is not None and const_spec.loader is not None
    const_mod = importlib.util.module_from_spec(const_spec)
    const_spec.loader.exec_module(const_mod)
    sys.modules["custom_components.homey_hass.const"] = const_mod

    spec = importlib.util.spec_from_file_location(
        "multi_homey_under_test",
        _MULTI_HOMEY_PATH,
        submodule_search_locations=[str(_MULTI_HOMEY_PATH.parent)],
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    module.__package__ = "custom_components.homey_hass"
    spec.loader.exec_module(module)
    return module


_multi = _load_multi_homey()
should_use_multi_homey = _multi.should_use_multi_homey
registry_uses_hub_prefix = _multi.registry_uses_hub_prefix
unique_id_hub_prefix = _multi.unique_id_hub_prefix


def test_single_active_hub_without_entities_stays_single() -> None:
    """One real hub + ignored discoveries must not enable multi-hub."""
    assert (
        should_use_multi_homey(
            active_hub_count=1,
            sticky_enabled=False,
            registry_uses_hub_prefix=None,
        )
        is False
    )


def test_two_active_hubs_enables_multi_mode() -> None:
    assert (
        should_use_multi_homey(
            active_hub_count=2,
            sticky_enabled=False,
            registry_uses_hub_prefix=False,
        )
        is True
    )


def test_existing_prefixes_stay_even_without_sticky_flag() -> None:
    """#37: 2.1.2 prefixed IDs, but multi_homey_enabled was never stored."""
    assert (
        should_use_multi_homey(
            active_hub_count=1,
            sticky_enabled=False,
            registry_uses_hub_prefix=True,
        )
        is True
    )


def test_unprefixed_single_hub_ignores_stale_flag() -> None:
    """A stored flag must not re-prefix entities that are working unprefixed."""
    assert (
        should_use_multi_homey(
            active_hub_count=1,
            sticky_enabled=True,
            registry_uses_hub_prefix=False,
        )
        is False
    )


def test_sticky_with_no_entities_keeps_multi_mode() -> None:
    assert (
        should_use_multi_homey(
            active_hub_count=1,
            sticky_enabled=True,
            registry_uses_hub_prefix=None,
        )
        is True
    )


def test_zero_active_hubs_without_sticky() -> None:
    assert (
        should_use_multi_homey(
            active_hub_count=0,
            sticky_enabled=False,
            registry_uses_hub_prefix=None,
        )
        is False
    )


def test_prefixed_sensor_unique_id_detected() -> None:
    uid = f"homey_hass_{HUB}_{DEVICE}_measure_temperature"
    assert unique_id_hub_prefix(uid) == HUB
    assert registry_uses_hub_prefix([uid]) is True


def test_unprefixed_sensor_unique_id_not_detected_as_hub() -> None:
    uid = f"homey_hass_{DEVICE}_measure_humidity"
    assert unique_id_hub_prefix(uid) is None
    assert registry_uses_hub_prefix([uid], homey_ids=[HUB]) is False


def test_known_homey_id_prefix_counts_even_without_uuid() -> None:
    uid = f"homey_hass_{HUB}_logic_text_forecast"
    assert registry_uses_hub_prefix([uid], homey_ids=[HUB]) is True


def test_empty_registry_is_unknown() -> None:
    assert registry_uses_hub_prefix([]) is None


def test_init_preserves_existing_prefixes() -> None:
    text = _INIT_PATH.read_text(encoding="utf-8")
    assert "preserve_existing_prefixes" in text
    assert "registry_uses_hub_prefix" in text
    assert "migrated_unique_id(" in text
    assert 'async_entries(DOMAIN, include_ignore=False)' in text


def test_string_entities_exclude_full_value_from_recorder() -> None:
    """full_value must stay live for templates but not bloat the history DB."""
    sensor_text = _SENSOR_PATH.read_text(encoding="utf-8")
    text_text = _TEXT_PATH.read_text(encoding="utf-8")
    marker = '_unrecorded_attributes = frozenset({ATTR_FULL_VALUE})'
    assert marker in sensor_text
    assert marker in text_text
    assert text_text.count(marker) == 2
