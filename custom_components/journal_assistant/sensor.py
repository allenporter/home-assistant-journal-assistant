"""Journal assistant sensor platform."""

import datetime
import logging


from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.components.sensor import SensorEntity
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
    async_add_entities([VectorDBCountSensorEntity(entry)], True)


class VectorDBCountSensorEntity(SensorEntity):
    """A sensor for the number of entries in the vector db index."""

    _attr_has_entity_name = True
    _attr_state_class = "measurement"
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, entry: JournalAssistantConfigEntry) -> None:
        """Initialize the vector db count sensor."""
        self._attr_unique_id = f"{entry.entry_id}-vector-db-count"
        self._db = entry.runtime_data
        self._attr_name = "Vector DB Count"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry.entry_id)},
            "name": entry.title,
        }

    def update(self) -> None:
        """Update the sensor state."""
        self._attr_native_value = self._db.count()
