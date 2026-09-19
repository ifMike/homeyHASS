"""Tests for HA state length helpers (#34)."""
from __future__ import annotations

import importlib.util
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
_STATE_UTILS_PATH = _ROOT / "custom_components" / "homey_hass" / "state_utils.py"


def _load_state_utils():
    spec = importlib.util.spec_from_file_location("state_utils_under_test", _STATE_UTILS_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_state_utils = _load_state_utils()
truncate_ha_state = _state_utils.truncate_ha_state
state_attributes_for_truncated = _state_utils.state_attributes_for_truncated
HA_STATE_MAX_LENGTH = _state_utils.HA_STATE_MAX_LENGTH
ATTR_FULL_VALUE = _state_utils.ATTR_FULL_VALUE


def test_short_string_unchanged() -> None:
    state, full = truncate_ha_state("hello")
    assert state == "hello"
    assert full is None
    assert state_attributes_for_truncated(full) == {}


def test_exact_limit_unchanged() -> None:
    value = "x" * HA_STATE_MAX_LENGTH
    state, full = truncate_ha_state(value)
    assert state == value
    assert full is None


def test_long_string_truncated_with_full_attribute() -> None:
    value = "a" * (HA_STATE_MAX_LENGTH + 50)
    state, full = truncate_ha_state(value)
    assert len(state) == HA_STATE_MAX_LENGTH
    assert state.endswith("…")
    assert full == value
    assert state_attributes_for_truncated(full) == {ATTR_FULL_VALUE: value}


def test_svg_uses_short_marker() -> None:
    svg = "<svg xmlns='http://www.w3.org/2000/svg'>" + ("x" * 300) + "</svg>"
    state, full = truncate_ha_state(svg)
    assert state == "svg"
    assert full == svg
    assert len(state) <= HA_STATE_MAX_LENGTH


def test_svg_with_leading_whitespace() -> None:
    svg = "  \n<svg>" + ("y" * 300)
    state, full = truncate_ha_state(svg)
    assert state == "svg"
    assert full == svg
