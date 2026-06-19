"""Support for Homey media players."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.media_player import (
    MediaPlayerEntity,
    MediaPlayerEntityFeature,
    MediaPlayerState,
)
from homeassistant.components.media_player.const import RepeatMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import HomeyDataUpdateCoordinator
from .device_info import build_entity_unique_id, get_device_info

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Homey media players from a config entry."""
    coordinator: HomeyDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    api = hass.data[DOMAIN][entry.entry_id]["api"]
    zones = hass.data[DOMAIN][entry.entry_id].get("zones", {})
    multi_homey = hass.data[DOMAIN][entry.entry_id].get("multi_homey", False)
    homey_id = hass.data[DOMAIN][entry.entry_id].get("homey_id")

    entities = []
    # Use coordinator data if available (more up-to-date), otherwise fetch fresh
    devices = coordinator.data if coordinator.data else await api.get_devices()
    
    # Filter devices if device_filter is configured
    from . import filter_devices
    devices = filter_devices(devices, entry.data.get("device_filter"))

    for device_id, device in devices.items():
        capabilities = device.get("capabilitiesObj", {})
        if any(
            cap in capabilities
            for cap in [
                "volume_set",
                "speaker_playing",
                "speaker_next",
                "speaker_prev",
                "speaker_shuffle",
                "speaker_repeat",
            ]
        ):
            entities.append(HomeyMediaPlayer(coordinator, device_id, device, api, zones, homey_id, multi_homey))

    async_add_entities(entities)


