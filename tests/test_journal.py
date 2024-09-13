"""Test parsing journal entries as a RFC5545 Journal."""

import datetime
from pathlib import Path

from custom_components.journal_assistant.journal import journal_from_yaml


def test_parse_journal_as_calendar() -> None:
    """Test parsing a journal page."""

    entries = journal_from_yaml(Path("tests/fixtures"))
    assert "Daily" in entries

    assert [entry.dtstart for entry in entries["Daily"].journal] == [
        datetime.date(2023, 12, 19),
        datetime.date(2023, 12, 20),
        datetime.date(2023, 12, 21),
        datetime.date(2023, 12, 22),
    ]
