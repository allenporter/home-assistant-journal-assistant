"""Journal assistant button platform."""

import datetime
import logging


from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.components.button import ButtonEntity
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .types import JournalAssistantConfigEntry

_LOGGER = logging.getLogger(__name__)

UPDATE_INTERVAL = datetime.timedelta(minutes=15)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: JournalAssistantConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the journal sensor component."""
    async_add_entities([ProcessMediaButtonEntity(entry)], True)


class ProcessMediaButtonEntity(ButtonEntity):
    """A button that allows manual processing of media."""

    _attr_has_entity_name = True
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, entry: JournalAssistantConfigEntry) -> None:
        """Initialize the process media button entity."""
        self._attr_unique_id = f"{entry.entry_id}-process-media"
        self._processor = entry.runtime_data.media_source_processor
        self._attr_name = "Process Media"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry.entry_id)},
            "name": entry.title,
        }

    async def async_press(self) -> None:
        """Handle the button press."""
        self.hass.async_create_task(
            self._processor.async_process_media(datetime.datetime.now())
        )
