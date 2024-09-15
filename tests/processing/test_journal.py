"""Test parsing journal entries as a RFC5545 Journal."""

import datetime
from pathlib import Path

from custom_components.journal_assistant.processing.journal import journal_from_yaml


def test_parse_journal_as_calendar() -> None:
    """Test parsing a journal page."""

    entries = journal_from_yaml(Path("tests/fixtures"), {"Daily", "Monthly"}, "Journal")
    assert entries.keys() == {"Daily", "Journal", "Monthly"}
    uids = {
        entry.uid
        for calendar in entries.values()
        for entry in calendar.journal
    }
    # Assert that uids are stable so that re-indexing is efficient
    assert uids == {
       '1d01a07c85a81ede664bd214842c6be31292fffc34c36b2fcca5d808b079e47a',
       '3ac14d0bb8c28ac12733b156a5b96d6af62d3c3be63d488aa763a99637a407ce',
       '6adda50869fb7bfd3ffb4f6b49c75156f7735722b01bdc9b745dd21c3eff54ca',
       'b126a70824675efb8b8ce68fb86ecf7e1440460fea272f354da3ee61990425d2',
       'caba4b5990a778e89764bdb09f6902d6fc68a48d8fe96c1d9bbe4424d00af930',
       'cdb5cd2f9dae4dde73432f5bb694f77a538333ccaa1ab928985c0a0c5ac1d6dd',
    }

    assert [entry.dtstart for entry in entries["Daily"].journal] == [
        datetime.date(2023, 12, 19),
        datetime.date(2023, 12, 20),
        datetime.date(2023, 12, 21),
        datetime.date(2023, 12, 22),
    ]

    assert [entry.dtstart for entry in entries["Journal"].journal] == [
        datetime.datetime(2023, 12, 23, 17, 18, 11, 138118),
    ]

    assert [entry.dtstart for entry in entries["Monthly"].journal] == [
        datetime.date(2024, 4, 1),
    ]
