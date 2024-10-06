"""Processes a media source as a Bullet Journal.

This module is used to process a media source as a Bullet Journal. It extracts
text from the media source using a vision model and updates the vector database
with new journal entries.
"""

from homeassistant.core import HomeAssistant

from .media_source_listener import async_create_media_source_listener
from .const import DOMAIN

DATA_KEY = "bullet_journal_processor"


def async_register(
    hass: HomeAssistant, config_entry_id: str, media_source_domain: str
) -> None:
    """Register the media source listener."""
    listener_id = f"{DOMAIN}_{config_entry_id}"
    unsub = async_create_media_source_listener(hass, media_source_domain, listener_id)
    hass.data[DOMAIN].setdefault(DATA_KEY, {})
    hass.data[DOMAIN][DATA_KEY][config_entry_id] = unsub


def async_unregister(hass: HomeAssistant, config_entry_id: str) -> None:
    """Unregister the media source listener."""
    callbacks = hass.data[DOMAIN][DATA_KEY]
    if config_entry_id in callbacks:
        unsub = callbacks.pop(config_entry_id)
        unsub()
