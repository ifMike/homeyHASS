"""Helpers for multi-Homey hub detection and unique_id scoping."""
from __future__ import annotations

import re

from .const import UNIQUE_ID_PREFIX

# Homey device ids are UUIDs. A hub-prefixed unique_id is
# ``homey_hass_{hub}_{device-uuid}_{suffix}``.
_DEVICE_UUID = (
    r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-"
    r"[0-9a-fA-F]{4}-[0-9a-fA-F]{12}"
)
_PREFIXED_DEVICE_UNIQUE_ID = re.compile(
    rf"^{re.escape(UNIQUE_ID_PREFIX)}(?P<hub>.+?)_(?P<uuid>{_DEVICE_UUID})_"
)


def unique_id_hub_prefix(unique_id: str | None) -> str | None:
    """Return the hub id already embedded in a unique_id, if any."""
    if not unique_id:
        return None
    match = _PREFIXED_DEVICE_UNIQUE_ID.match(unique_id)
    if not match:
        return None
    return match.group("hub")


def registry_uses_hub_prefix(
    unique_ids: list[str],
    *,
    homey_ids: list[str] | None = None,
    device_identifier_values: list[str] | None = None,
) -> bool | None:
    """Whether existing entities already use hub-prefixed unique_ids.

    Returns True/False when Homey entities exist, or None when the registry
    has nothing to preserve. Entity unique_ids win over device identifiers:
    flipping the scheme is what makes entities show as unavailable.
    """
    ours = [uid for uid in unique_ids if uid and uid.startswith(UNIQUE_ID_PREFIX)]
    known = [hid for hid in (homey_ids or []) if hid]
    for uid in ours:
        if unique_id_hub_prefix(uid):
            return True
        for hid in known:
            if uid.startswith(f"{UNIQUE_ID_PREFIX}{hid}_"):
                return True
    if ours:
        return False
    scoped_devices = [v for v in (device_identifier_values or []) if v and ":" in v]
    if scoped_devices:
        return True
    return None


def migrated_unique_id(unique_id: str, homey_id: str) -> str | None:
    """Return a hub-prefixed unique_id, or None when the current id must stay.

    None means "do not touch this entity". Already-prefixed ids are left as
    they are, including ids prefixed with a different hub string, so a later
    release cannot stack a second prefix and orphan the entity.
    """
    if not unique_id or not homey_id or not unique_id.startswith(UNIQUE_ID_PREFIX):
        return None
    scoped_prefix = f"{UNIQUE_ID_PREFIX}{homey_id}_"
    if unique_id.startswith(scoped_prefix):
        return None
    if unique_id_hub_prefix(unique_id):
        return None
    suffix = unique_id[len(UNIQUE_ID_PREFIX) :]
    return f"{scoped_prefix}{suffix}"


def should_use_multi_homey(
    *,
    active_hub_count: int,
    sticky_enabled: bool,
    registry_uses_hub_prefix: bool | None,
) -> bool:
    """Decide whether entity unique_ids should be hub-prefixed.

    Existing registry IDs are the compatibility source of truth:

    - Already prefixed → stay prefixed (even with one real hub and no flag).
      This is the 2.1.2 → 2.1.3 break: ignored discoveries used to count as
      hubs, so single-hub installs could already have prefixed IDs without
      ``multi_homey_enabled`` stored.
    - Already unprefixed and only one real hub → stay unprefixed, even if a
      stale ``multi_homey_enabled`` flag is set. Re-prefixing would orphan them.
    - Two or more real hubs → prefix (setup migrates unprefixed IDs in place).
    - No entities yet → prefix only for 2+ real hubs, or a sticky flag.

    Ignored discovery entries must not be included in ``active_hub_count``.
    """
    if registry_uses_hub_prefix is True:
        return True
    if active_hub_count > 1:
        return True
    if registry_uses_hub_prefix is False:
        return False
    if sticky_enabled:
        return True
    return False
