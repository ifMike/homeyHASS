"""Tests for multi-hub enablement decision (#35 follow-up)."""
from __future__ import annotations

import importlib.util
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
_MULTI_HOMEY_PATH = _ROOT / "custom_components" / "homey_hass" / "multi_homey.py"
_INIT_PATH = _ROOT / "custom_components" / "homey_hass" / "__init__.py"
_SENSOR_PATH = _ROOT / "custom_components" / "homey_hass" / "sensor.py"
_TEXT_PATH = _ROOT / "custom_components" / "homey_hass" / "text.py"


def _load_multi_homey():
    spec = importlib.util.spec_from_file_location("multi_homey_under_test", _MULTI_HOMEY_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_multi = _load_multi_homey()
should_use_multi_homey = _multi.should_use_multi_homey


def test_single_active_hub_without_sticky_is_single_mode() -> None:
    """One real hub + ignored discoveries must not enable multi-hub."""
    assert should_use_multi_homey(active_hub_count=1, sticky_enabled=False) is False


def test_two_active_hubs_enables_multi_mode() -> None:
    assert should_use_multi_homey(active_hub_count=2, sticky_enabled=False) is True


def test_sticky_keeps_multi_mode_when_count_drops_to_one() -> None:
    """Deleting ignored entries must not reverse unique_id prefixes."""
    assert should_use_multi_homey(active_hub_count=1, sticky_enabled=True) is True


def test_zero_active_hubs_without_sticky() -> None:
    assert should_use_multi_homey(active_hub_count=0, sticky_enabled=False) is False


def test_init_excludes_ignored_entries_when_counting_hubs() -> None:
    """Regression: async_entries defaults to include_ignore=True in HA."""
    text = _INIT_PATH.read_text(encoding="utf-8")
    assert 'async_entries(DOMAIN, include_ignore=False)' in text
    assert "should_use_multi_homey(" in text
    # Old buggy pattern must not remain as the multi-hub decision.
    assert "multi_hub = len(entries) > 1" not in text
    assert (
        "multi_homey_enabled = len(list(hass.config_entries.async_entries(DOMAIN))) > 1"
        not in text
    )


def test_string_entities_exclude_full_value_from_recorder() -> None:
    """full_value must stay live for templates but not bloat the history DB."""
    sensor_text = _SENSOR_PATH.read_text(encoding="utf-8")
    text_text = _TEXT_PATH.read_text(encoding="utf-8")
    marker = '_unrecorded_attributes = frozenset({ATTR_FULL_VALUE})'
    assert marker in sensor_text
    assert marker in text_text
    assert text_text.count(marker) == 2  # HomeyText + HomeyLogicText