class HomeyMediaPlayer(CoordinatorEntity, MediaPlayerEntity):
    """Representation of a Homey media player."""

    def __init__(
        self,
        coordinator: HomeyDataUpdateCoordinator,
        device_id: str,
        device: dict[str, Any],
        api,
        zones: dict[str, dict[str, Any]] | None = None,
        homey_id: str | None = None,
        multi_homey: bool = False,
    ) -> None:
        """Initialize the media player."""
        super().__init__(coordinator)
        self._device_id = device_id
        self._device = device
        self._api = api
        self._homey_id = homey_id
        self._multi_homey = multi_homey
        self._attr_name = device.get("name", "Unknown Media Player")
        self._attr_unique_id = build_entity_unique_id(
            homey_id, device_id, "media_player", multi_homey
        )

        capabilities = device.get("capabilitiesObj", {})
        supported_features = 0

        if "volume_set" in capabilities:
            supported_features |= MediaPlayerEntityFeature.VOLUME_SET
        if "volume_mute" in capabilities:
            supported_features |= MediaPlayerEntityFeature.VOLUME_MUTE
        if "speaker_playing" in capabilities:
            supported_features |= MediaPlayerEntityFeature.PLAY | MediaPlayerEntityFeature.PAUSE
        if "speaker_next" in capabilities:
            supported_features |= MediaPlayerEntityFeature.NEXT_TRACK
        if "speaker_prev" in capabilities:
            supported_features |= MediaPlayerEntityFeature.PREVIOUS_TRACK
        if "speaker_shuffle" in capabilities:
            supported_features |= MediaPlayerEntityFeature.SHUFFLE_SET
        if "speaker_repeat" in capabilities:
            supported_features |= MediaPlayerEntityFeature.REPEAT_SET

        self._attr_supported_features = supported_features

        self._attr_device_info = get_device_info(
            self._homey_id, device_id, device, zones, self._multi_homey
        )

    @property
    def state(self) -> MediaPlayerState:
        """Return the state of the media player."""
        device_data = self.coordinator.data.get(self._device_id, self._device)
        capabilities = device_data.get("capabilitiesObj", {})
        playing = capabilities.get("speaker_playing", {}).get("value", False)
        return MediaPlayerState.PLAYING if playing else MediaPlayerState.IDLE

    @property
    def volume_level(self) -> float | None:
        """Return the volume level."""
        device_data = self.coordinator.data.get(self._device_id, self._device)
        capabilities = device_data.get("capabilitiesObj", {})
        volume = capabilities.get("volume_set", {}).get("value")
        return float(volume) if volume is not None else None

    @property
    def is_volume_muted(self) -> bool:
        """Return true if volume is muted."""
        device_data = self.coordinator.data.get(self._device_id, self._device)
        capabilities = device_data.get("capabilitiesObj", {})
        muted = capabilities.get("volume_mute", {}).get("value", False)
        return bool(muted)

    @property
    def media_artist(self) -> str | None:
        """Return the artist of current playing media."""
        device_data = self.coordinator.data.get(self._device_id, self._device)
        capabilities = device_data.get("capabilitiesObj", {})
        artist = capabilities.get("speaker_artist", {}).get("value")
        return str(artist) if artist is not None else None

    @property
    def media_album_name(self) -> str | None:
        """Return the album name of current playing media."""
        device_data = self.coordinator.data.get(self._device_id, self._device)
        capabilities = device_data.get("capabilitiesObj", {})
        album = capabilities.get("speaker_album", {}).get("value")
        return str(album) if album is not None else None

    @property
    def media_title(self) -> str | None:
        """Return the title of current playing media."""
        device_data = self.coordinator.data.get(self._device_id, self._device)
        capabilities = device_data.get("capabilitiesObj", {})
        track = capabilities.get("speaker_track", {}).get("value")
        return str(track) if track is not None else None

    @property
    def media_duration(self) -> int | None:
        """Return the duration of current playing media in seconds."""
        device_data = self.coordinator.data.get(self._device_id, self._device)
        capabilities = device_data.get("capabilitiesObj", {})
        duration = capabilities.get("speaker_duration", {}).get("value")
        if duration is not None:
            try:
                return int(float(duration))
            except (ValueError, TypeError):
                return None
        return None

    @property
    def media_position(self) -> int | None:
        """Return the current position of playing media in seconds."""
        device_data = self.coordinator.data.get(self._device_id, self._device)
        capabilities = device_data.get("capabilitiesObj", {})
        position = capabilities.get("speaker_position", {}).get("value")
        if position is not None:
            try:
                return int(float(position))
            except (ValueError, TypeError):
                return None
        return None

    @property
    def media_position_updated_at(self):
        """When was the position of the current playing media valid."""
        # Return current time if we have position data
        if self.media_position is not None:
            from homeassistant.util.dt import utcnow
            return utcnow()
        return None

    @property
    def shuffle(self) -> bool:
        """Return true if shuffle is enabled."""
        device_data = self.coordinator.data.get(self._device_id, self._device)
        capabilities = device_data.get("capabilitiesObj", {})
        value = capabilities.get("speaker_shuffle", {}).get("value", False)
        return bool(value)

    @property
    def repeat(self) -> RepeatMode | str | None:
        """Return the current repeat mode."""
        device_data = self.coordinator.data.get(self._device_id, self._device)
        capabilities = device_data.get("capabilitiesObj", {})
        value = capabilities.get("speaker_repeat", {}).get("value")
        if value is None:
            return None
        value_str = str(value).lower()
        if value_str in ("off", "false", "0"):
            return RepeatMode.OFF
        if value_str in ("one", "1"):
            return RepeatMode.ONE
        if value_str in ("all", "playlist"):
            return RepeatMode.ALL
        return RepeatMode.OFF

    async def async_media_play(self) -> None:
        """Send play command."""
        if "speaker_playing" in self._device.get("capabilitiesObj", {}):
            await self._api.set_capability_value(self._device_id, "speaker_playing", True)
            # Immediately refresh this device's state for instant UI feedback
            await self.coordinator.async_refresh_device(self._device_id)

    async def async_media_pause(self) -> None:
        """Send pause command."""
        if "speaker_playing" in self._device.get("capabilitiesObj", {}):
            await self._api.set_capability_value(self._device_id, "speaker_playing", False)
            # Immediately refresh this device's state for instant UI feedback
            await self.coordinator.async_refresh_device(self._device_id)

    async def async_media_next_track(self) -> None:
        """Send next track command."""
        if "speaker_next" in self._device.get("capabilitiesObj", {}):
            await self._api.set_capability_value(self._device_id, "speaker_next", True)
            # Immediately refresh this device's state for instant UI feedback
            await self.coordinator.async_refresh_device(self._device_id)

    async def async_media_previous_track(self) -> None:
        """Send previous track command."""
        if "speaker_prev" in self._device.get("capabilitiesObj", {}):
            await self._api.set_capability_value(self._device_id, "speaker_prev", True)
            # Immediately refresh this device's state for instant UI feedback
            await self.coordinator.async_refresh_device(self._device_id)

    async def async_set_volume_level(self, volume: float) -> None:
        """Set volume level.
        
        Home Assistant uses normalized volume (0.0-1.0).
        Homey API also uses normalized volume (0-1), so no conversion needed.
        """
        if "volume_set" in self._device.get("capabilitiesObj", {}):
            # Both HA and Homey use normalized 0-1 for volume, so pass through directly
            await self._api.set_capability_value(self._device_id, "volume_set", volume)
            # Immediately refresh this device's state for instant UI feedback
            await self.coordinator.async_refresh_device(self._device_id)

    async def async_mute_volume(self, mute: bool) -> None:
        """Mute or unmute volume."""
        if "volume_mute" in self._device.get("capabilitiesObj", {}):
            await self._api.set_capability_value(self._device_id, "volume_mute", mute)
            # Immediately refresh this device's state for instant UI feedback
            await self.coordinator.async_refresh_device(self._device_id)

    async def async_set_shuffle(self, shuffle: bool) -> None:
        """Enable or disable shuffle."""
        if "speaker_shuffle" in self._device.get("capabilitiesObj", {}):
            await self._api.set_capability_value(self._device_id, "speaker_shuffle", shuffle)
            await self.coordinator.async_refresh_device(self._device_id)

    async def async_set_repeat(self, repeat: RepeatMode) -> None:
        """Set repeat mode. Homey uses 'off', 'one', 'all'."""
        if "speaker_repeat" in self._device.get("capabilitiesObj", {}):
            homey_value = repeat.value if hasattr(repeat, "value") else str(repeat)
            await self._api.set_capability_value(self._device_id, "speaker_repeat", homey_value)
            await self.coordinator.async_refresh_device(self._device_id)

