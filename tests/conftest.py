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
from homeassistant.components.media_source import (
    URI_SCHEME,
    BrowseMediaSource,
    MediaSource,
    MediaSourceItem,
    PlayMedia,
)
from homeassistant.config_entries import ConfigEntry, ConfigEntryState, ConfigFlow

from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    MockModule,
    mock_config_flow,
    mock_integration,
    mock_platform,
)

from custom_components.journal_assistant.const import (
    DOMAIN,
    CONF_NOTES,
    CONF_API_KEY,
    CONF_MEDIA_SOURCE,
)

_LOGGER = logging.getLogger(__name__)

TEST_DOMAIN = "test_domain"
MEDIA_SOURCE_PREFIX = f"{URI_SCHEME}{TEST_DOMAIN}"
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
        mock_vectordb.return_value.count.return_value = 7
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
            CONF_MEDIA_SOURCE: TEST_DOMAIN,
        },
        title="My Journal",
    )
    config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()
    return config_entry


@pytest.fixture(name="mock_integration")
def mock_integration_fixture(hass: HomeAssistant) -> None:
    """Fixture to set up a mock integration."""

    async def async_setup_entry_init(
        hass: HomeAssistant, config_entry: ConfigEntry
    ) -> bool:
        """Set up test config entry."""
        await hass.config_entries.async_forward_entry_setups(config_entry, [])
        return True

    async def async_unload_entry_init(
        hass: HomeAssistant,
        config_entry: ConfigEntry,
    ) -> bool:
        await hass.config_entries.async_unload_platforms(config_entry, [])
        return True

    mock_integration(
        hass,
        MockModule(
            TEST_DOMAIN,
            async_setup_entry=async_setup_entry_init,
            async_unload_entry=async_unload_entry_init,
        ),
    )


class MockFlow(ConfigFlow):
    """Test flow."""


@pytest.fixture(name="mock_media_source_config_flow")
def mock_config_flow_fixture(
    hass: HomeAssistant, mock_integration: None
) -> Generator[None]:
    """Fixture to set up a mock config flow."""

    mock_platform(hass, f"{TEST_DOMAIN}.config_flow")
    with mock_config_flow(TEST_DOMAIN, MockFlow):
        yield


class MockMediaSource(MediaSource):
    """A mock media source that returns faked responses."""

    name = "Supernote Cloud"

    def __init__(self) -> None:
        """Initialize the media source."""
        super().__init__(TEST_DOMAIN)
        self.resolve_response: dict[str | None, PlayMedia] = {}
        self.browse_response: dict[str | None, BrowseMediaSource] = {}

    async def async_resolve_media(self, item: MediaSourceItem) -> PlayMedia:
        """Resolve media identifier."""
        _LOGGER.debug("Resolving media %s", item.identifier)
        return self.resolve_response[item.identifier]

    async def async_browse_media(self, item: MediaSourceItem) -> BrowseMediaSource:
        """Return details about the media source."""
        _LOGGER.debug("Browsing media %s", item.identifier)
        return self.browse_response[item.identifier]


@pytest.fixture(name="mock_media_source", autouse=True)
def mock_media_source_fixture(hass: HomeAssistant) -> MockMediaSource:
    """Fixture to set up a mock media source."""
    return MockMediaSource()


@pytest.fixture(name="mock_media_source_platform")
async def mock_media_source_platform_fixture(
    hass: HomeAssistant,
    mock_integration: None,
    mock_media_source_config_flow: None,
    mock_media_source: MockMediaSource,
) -> None:
    """Fixture to set up a mock integration."""

    async def async_get_media_source(hass: HomeAssistant) -> MediaSource:
        return mock_media_source

    mock_media_source_platform = Mock()
    mock_media_source_platform.async_get_media_source = async_get_media_source
    mock_platform(
        hass,
        f"{TEST_DOMAIN}.media_source",
        mock_media_source_platform,
    )

    config_entry = MockConfigEntry(domain=TEST_DOMAIN)
    config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()
    assert config_entry.state is ConfigEntryState.LOADED

    await async_setup_component(hass, "media_source", {})
