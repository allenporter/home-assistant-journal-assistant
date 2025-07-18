"""journal_assistant custom component."""

from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from google import genai

from .const import DOMAIN, CONF_MEDIA_SOURCE, VISION_MODEL_NAME, CONF_API_KEY
from .services import async_register_services
from .llm import async_register_llm_apis
from .types import JournalAssistantConfigEntry, JournalAssistantData
from .storage import create_vector_db
from .processing.vision_model import VisionModel
from .media_source_processor import MediaSourceProcessor, ProcessMediaServiceCall

__all__ = [
    "DOMAIN",
]

_LOGGER = logging.getLogger(__name__)


PLATFORMS = (Platform.BUTTON, Platform.CALENDAR, Platform.SENSOR)


async def async_setup_entry(
    hass: HomeAssistant, entry: JournalAssistantConfigEntry
) -> bool:
    """Set up a config entry."""
    client = genai.Client(api_key=entry.options[CONF_API_KEY])
    vision_model = VisionModel(client, VISION_MODEL_NAME)
    vector_db = await create_vector_db(hass, entry, vision_model)

    media_source = entry.options[CONF_MEDIA_SOURCE]
    processor = MediaSourceProcessor(
        hass,
        entry.entry_id,
        media_source,
        ProcessMediaServiceCall(entry.entry_id),
    )

    entry.runtime_data = JournalAssistantData(
        vector_db=vector_db,
        vision_model=VisionModel(client, VISION_MODEL_NAME),
        media_source_processor=processor,
    )
    await hass.config_entries.async_forward_entry_setups(
        entry,
        platforms=PLATFORMS,
    )

    async_register_services(hass)

    await processor.async_attach()
    entry.async_on_unload(processor.async_detach)

    await async_register_llm_apis(hass, entry)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(
        entry,
        PLATFORMS,
    )


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload the config entry when it changed."""
    await hass.config_entries.async_reload(entry.entry_id)
