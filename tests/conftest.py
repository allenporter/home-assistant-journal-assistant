"""Fixtures for the custom component."""

from collections.abc import Generator, AsyncGenerator
import logging
from unittest.mock import patch, Mock
from pathlib import Path
import hashlib


import pytest

from homeassistant.const import Platform, CONF_NAME
from homeassistant.core import HomeAssistant
from homeassistant.setup import async_setup_component

from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
)

from custom_components.journal_assistant.const import (
    DOMAIN,
    CONF_NOTES,
    CONF_API_KEY,
)

_LOGGER = logging.getLogger(__name__)

FIXTURES_DIR = Path("tests/fixtures/")
DOCUMENT_RESULT = {
    "id": hashlib.sha256("test".encode()).hexdigest(),
    "content": "document",
    "notebook": "Daily",
}


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(
    enable_custom_integrations: None,
) -> Generator[None, None, None]:
    """Enable custom integration."""
    _ = enable_custom_integrations  # unused
    yield


@pytest.fixture(name="platforms")
def mock_platforms() -> list[Platform]:
    """Fixture for platforms loaded by the integration."""
    return []


@pytest.fixture(name="journal_storage_path")
def mock_journal_storage_path() -> Generator[Path, None, None]:
    """Fake out the storage path to load from the fixtures directory."""
    with patch(
        f"custom_components.{DOMAIN}.storage.journal_storage_path",
        return_value=FIXTURES_DIR,
    ):
        yield FIXTURES_DIR


@pytest.fixture(name="mock_vectordb")
def mock_vectordb() -> Generator[Mock, None, None]:
    """Fixture to mock the VectorDB system."""
    with patch(
        f"custom_components.{DOMAIN}.storage.VectorDB",
    ) as mock_vectordb:
        mock_vectordb.return_value.query.return_value = [
            DOCUMENT_RESULT,
        ]
        yield mock_vectordb


@pytest.fixture(name="setup_integration")
async def mock_setup_integration(
    hass: HomeAssistant,
    journal_storage_path: Path,
    mock_vectordb: Mock,
    config_entry: MockConfigEntry,
    platforms: list[Platform],
) -> AsyncGenerator[None, None]:
    """Set up the integration."""

    with patch(f"custom_components.{DOMAIN}.PLATFORMS", platforms):
        assert await async_setup_component(hass, DOMAIN, {})
        await hass.async_block_till_done()
        yield


@pytest.fixture(name="config_entry")
async def mock_config_entry(
    hass: HomeAssistant,
) -> MockConfigEntry:
    """Fixture to create a configuration entry."""
    config_entry = MockConfigEntry(
        data={},
        domain=DOMAIN,
        options={
            CONF_NAME: "My Journal",
            CONF_NOTES: "Daily\nWeekly\nMonthly",
            CONF_API_KEY: "12345",
        },
        title="My Journal",
    )
    config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()
    return config_entry
