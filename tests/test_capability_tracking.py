"""Known-capability baseline survives restarts (no repeated 'new capability' notifications)."""
from __future__ import annotations

import importlib.util
from pathlib import Path

_PATH = Path(__file__).resolve().parents[1] / "custom_components" / "homey_hass" / "capability_tracking.py"
_spec = importlib.util.spec_from_file_location("homey_capability_tracking_under_test", _PATH)
assert _spec is not None and _spec.loader is not None
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)
KnownCapabilityTracker = _mod.KnownCapabilityTracker
storage_key = _mod.storage_key


def test_first_run_sets_baseline_without_reporting() -> None:
    tracker = KnownCapabilityTracker()
    assert tracker.update({"onoff", "dim"}) == set()
    assert tracker.has_baseline


def test_later_capability_is_reported_once() -> None:
    tracker = KnownCapabilityTracker()
    tracker.update({"onoff"})
    assert tracker.update({"onoff", "lightDiyScenes"}) == {"lightDiyScenes"}
    assert tracker.update({"onoff", "lightDiyScenes"}) == set()


def test_restart_restores_baseline_so_known_capability_is_not_reported_again() -> None:
    before = KnownCapabilityTracker()
    before.update({"onoff"})
    before.update({"onoff", "lightDiyScenes"})
    stored = before.as_storage()

    after_restart = KnownCapabilityTracker()
    after_restart.restore(stored)
    assert after_restart.update({"onoff", "lightDiyScenes"}) == set()
    assert after_restart.update({"onoff", "lightDiyScenes", "measure_power"}) == {"measure_power"}


def test_missing_or_invalid_storage_falls_back_to_first_run_behaviour() -> None:
    for data in (None, [], {"capabilities": "onoff"}, {"other": 1}):
        tracker = KnownCapabilityTracker()
        tracker.restore(data)
        assert not tracker.has_baseline
        assert tracker.update({"onoff"}) == set()


def test_non_string_entries_are_ignored_on_restore() -> None:
    tracker = KnownCapabilityTracker()
    tracker.restore({"capabilities": ["onoff", 3, None]})
    assert tracker.update({"onoff", "dim"}) == {"dim"}


def test_storage_is_sorted_and_key_is_per_entry() -> None:
    tracker = KnownCapabilityTracker()
    tracker.update({"b", "a"})
    assert tracker.as_storage() == {"capabilities": ["a", "b"]}
    assert storage_key("homey_hass", "abc") == "homey_hass_known_capabilities_abc"
