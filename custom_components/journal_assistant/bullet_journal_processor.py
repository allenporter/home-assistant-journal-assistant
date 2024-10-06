"""Processes a media source as a Bullet Journal.

This module is used to process a media source as a Bullet Journal. It extracts
text from the media source using a vision model and updates the vector database
with new journal entries.
"""

from typing import Any
import logging

from homeassistant.core import HomeAssistant, CALLBACK_TYPE, Event

from .media_source_listener import async_create_media_source_listener
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


DATA_KEY = "bullet_journal_processor"


def async_register(
    hass: HomeAssistant, config_entry_id: str, media_source_domain: str
) -> CALLBACK_TYPE:
    """Register the media source listener."""
    listener_id = f"{DOMAIN}_{config_entry_id}"

    processor = BulletJournalProcessor(hass)
    cancel = hass.bus.async_listen(listener_id, processor.handle_event)
    unsub = async_create_media_source_listener(hass, media_source_domain, listener_id)

    def cleanup() -> None:
        """Clean up the media source listener."""
        cancel()
        unsub()

    return cleanup


class BulletJournalProcessor:
    """Library for processing a media source as a Bullet Journal."""

    def __init__(self, hass: HomeAssistant) -> None:
        """Initialize the Bullet Journal Processor."""
        self._hass = hass

    async def handle_event(self, event: Event[dict[str, Any]]) -> None:
        """Handle an updated media source object."""
        _LOGGER.info("Processing media source event: %s", event)
