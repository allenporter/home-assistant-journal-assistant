"""Processes a media source as a Bullet Journal.

This module is used to process a media source as a Bullet Journal. It extracts
text from the media source using a vision model and updates the vector database
with new journal entries.
"""

from homeassistant.core import HomeAssistant, CALLBACK_TYPE

from .media_source_listener import async_create_media_source_listener
from .const import DOMAIN

DATA_KEY = "bullet_journal_processor"


def async_register(
    hass: HomeAssistant, config_entry_id: str, media_source_domain: str
) -> CALLBACK_TYPE:
    """Register the media source listener."""
    listener_id = f"{DOMAIN}_{config_entry_id}"

    return async_create_media_source_listener(hass, media_source_domain, listener_id)
