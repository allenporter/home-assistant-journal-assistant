"""A journal calendar component."""

import datetime
import logging
from pathlib import Path
import slugify

from ical.calendar import Calendar
from ical.journal import Journal
from ical.timeline import generic_timeline

from homeassistant.components.calendar import CalendarEntity, CalendarEvent
from homeassistant.const import CONF_NAME
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util import dt as dt_util

from .const import DOMAIN, CONF_NOTES
from .journal import journal_from_yaml

_LOGGER = logging.getLogger(__name__)

UPDATE_INTERVAL = datetime.timedelta(minutes=15)
STORAGE_PATH = f"{DOMAIN}/data"


def storage_path(hass: HomeAssistant) -> Path:
    """Return the storage path for yaml notebook files."""
    _LOGGER.debug("Calling storage_path")
    return Path(hass.config.path(STORAGE_PATH))


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the journal calendar component."""
    _LOGGER.debug("Setting up journal calendar component")
    entries = await hass.async_add_executor_job(
        journal_from_yaml,
        storage_path(hass),
        set(entry.options[CONF_NOTES].split("\n")),
    )

    for journal_name, calendar in entries.items():
        async_add_entities([JournalCalendar(entry, journal_name, calendar)])


class JournalCalendar(CalendarEntity):
    """A journal calendar component."""

    _attr_has_entity_name = True

    def __init__(
        self, entry: ConfigEntry, journal_name: str, calendar: Calendar
    ) -> None:
        """Initialize the journal calendar component."""
        self._attr_unique_id = f"{entry.entry_id}-{slugify.slugify(journal_name)}"
        self._entry = entry
        self._attr_name = entry.options[CONF_NAME] + ": " + journal_name
        self._calendar = calendar
        self._event: CalendarEvent | None = None

    @property
    def event(self) -> CalendarEvent | None:
        """Return the events of the calendar."""
        return self._event

    async def async_get_events(
        self,
        hass: HomeAssistant,
        start_date: datetime.datetime,
        end_date: datetime.datetime,
    ) -> list[CalendarEvent]:
        """Return calendar events within a datetime range."""
        events = generic_timeline(
            self._calendar.journal, start_date.tzinfo or dt_util.UTC
        ).overlapping(
            start_date,
            end_date,
        )
        return [_get_calendar_event(event) for event in events]

    async def async_update(self) -> None:
        """Update entity state with the next upcoming event."""
        now = dt_util.now()
        events = generic_timeline(
            self._calendar.journal, now.tzinfo or dt_util.UTC
        ).active_after(now)
        if event := next(events, None):
            self._event = _get_calendar_event(event)
        else:
            self._event = None


def _get_calendar_event(event: Journal) -> CalendarEvent:
    """Return a CalendarEvent from an API event."""
    start: datetime.datetime | datetime.date
    end: datetime.datetime | datetime.date
    if isinstance(event.start, datetime.datetime):
        start = dt_util.as_local(event.start)
        end = start + event.computed_duration
    else:
        start = event.start
        end = start + event.computed_duration

    return CalendarEvent(
        summary=event.summary or "",
        start=start,
        end=end,
        description=event.description,
        uid=event.uid,
    )
