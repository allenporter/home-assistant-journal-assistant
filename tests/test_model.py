"""Test parsing journal entries."""

from pathlib import Path

from custom_components.journal_assistant.model import JournalPage, RapidLogEntry
from custom_components.journal_assistant.const import DOMAIN


def test_journal_page() -> None:
    """Test parsing a journal page."""

    with Path("tests/fixtures/Daily-01.yaml").open() as file:
        page = JournalPage.from_yaml(file.read())
        assert page.date == "2023-12-19"
        assert page.label == "daily"
