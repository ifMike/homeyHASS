"""Helpers for Home Assistant entity state constraints."""
from __future__ import annotations

# Home Assistant rejects entity states longer than this and logs the full value.
HA_STATE_MAX_LENGTH = 255

# Extra state attribute used when the live state is truncated.
ATTR_FULL_VALUE = "full_value"


def truncate_ha_state(value: str) -> tuple[str, str | None]:
    """Return a HA-safe state and optional full value for attributes.

    When the string fits in HA's state limit, returns ``(value, None)``.
    When it does not, returns a short state plus the original string so callers
    can expose it via ``extra_state_attributes`` (attributes are not limited
    to 255 characters).
    """
    if len(value) <= HA_STATE_MAX_LENGTH:
        return value, None

    stripped = value.lstrip()
    if stripped[:4].lower() == "<svg":
        return "svg", value

    # Keep total length at HA_STATE_MAX_LENGTH (ellipsis is one character).
    return f"{value[: HA_STATE_MAX_LENGTH - 1]}…", value


def state_attributes_for_truncated(full_value: str | None) -> dict[str, str]:
    """Build extra attributes when a state was truncated."""
    if full_value is None:
        return {}
    return {ATTR_FULL_VALUE: full_value}
