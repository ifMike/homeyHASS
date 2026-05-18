"""Pytest configuration for Homey integration tests."""
from __future__ import annotations

import sys
from unittest.mock import MagicMock


def _install_homeassistant_stubs() -> None:
    """Minimal homeassistant stubs so unit tests can import integration modules."""
    if "homeassistant" in sys.modules:
        return

    ha = MagicMock()
    ha.const.UnitOfTemperature.CELSIUS = "°C"
    ha.const.UnitOfTemperature.FAHRENHEIT = "°F"

    def _convert(value: float, from_unit: str, to_unit: str) -> float:
        if from_unit == to_unit:
            return value
        if from_unit == "°C" and to_unit == "°F":
            return (value * 9 / 5) + 32
        if from_unit == "°F" and to_unit == "°C":
            return (value - 32) * 5 / 9
        return value

    ha.util.unit_conversion.TemperatureConverter.convert = _convert

    ha.config_entries = MagicMock()
    ha.config_entries.ConfigEntry = type("ConfigEntry", (), {})

    sys.modules["homeassistant"] = ha
    sys.modules["homeassistant.const"] = ha.const
    sys.modules["homeassistant.config_entries"] = ha.config_entries
    sys.modules["homeassistant.util"] = ha.util
    sys.modules["homeassistant.util.unit_conversion"] = ha.util.unit_conversion


def pytest_configure(config) -> None:
    _install_homeassistant_stubs()
