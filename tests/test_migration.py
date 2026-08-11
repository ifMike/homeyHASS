from __future__ import annotations

import importlib.util
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

_ROOT = Path(__file__).resolve().parents[1]
_MIGRATION_PATH = _ROOT / "custom_components" / "homey_hass" / "migration.py"
_CONST_PATH = _ROOT / "custom_components" / "homey_hass" / "const.py"


def _load_migration_module():
    import sys

    if "homeassistant.core" not in sys.modules:
        ha = sys.modules.get("homeassistant") or MagicMock()
        sys.modules["homeassistant"] = ha
        sys.modules["homeassistant.core"] = MagicMock()
        sys.modules["homeassistant.config_entries"] = MagicMock()
        sys.modules["homeassistant.helpers"] = MagicMock()
        sys.modules["homeassistant.helpers.device_registry"] = MagicMock()
        sys.modules["homeassistant.helpers.entity_registry"] = MagicMock()

    const_spec = importlib.util.spec_from_file_location("const_for_migration", _CONST_PATH)
    assert const_spec is not None and const_spec.loader is not None
    const_mod = importlib.util.module_from_spec(const_spec)
    const_spec.loader.exec_module(const_mod)

    spec = importlib.util.spec_from_file_location(
        "migration_for_tests",
        _MIGRATION_PATH,
        submodule_search_locations=[str(_MIGRATION_PATH.parent)],
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    module.__package__ = "custom_components.homey_hass"
    import sys

    package = sys.modules.get("custom_components.homey_hass")
    if package is None:
        package = MagicMock()
        package.__dict__["__path__"] = [str(_MIGRATION_PATH.parent)]
        sys.modules["custom_components.homey_hass"] = package
    sys.modules["custom_components.homey_hass.const"] = const_mod
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


_migration = _load_migration_module()
legacy_unique_id_body = _migration.legacy_unique_id_body
snapshot_legacy_entity_map = _migration.snapshot_legacy_entity_map
build_migration_success_message = _migration.build_migration_success_message
LegacyMigrationResult = _migration.LegacyMigrationResult
get_legacy_config_entries = _migration.get_legacy_config_entries
_device_config_entry_ids = _migration._device_config_entry_ids
_device_belongs_to_entry = _migration._device_belongs_to_entry


def test_legacy_unique_id_body_strips_prefixes() -> None:
    assert legacy_unique_id_body("homey_abc123_onoff") == "abc123_onoff"
    assert legacy_unique_id_body("homey_hass_abc123_onoff") == "abc123_onoff"
    assert legacy_unique_id_body("other_prefix_abc") is None
    assert legacy_unique_id_body(None) is None


def test_legacy_unique_id_body_multi_hub() -> None:
    body = "hub-1_device-1_measure_temperature"
    assert legacy_unique_id_body(f"homey_{body}") == body
    assert legacy_unique_id_body(f"homey_hass_{body}") == body


def test_device_config_entry_ids_supports_plural_and_singular() -> None:
    plural = SimpleNamespace(config_entries=frozenset({"entry-a", "entry-b"}))
    assert _device_config_entry_ids(plural) == {"entry-a", "entry-b"}

    singular = SimpleNamespace(config_entry_id="entry-a")
    assert _device_config_entry_ids(singular) == {"entry-a"}

    empty = SimpleNamespace()
    assert _device_config_entry_ids(empty) == set()


def test_device_belongs_to_entry() -> None:
    device = SimpleNamespace(config_entries=frozenset({"legacy-1", "legacy-2"}))
    assert _device_belongs_to_entry(device, "legacy-1") is True
    assert _device_belongs_to_entry(device, "other") is False


def test_snapshot_legacy_entity_map_filters_by_entry() -> None:
    entities = {
        "light.one": SimpleNamespace(
            platform="homey",
            config_entry_id="legacy-1",
            unique_id="homey_dev1_onoff",
            entity_id="light.one",
        ),
        "light.two": SimpleNamespace(
            platform="homey",
            config_entry_id="legacy-2",
            unique_id="homey_dev2_onoff",
            entity_id="light.two",
        ),
        "light.three": SimpleNamespace(
            platform="homey_hass",
            config_entry_id="new-1",
            unique_id="homey_hass_dev1_onoff",
            entity_id="light.three",
        ),
    }
    registry = SimpleNamespace(entities=entities)

    scoped = snapshot_legacy_entity_map(registry, "legacy-1")
    assert scoped == {"dev1_onoff": "light.one"}

    all_legacy = snapshot_legacy_entity_map(registry, None)
    assert all_legacy == {
        "dev1_onoff": "light.one",
        "dev2_onoff": "light.two",
    }


def test_get_legacy_config_entries_requires_loaded_integration() -> None:
    from unittest.mock import MagicMock

    legacy_entry = SimpleNamespace(domain="homey", entry_id="legacy-1")
    hass = MagicMock()
    hass.config.components = {"homey"}
    hass.config_entries.async_entries.return_value = [legacy_entry]
    assert get_legacy_config_entries(hass) == [legacy_entry]

    hass.config.components = set()
    assert get_legacy_config_entries(hass) == []


def test_build_migration_success_message_includes_service_hints() -> None:
    message = build_migration_success_message(
        LegacyMigrationResult(
            entities_preserved=10,
            entities_skipped=1,
            device_areas_restored=3,
            legacy_entry_removed=True,
        )
    )
    assert "Entity IDs preserved: **10**" in message
    assert "homey.trigger_flow" in message
    assert "homey_hass.trigger_flow" in message
    assert "custom_components/homey/" in message
    assert "migrating-from-1x-to-2x" in message
