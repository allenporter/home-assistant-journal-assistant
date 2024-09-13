"""Converter from yaml journal files to an RFC5545 Journal."""

from pathlib import Path
import datetime
import logging

from ical.calendar import Calendar
from ical.journal import Journal
from .model import JournalPage


_LOGGER = logging.getLogger(__name__)


def journal_pages(storage_dir: Path, journal_name: str) -> list[JournalPage]:
    """Load all journal pages from a storage directory with the specified journal prefix."""
    pages = []
    files = list(storage_dir.glob(f"{journal_name}-*.yaml"))
    files.sort()
    for filename in files:
        with filename.open() as file:
            page = JournalPage.from_yaml(file.read())
        pages.append(page)
    return pages


def get_dated_content(page: JournalPage) -> dict[str, list[str]]:
    """Get the date and content from a journal page."""
    default_date = page.date or page.created_at
    if not page.records:
        return {default_date: [str(page.content)]}

    dated_content: dict[str, list[str]] = {}
    for note in page.records:
        note_date = note.date or default_date
        if note_date not in dated_content:
            dated_content[note_date] = []
        dated_content[note_date].append(f"- {note.content}")
    return dated_content


def journal_from_yaml(storage_dir: Path) -> dict[str, Calendar]:
    """Convert a yaml journal to an RFC5545 Journal."""
    _LOGGER.debug("Loading journal content from %s", storage_dir)
    # Get the unique list of journal names
    journal_names = {
        filename.name.split("-")[0] for filename in storage_dir.glob("*.yaml")
    }
    _LOGGER.debug("Journal names: %s", journal_names)

    journals = {}

    keys = list(journal_names)
    keys.sort()
    for journal_name in keys:

        # Load all pages from with the same journal prefix
        pages = journal_pages(storage_dir, journal_name)

        dated_content: dict[str, list[str]] = {}
        for page in pages:
            dated_content.update(get_dated_content(page))

        if journal_name not in journals:
            journals[journal_name] = Calendar()

        # Add a journal entry for each date
        calendar = journals[journal_name]
        for date, content_list in dated_content.items():
            journal = Journal()
            journal.summary = f"{journal_name} {date}"
            if "T" in date:
                journal.dtstart = datetime.datetime.fromisoformat(date)
            else:
                journal.dtstart = datetime.date.fromisoformat(date)
            journal.description = "\n".join(content_list)
            calendar.journal.append(journal)

        journals[journal_name] = calendar

    return journals
