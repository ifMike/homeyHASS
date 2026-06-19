"""Support for Homey scenes."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.scene import Scene
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .device_info import build_entity_unique_id
from .homey_api import HomeyAPI

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Homey scenes and moods from a config entry."""
    api: HomeyAPI = hass.data[DOMAIN][entry.entry_id]["api"]

    homey_id = hass.data[DOMAIN][entry.entry_id].get("homey_id")
    multi_homey = hass.data[DOMAIN][entry.entry_id].get("multi_homey", False)
    entities = []
    
    # Add scenes
    scenes = await api.get_scenes()
    # Empty scenes dict is OK - user just doesn't have scenes configured
    for scene_id, scene in scenes.items():
        entities.append(
            HomeyScene(scene_id, scene, api, is_mood=False, homey_id=homey_id, multi_homey=multi_homey)
        )
    
    # Add moods (if available)
    moods = await api.get_moods()
    # Empty moods dict is OK - user just doesn't have moods configured or feature not available
    for mood_id, mood in moods.items():
        entities.append(
            HomeyScene(mood_id, mood, api, is_mood=True, homey_id=homey_id, multi_homey=multi_homey)
        )

    if entities:
        scene_count = len(scenes)
        mood_count = len(moods)
        _LOGGER.info("Created %d Homey scene entities (%d scenes, %d moods)", 
                     len(entities), scene_count, mood_count)
    else:
        _LOGGER.debug("No scenes or moods found - this is normal if you don't have any scenes/moods configured in Homey")
    async_add_entities(entities)


class HomeyScene(Scene):
    """Representation of a Homey scene."""

    def __init__(
        self,
        scene_id: str,
        scene: dict[str, Any],
        api: HomeyAPI,
        is_mood: bool = False,
        homey_id: str | None = None,
        multi_homey: bool = False,
    ) -> None:
        """Initialize the scene or mood."""
        self._scene_id = scene_id
        self._scene = scene
        self._api = api
        self._is_mood = is_mood
        self._homey_id = homey_id
        self._multi_homey = multi_homey
        
        if is_mood:
            self._attr_name = scene.get("name", "Unknown Mood")
            self._attr_unique_id = build_entity_unique_id(
                homey_id, scene_id, "mood", multi_homey
            )
            self._attr_icon = "mdi:emoticon-happy-outline"
        else:
            self._attr_name = scene.get("name", "Unknown Scene")
            self._attr_unique_id = build_entity_unique_id(
                homey_id, scene_id, "scene", multi_homey
            )
            self._attr_icon = "mdi:palette"

    async def async_activate(self, **kwargs: Any) -> None:
        """Activate the scene or mood."""
        if self._is_mood:
            success = await self._api.trigger_mood(self._scene_id)
            if not success:
                _LOGGER.error("Failed to activate Homey mood: %s", self._attr_name)
        else:
            success = await self._api.trigger_scene(self._scene_id)
            if not success:
                _LOGGER.error("Failed to activate Homey scene: %s", self._attr_name)
