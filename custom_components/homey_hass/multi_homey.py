"""Helpers for multi-Homey hub detection and unique_id scoping."""
from __future__ import annotations


def should_use_multi_homey(*, active_hub_count: int, sticky_enabled: bool) -> bool:
    """Decide whether entity unique_ids should be hub-prefixed.

    ``active_hub_count`` must count only real configured hubs — ignored
    discovery entries (``source=ignore``) must not be included. Home Assistant's
    ``async_entries()`` defaults to ``include_ignore=True``, which would falsely
    enable multi-hub mode when a user dismissed other Homeys with "Ignore".

    ``sticky_enabled`` is True when any real entry already persisted
    ``multi_homey_enabled``. Once prefixes are applied, keep them even if the
    active hub count later drops to 1 (e.g. ignored entries are deleted), so
    entities are not recreated with unprefixed unique_ids.
    """
    if sticky_enabled:
        return True
    return active_hub_count > 1
