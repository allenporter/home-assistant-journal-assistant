"""A journal calendar component."""

import datetime

from homeassistant.components.calendar import CalendarEntity, CalendarEvent
from homeassistant.const import CONF_NAME
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the journal calendar component."""
    async_add_entities([JournalCalendar(entry)])


class JournalCalendar(CalendarEntity):
    """A journal calendar component."""

    _attr_has_entity_name = True

    def __init__(self, entry: ConfigEntry) -> None:
        """Initialize the journal calendar component."""
        self._entry = entry
        self._attr_name = entry.data[CONF_NAME]

    @property
    def event(self) -> CalendarEvent | None:
        """Return the events of the calendar."""
        return None

    async def async_get_events(
        self,
        hass: HomeAssistant,
        start_date: datetime.datetime,
        end_date: datetime.datetime,
    ) -> list[CalendarEvent]:
        """Return calendar events within a datetime range."""
        return []
