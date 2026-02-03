"""Converter from yaml journal files to an RFC5545 Journal."""

from pathlib import Path
import itertools
import datetime
import logging
import hashlib
from typing import cast
from collections.abc import Generator


from ical.calendar import Calendar
from ical.journal import Journal

import yaml

from homeassistant.util import dt as dt_util
from custom_components.journal_assistant.vectordb import IndexableDocument

from .model import JournalPage

_LOGGER = logging.getLogger(__name__)

__all__ = [
    "journal_from_yaml",
]

INDEX_BATCH_SIZE = 25


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
        content = ""
        if note.content:
            if note.status:
                content = f"- ({note.status}) {note.content}"
            else:
                content = f"- {note.content}"
        if note.entries:
            if content:
                content += "\n"
            content += "\n".join(f"  - {entry}" for entry in note.entries if entry)
        dated_content[note_date].append(content)
    return dated_content


def write_content(content: str, filename: Path) -> None:
    """Write content to a file."""
    with filename.open("w") as file:
        file.write(content)


def write_journal_page_yaml(
    storage_dir: Path,
    note_name: str,
    page: JournalPage,
) -> None:
    """Write a journal page yaml string to a yaml file."""
    if "-" not in note_name:
        raise ValueError(f"Note name must contain a '-' character: {note_name}")
    if not page.filename.startswith(note_name):
        raise ValueError(
            f"Note name must match page filename: {note_name} != {page.filename}"
        )
    storage_dir.mkdir(parents=True, exist_ok=True)
    filename = storage_dir / f"{note_name}.yaml"
    _LOGGER.debug("Writing journal page to %s", filename)
    content = cast(str, page.to_yaml())
    write_content(content, filename)


def journal_from_yaml(
    storage_dir: Path,
    allowed_notes: set[str],
    default_note_name: str,
) -> dict[str, Calendar]:
    """Convert a yaml journal to an RFC5545 Journal."""
    _LOGGER.debug("Loading journal content from %s", storage_dir)
    # Get the unique list of journal names
    filename_prefixes = {
        filename.name.split("-")[0] for filename in storage_dir.glob("*.yaml")
    }
    note_names = list(filename_prefixes)
    note_names.sort()
    _LOGGER.debug("Journal names: %s", note_names)

    journals = {}
    for note_name in note_names:
        # Load all pages from with the same journal prefix
        pages = journal_pages(storage_dir, note_name)

        # Allow notes to have their own calendar entry if in the list of allowed notes
        key_name = note_name if note_name in allowed_notes else default_note_name

        dated_content: dict[str, list[str]] = {}
        for page in pages:
            for date, content_list in get_dated_content(page).items():
                if date not in dated_content:
                    dated_content[date] = []
                dated_content[date].extend(content_list)

        if key_name not in journals:
            journals[key_name] = Calendar()

        # Add a journal entry for each date
        calendar = journals[key_name]
        for date, content_list in dated_content.items():
            journal = Journal()
            journal.uid = hashlib.sha256(f"{note_name}-{date}".encode()).hexdigest()
            journal.summary = f"{note_name} {date}"
            journal.categories = [key_name]
            if note_name not in allowed_notes:
                journal.categories.append(note_name)
            if "T" in date:
                journal.dtstart = datetime.datetime.fromisoformat(date)
            else:
                journal.dtstart = datetime.date.fromisoformat(date)
            journal.description = "\n".join(content_list)
            calendar.journal.append(journal)

        journals[key_name] = calendar

    return journals


def _serialize_content(item: Journal) -> str:
    """Serialize a journal entry."""
    return yaml.dump(
        item.dict(exclude={"uid", "dtsamp"}, exclude_unset=True, exclude_none=True)  # type: ignore[deprecated]
    )


def create_indexable_document(journal_entry: Journal) -> IndexableDocument:
    """Create an indexable document from a journal entry."""
    return IndexableDocument(
        uid=journal_entry.uid or "",
        document=_serialize_content(journal_entry),
        timestamp=dt_util.start_of_local_day(journal_entry.dtstart),
        metadata={
            "category": (next(iter(journal_entry.categories), "")),
            "name": journal_entry.summary or "",
        },
    )


def indexable_notebooks_iterator(
    notebooks: dict[str, Calendar], batch_size: int | None = None
) -> Generator[list[IndexableDocument]]:
    """Iterate over notebooks in batches."""
    total = sum(len(calendar.journal) for calendar in notebooks.values())
    count = 0
    for calendar in notebooks.values():
        for found_journal_entries in itertools.batched(
            calendar.journal, batch_size or INDEX_BATCH_SIZE
        ):
            count += len(found_journal_entries)
            _LOGGER.debug("Processing batch %s of %s", count, total)
            yield [
                create_indexable_document(journal_entry)
                for journal_entry in found_journal_entries
            ]
