"""Guards for Home Assistant 2026.11 compatibility (no HA import required)."""
from __future__ import annotations

from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
_CLIMATE = _ROOT / "custom_components" / "homey_hass" / "climate.py"
_LIGHT = _ROOT / "custom_components" / "homey_hass" / "light.py"


def test_climate_uses_native_temperature_when_available() -> None:
    text = _CLIMATE.read_text(encoding="utf-8")
    assert "_USE_NATIVE_CLIMATE_TEMP" in text
    assert "native_current_temperature" in text
    assert "native_target_temperature" in text
    assert "_attr_native_temperature_unit" in text
    # Old API retained for HA 2026.10 and earlier.
    assert "_attr_temperature_unit" in text
    assert "def current_temperature" in text
    assert "def target_temperature" in text


def test_light_opts_in_to_inplace_entity_id_changes() -> None:
    text = _LIGHT.read_text(encoding="utf-8")
    assert "def async_entity_id_changed" in text
    assert "async_added_to_hass" in text
