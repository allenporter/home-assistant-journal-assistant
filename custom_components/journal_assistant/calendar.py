"""A journal calendar component."""

from homeassistant.components.calendar import CalendarEntity, CalendarEvent
from homeassistant.const import CONF_NAME
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities,
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

    async def async_get_events(self, *args, **kwargs) -> list[CalendarEvent]:
        """Get the events of the calendar."""
        return []
