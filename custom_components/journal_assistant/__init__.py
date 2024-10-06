"""journal_assistant custom component."""

from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

import google.generativeai as genai

from . import bullet_journal_processor
from .const import DOMAIN, CONF_MEDIA_SOURCE, VISION_MODEL_NAME, CONF_API_KEY
from .services import async_register_services
from .llm import async_register_llm_apis
from .types import JournalAssistantConfigEntry, JournalAssistantData
from .storage import create_vector_db
from .processing.vision_model import VisionModel

__all__ = [
    "DOMAIN",
]

_LOGGER = logging.getLogger(__name__)


PLATFORMS = (Platform.CALENDAR, Platform.SENSOR)


async def async_setup_entry(
    hass: HomeAssistant, entry: JournalAssistantConfigEntry
) -> bool:
    """Set up a config entry."""
    genai.configure(api_key=entry.options[CONF_API_KEY])
    model = genai.GenerativeModel(model_name=VISION_MODEL_NAME)
    vector_db = await create_vector_db(hass, entry)
    entry.runtime_data = JournalAssistantData(
        vector_db=vector_db,
        vision_model=VisionModel(model),
    )
    await hass.config_entries.async_forward_entry_setups(
        entry,
        platforms=PLATFORMS,
    )
    async_register_services(hass)
    await async_register_llm_apis(hass, entry)

    entry.async_on_unload(
        bullet_journal_processor.async_register(
            hass, entry.entry_id, entry.options[CONF_MEDIA_SOURCE]
        )
    )
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(
        entry,
        PLATFORMS,
    )
