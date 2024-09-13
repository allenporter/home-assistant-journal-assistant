"""Converter from yaml journal files to an RFC5545 Journal."""

from pathlib import Path
import datetime
import logging

from ical.calendar import Calendar
from ical.journal import Journal
from .model import JournalPage


_LOGGER = logging.getLogger(__name__)


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
        pages = []
        files = list(storage_dir.glob(f"{journal_name}-*.yaml"))
        files.sort()
        for filename in files:
            with filename.open() as file:
                page = JournalPage.from_yaml(file.read())
            pages.append(page)

        dated_content: dict[str, list[str]] = {}
        for page in pages:
            content = str(page.content)
            for note in page.records or ():
                if note.date is not None:
                    if note.date not in dated_content:
                        dated_content[note.date] = []
                    dated_content[note.date].append(f"- {note.content}")
                else:
                    content += note.content

        if journal_name not in journals:
            journals[journal_name] = Calendar()

        # Add a journal entry for each date
        calendar = journals[journal_name]
        for date, content_list in dated_content.items():
            journal = Journal()
            journal.summary = f"{journal_name} {date}"
            journal.dtstart = datetime.date.fromisoformat(date)
            journal.description = "\n".join(content_list)
            calendar.journal.append(journal)

        journals[journal_name] = calendar

    return journals
