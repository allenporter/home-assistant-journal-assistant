"""Test parsing journal entries as a RFC5545 Journal."""

from pathlib import Path

from syrupy import SnapshotAssertion

from custom_components.journal_assistant.processing.journal import journal_from_yaml


def test_parse_journal_as_calendar(snapshot: SnapshotAssertion) -> None:
    """Test parsing a journal page."""

    calendars = journal_from_yaml(
        Path("tests/fixtures"), {"Daily", "Monthly"}, "Journal"
    )
    assert calendars.keys() == {"Daily", "Journal", "Monthly"}
    assert [
        entry.dict(exclude={"uid", "dtstamp"}, exclude_none=True, exclude_unset=True)
        for calendar in calendars.values()
        for entry in calendar.journal
    ] == snapshot
