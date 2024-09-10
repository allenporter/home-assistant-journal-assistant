"""Converter from yaml journal files to an RFC5545 Journal."""

from pathlib import Path

from ical.calendar import Calendar
from ical.journal import Journal
from .model import JournalPage, RapidLogEntry


JOURNAL_PREFIXES = {
    "Daily",
    "Monthly",
    "Weekly",
    "FutureLog",
}



def journal_from_yaml(storage_dir: Path) -> dict[str, Calendar]:
    """Convert a yaml journal to an RFC5545 Journal."""

    # Get the unique list of journal names
    journal_names = {
        filename.name.split("-")[0]
        for filename in storage_dir.glob("*.yaml")
    }

    journals = {}

    for journal_name in journal_names:

        # Load all pages from with the same journal prefix
        pages = []
        for filename in storage_dir.glob(f"{journal_name}-*.yaml"):
            with filename.open() as file:
                page = JournalPage.from_yaml(file.read())
            pages.append(page)

        dated_content = {}
        for page in pages:
            content = str(page.content)
            for note in page.records:
                if note.date is not None:
                    if note.date not in dated_content:
                        dated_content[note.date] = ""
                    dated_content[note.date] += note.content
                else:
                    content += note.content

        if journal_name not in journals:
            journals[journal_name] = Calendar()

        # Add a journal entry for each date
        calendar = journals[journal_name]
        for date, content in dated_content.items():
            journal = Journal()
            journal.dtstart = date
            journal.description = content
            calendar.journal.append(journal)

        journals[journal_name] = calendar

    return journals
