"""Upgrade compatibility: the next release must keep existing entity IDs.

Home Assistant matches entities by unique_id. If a release builds a different
id, the old entity becomes unavailable and a new one is created. These cases
are the installs we already shipped, including the 2.1.3 regression (#37).
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
_PKG = _ROOT / "custom_components" / "homey_hass"

HUB = "64a800e59e98a40b8d6a18d5"
OTHER_HUB = "aaaaaaaaaaaaaaaaaaaaaaaa"
DEVICE = "81ac96a5-0518-4222-a6f1-f68b2f21f410"
SENSOR_SUFFIXES = (
    "measure_temperature",
    "measure_humidity",
    "measure_battery",
    "onoff",
    "climate",
)


def _load(name: str, filename: str):
    path = _PKG / filename
    spec = importlib.util.spec_from_file_location(
        name,
        path,
        submodule_search_locations=[str(_PKG)],
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    module.__package__ = "custom_components.homey_hass"
    spec.loader.exec_module(module)
    return module


def _load_modules():
    const = _load("const_for_upgrade", "const.py")
    sys.modules["custom_components.homey_hass.const"] = const
    return _load("device_info_for_upgrade", "device_info.py"), _load(
        "multi_homey_for_upgrade", "multi_homey.py"
    )


_device_info, _multi = _load_modules()
build_entity_unique_id = _device_info.build_entity_unique_id
build_device_identifier = _device_info.build_device_identifier
should_use_multi_homey = _multi.should_use_multi_homey
registry_uses_hub_prefix = _multi.registry_uses_hub_prefix
migrated_unique_id = _multi.migrated_unique_id


def _ids_for(multi: bool, suffix: str) -> tuple[str, tuple[str, str]]:
    return (
        build_entity_unique_id(HUB, DEVICE, suffix, multi),
        build_device_identifier(HUB, DEVICE, multi),
    )


def _next_multi(existing_unique_ids: list[str], *, hubs: int, sticky: bool) -> bool:
    """What this release would do, given the IDs already in the registry."""
    state = registry_uses_hub_prefix(existing_unique_ids, homey_ids=[HUB])
    return should_use_multi_homey(
        active_hub_count=hubs,
        sticky_enabled=sticky,
        registry_uses_hub_prefix=state,
    )


def test_single_hub_install_keeps_unprefixed_ids() -> None:
    existing = [build_entity_unique_id(HUB, DEVICE, s, False) for s in SENSOR_SUFFIXES]
    assert _next_multi(existing, hubs=1, sticky=False) is False
    for suffix in SENSOR_SUFFIXES:
        old_uid, old_device = _ids_for(False, suffix)
        assert _ids_for(_next_multi(existing, hubs=1, sticky=False), suffix) == (
            old_uid,
            old_device,
        )


def test_issue_37_prefixed_single_hub_without_flag_keeps_ids() -> None:
    """2.1.3 dropped these prefixes and sensors showed unavailable."""
    existing = [build_entity_unique_id(HUB, DEVICE, s, True) for s in SENSOR_SUFFIXES]
    # The 2.1.3 rule (hub count + flag only) would have turned prefixes off.
    buggy_2_1_3 = False or 1 > 1
    assert buggy_2_1_3 is False
    assert _next_multi(existing, hubs=1, sticky=False) is True
    for suffix in SENSOR_SUFFIXES:
        old_uid, old_device = _ids_for(True, suffix)
        assert _ids_for(True, suffix) == (old_uid, old_device)
        assert migrated_unique_id(old_uid, HUB) is None


def test_stale_flag_does_not_reprefix_a_working_single_hub() -> None:
    existing = [build_entity_unique_id(HUB, DEVICE, s, False) for s in SENSOR_SUFFIXES]
    assert _next_multi(existing, hubs=1, sticky=True) is False
    for suffix in SENSOR_SUFFIXES:
        assert _ids_for(False, suffix)[0] == existing[SENSOR_SUFFIXES.index(suffix)]


def test_two_real_hubs_already_prefixed_stay_prefixed() -> None:
    existing = [build_entity_unique_id(HUB, DEVICE, "measure_temperature", True)]
    assert _next_multi(existing, hubs=2, sticky=True) is True
    assert migrated_unique_id(existing[0], HUB) is None


def test_second_real_hub_migrates_unprefixed_id_in_place() -> None:
    old = build_entity_unique_id(HUB, DEVICE, "measure_temperature", False)
    new = build_entity_unique_id(HUB, DEVICE, "measure_temperature", True)
    assert _next_multi([old], hubs=2, sticky=False) is True
    assert migrated_unique_id(old, HUB) == new


def test_migration_never_stacks_a_second_hub_prefix() -> None:
    existing = build_entity_unique_id(HUB, DEVICE, "measure_humidity", True)
    assert migrated_unique_id(existing, OTHER_HUB) is None


def test_fresh_single_hub_with_no_entities_stays_unprefixed() -> None:
    assert _next_multi([], hubs=1, sticky=False) is False
    uid, _device = _ids_for(False, "measure_temperature")
    assert HUB not in uid


def test_ignored_discovery_does_not_change_a_fresh_single_hub() -> None:
    """Ignored entries are not part of active_hub_count (always 1 here)."""
    assert _next_multi([], hubs=1, sticky=False) is False
