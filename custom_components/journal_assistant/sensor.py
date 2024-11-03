"""Journal assistant sensor platform."""

import datetime
import logging
from dataclasses import dataclass
from collections.abc import Callable, Awaitable
from typing import Any


from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.components.sensor import (
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .types import JournalAssistantConfigEntry, JournalAssistantData

_LOGGER = logging.getLogger(__name__)

UPDATE_INTERVAL = datetime.timedelta(minutes=15)


@dataclass(frozen=True, kw_only=True)
class JournalAssistantSensorEntityDescription(SensorEntityDescription):
    """Describes Journal Assistant sensor entity."""

    key: str
    icon: str = "mdi:counter"
    value_fn: Callable[[JournalAssistantData], Any] = lambda entry: None

    @property
    def unique_id(self) -> str:
        """Return a unique id for the entity."""
        return f"{DOMAIN}_{self.key}"


SENSOR_DESCRIPTIONS = [
    JournalAssistantSensorEntityDescription(
        key="vector_db_count",
        translation_key="vector_db_count",
        value_fn=lambda data: data.vector_db.count(),
        state_class=SensorStateClass.MEASUREMENT,
    ),
    JournalAssistantSensorEntityDescription(
        key="scanned_folders",
        icon="mdi:folder",
        translation_key="scanned_folders",
        value_fn=lambda data: data.media_source_processor.scan_stats.scanned_folders,
        state_class=SensorStateClass.TOTAL,
    ),
    JournalAssistantSensorEntityDescription(
        key="scanned_files",
        icon="mdi:file_copy",
        translation_key="scanned_files",
        state_class=SensorStateClass.TOTAL,
        value_fn=lambda data: data.media_source_processor.scan_stats.scanned_files,
    ),
    JournalAssistantSensorEntityDescription(
        key="processed_files",
        icon="mdi:perm_media",
        translation_key="processed_files",
        value_fn=lambda data: data.media_source_processor.scan_stats.processed_files,
        state_class=SensorStateClass.TOTAL,
    ),
    JournalAssistantSensorEntityDescription(
        key="skipped_items",
        icon="mdi:skip-next",
        translation_key="skipped_items",
        value_fn=lambda data: data.media_source_processor.scan_stats.skipped_items,
        state_class=SensorStateClass.TOTAL,
    ),
    JournalAssistantSensorEntityDescription(
        key="errors",
        icon="mdi:running_with_errors",
        translation_key="errors",
        value_fn=lambda data: data.media_source_processor.scan_stats.errors,
        state_class=SensorStateClass.TOTAL,
    ),
    JournalAssistantSensorEntityDescription(
        key="last_scan_start",
        translation_key="last_scan_start",
        value_fn=lambda data: data.media_source_processor.scan_stats.last_scan_start,
    ),
    JournalAssistantSensorEntityDescription(
        key="last_scan_end",
        translation_key="last_scan_end",
        value_fn=lambda data: data.media_source_processor.scan_stats.last_scan_end,
    ),
]


async def async_setup_entry(
    hass: HomeAssistant,
    entry: JournalAssistantConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the journal sensor component."""
    async_add_entities(
        [VectorDBCountSensorEntity(entry, desc) for desc in SENSOR_DESCRIPTIONS], True
    )


class VectorDBCountSensorEntity(SensorEntity):
    """A sensor for the number of entries in the vector db index."""

    entity_description: JournalAssistantSensorEntityDescription
    _attr_has_entity_name = True
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(
        self,
        entry: JournalAssistantConfigEntry,
        desc: JournalAssistantSensorEntityDescription,
    ) -> None:
        """Initialize the vector db count sensor."""
        self.entity_description = desc
        self._attr_unique_id = f"{entry.entry_id}-{desc.key}"
        self._data = entry.runtime_data
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry.entry_id)},
            "name": entry.title,
        }

    async def async_update(self) -> None:
        """Update the sensor state."""
        task = self.entity_description.value_fn(self._data)
        if isinstance(task, Awaitable):
            task = await task
        self._attr_native_value = task
