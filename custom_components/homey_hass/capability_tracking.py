"""Track which Homey capabilities have already been seen, across restarts.

The coordinator raises a "New Homey capabilities detected" notification for
capabilities it has not seen before. The set of seen capabilities used to live
only in memory, so after every Home Assistant restart or integration reload the
first poll rebuilt the baseline and any capability that appeared later in the
same session was reported again, even though the user had seen it long ago.

This module holds the bookkeeping without Home Assistant imports, so it can be
unit-tested on its own. The coordinator persists ``as_storage()`` with a
``homeassistant.helpers.storage.Store`` and feeds it back via ``restore()``.
"""
from __future__ import annotations

from typing import Any

STORAGE_VERSION = 1


def storage_key(domain: str, entry_id: str) -> str:
    """Per config entry, so two Homey hubs keep separate baselines."""
    return f"{domain}_known_capabilities_{entry_id}"


class KnownCapabilityTracker:
    """Remembers seen capability ids; reports only genuinely new ones."""

    def __init__(self) -> None:
        self._known: set[str] | None = None

    @property
    def has_baseline(self) -> bool:
        return self._known is not None

    def restore(self, data: Any) -> None:
        """Load a stored baseline. Invalid or missing data leaves no baseline."""
        if not isinstance(data, dict):
            return
        caps = data.get("capabilities")
        if isinstance(caps, list):
            self._known = {cap for cap in caps if isinstance(cap, str)}

    def update(self, current: set[str]) -> set[str]:
        """Return capability ids not seen before and remember them.

        Without a baseline (first run ever) everything currently present
        becomes the baseline and nothing is reported, as before.

        The baseline only grows: capabilities of removed devices stay in it on
        purpose, so re-pairing a device does not raise the notification again.
        """
        if self._known is None:
            self._known = set(current)
            return set()
        new_caps = current - self._known
        self._known |= new_caps
        return new_caps

    def as_storage(self) -> dict[str, list[str]]:
        return {"capabilities": sorted(self._known or ())}
