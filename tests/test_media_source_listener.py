"""Tests for the media source listener module."""

import pytest
import datetime
from http import HTTPStatus
import logging
from collections.abc import Generator
from unittest.mock import Mock
from contextlib import contextmanager

from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry, ConfigEntryState, ConfigFlow
from homeassistant.setup import async_setup_component
from homeassistant.components.media_player import MediaClass, MediaType
from homeassistant.components.media_source import (
    BrowseMediaSource,
    MediaSource,
    MediaSourceItem,
    PlayMedia,
)

from pytest_homeassistant_custom_component.common import (
    async_capture_events,
    MockConfigEntry,
    MockModule,
    mock_config_flow,
    mock_integration,
    mock_platform,
    async_fire_time_changed,
)
from pytest_homeassistant_custom_component.test_util.aiohttp import AiohttpClientMocker


from custom_components.journal_assistant.media_source_listener import (
    async_create_media_source_listener,
)

from .conftest import MEDIA_SOURCE_PREFIX, TEST_DOMAIN

_LOGGER = logging.getLogger(__name__)

TEST_EVENT_NAME = "my-listener"
TEST_CONFIG_ENTRY_ID = "test_config_entry_id"


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


@pytest.fixture(name="mock_config_flow", autouse=True)
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


@pytest.fixture(name="mock_media_source_platform", autouse=True)
async def mock_media_source_platform_fixture(
    hass: HomeAssistant, mock_integration: None, mock_media_source: MockMediaSource
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


@contextmanager
def create_media_source_listener(hass: HomeAssistant) -> Generator[None]:
    """Mock the media source listener."""
    unsub = async_create_media_source_listener(hass, TEST_DOMAIN, TEST_EVENT_NAME)
    try:
        yield
    finally:
        unsub()


async def test_empty_media_source(
    hass: HomeAssistant, mock_media_source: MockMediaSource
) -> None:
    """Test processing an empty media source."""

    events = async_capture_events(hass, TEST_EVENT_NAME)

    mock_media_source.browse_response = {
        None: BrowseMediaSource(
            domain=TEST_DOMAIN,
            identifier="id",
            media_class=MediaClass.ALBUM,
            media_content_type=MediaType.ALBUM,
            children=[],
            title="Root",
            can_expand=True,
            can_play=False,
        )
    }
    now = datetime.datetime.now()

    with create_media_source_listener(hass):
        async_fire_time_changed(hass, now + datetime.timedelta(minutes=90))
        await hass.async_block_till_done()

    assert len(events) == 0


async def test_process_new_media_content(
    hass: HomeAssistant,
    mock_media_source: MockMediaSource,
    aioclient_mock: AiohttpClientMocker,
) -> None:
    """Test processing new content from a media source."""

    events = async_capture_events(hass, TEST_EVENT_NAME)

    mock_media_source.browse_response = {
        None: BrowseMediaSource(
            domain=TEST_DOMAIN,
            identifier="id",
            media_class=MediaClass.ALBUM,
            media_content_type=MediaType.ALBUM,
            children=[
                BrowseMediaSource(
                    domain=TEST_DOMAIN,
                    identifier=f"{MEDIA_SOURCE_PREFIX}/image-content-1",
                    media_class=MediaClass.IMAGE,
                    media_content_type=MediaType.IMAGE,
                    title="Image 1",
                    can_expand=False,
                    can_play=True,
                )
            ],
            title="Root",
            can_expand=True,
            can_play=False,
        ),
    }
    mock_media_source.resolve_response = {
        "image-content-1": PlayMedia(
            url="http://localhost/image-1.jpg",
            mime_type="image/jpeg",
        ),
    }

    aioclient_mock.get(
        "http://localhost/image-1.jpg",
        content=b"image-content",
    )

    now = datetime.datetime.now()
    with create_media_source_listener(hass):
        async_fire_time_changed(hass, now + datetime.timedelta(minutes=90))
        await hass.async_block_till_done()

    assert len(events) == 1
    assert events[0].data == {
        "identifier": "media-source://test_domain/image-content-1",
        "media_class": MediaClass.IMAGE,
        "media_content_type": MediaType.IMAGE,
        "title": "Image 1",
        "sha256": "d2dfc251c1a7245d4eb7d95e5f815472c6dbcf7ee6690bbd7c1912f477b6c22a",
    }
    events.clear()

    # Run again and verify no additional event is fired since the hash has not changed
    with create_media_source_listener(hass):
        async_fire_time_changed(hass, now + datetime.timedelta(minutes=150))
        await hass.async_block_till_done()

    assert len(events) == 0

    # Update the content and run again
    aioclient_mock.clear_requests()
    aioclient_mock.get(
        "http://localhost/image-1.jpg",
        content=b"image-content-updated",
    )
    with create_media_source_listener(hass):
        async_fire_time_changed(hass, now + datetime.timedelta(minutes=190))
        await hass.async_block_till_done()

    assert len(events) == 1
    assert events[0].data == {
        "identifier": "media-source://test_domain/image-content-1",
        "media_class": MediaClass.IMAGE,
        "media_content_type": MediaType.IMAGE,
        "title": "Image 1",
        # Updated hash from last time
        "sha256": "61c2409c3b6069988794042a8f99cad60d3afaefdf0a64afb2cd59cc9a2b0d44",
    }


async def test_process_failure(
    hass: HomeAssistant,
    mock_media_source: MockMediaSource,
    aioclient_mock: AiohttpClientMocker,
) -> None:
    """Test the case where an error occurs while processing content."""

    events = async_capture_events(hass, TEST_EVENT_NAME)

    mock_media_source.browse_response = {
        None: BrowseMediaSource(
            domain=TEST_DOMAIN,
            identifier="id",
            media_class=MediaClass.ALBUM,
            media_content_type=MediaType.ALBUM,
            children=[
                BrowseMediaSource(
                    domain=TEST_DOMAIN,
                    identifier=f"{MEDIA_SOURCE_PREFIX}/image-content-1",
                    media_class=MediaClass.IMAGE,
                    media_content_type=MediaType.IMAGE,
                    title="Image 1",
                    can_expand=False,
                    can_play=True,
                )
            ],
            title="Root",
            can_expand=True,
            can_play=False,
        ),
    }
    mock_media_source.resolve_response = {
        "image-content-1": PlayMedia(
            url="http://localhost/image-1.jpg",
            mime_type="image/jpeg",
        ),
    }

    aioclient_mock.get(
        "http://localhost/image-1.jpg",
        status=HTTPStatus.INTERNAL_SERVER_ERROR,
    )

    now = datetime.datetime.now()
    with create_media_source_listener(hass):
        async_fire_time_changed(hass, now + datetime.timedelta(minutes=90))
        await hass.async_block_till_done()

    # The event should not be fired as the download failed
    assert len(events) == 0


async def test_nested_folders(
    hass: HomeAssistant,
    mock_media_source: MockMediaSource,
    aioclient_mock: AiohttpClientMocker,
) -> None:
    """Test processing new content from a media source."""

    events = async_capture_events(hass, TEST_EVENT_NAME)

    mock_media_source.browse_response = {
        None: BrowseMediaSource(
            domain=TEST_DOMAIN,
            identifier="id",
            media_class=MediaClass.ALBUM,
            media_content_type=MediaType.ALBUM,
            children=[
                BrowseMediaSource(
                    domain=TEST_DOMAIN,
                    identifier=f"{MEDIA_SOURCE_PREFIX}/folder-1",
                    media_class=MediaClass.ALBUM,
                    media_content_type=MediaType.ALBUM,
                    title="Folder 1",
                    can_expand=True,
                    can_play=False,
                )
            ],
            title="Root",
            can_expand=True,
            can_play=False,
        ),
        "folder-1": BrowseMediaSource(
            domain=TEST_DOMAIN,
            identifier="image-content-1",
            media_class=MediaClass.ALBUM,
            media_content_type=MediaType.ALBUM,
            children=[
                BrowseMediaSource(
                    domain=TEST_DOMAIN,
                    identifier=f"{MEDIA_SOURCE_PREFIX}/image-content-1",
                    media_class=MediaClass.IMAGE,
                    media_content_type=MediaType.IMAGE,
                    title="Image 1",
                    can_expand=False,
                    can_play=True,
                )
            ],
            title="Image 1",
            can_expand=True,
            can_play=False,
        ),
    }
    mock_media_source.resolve_response = {
        "image-content-1": PlayMedia(
            url="http://localhost/image-1.jpg",
            mime_type="image/jpeg",
        ),
    }

    aioclient_mock.get(
        "http://localhost/image-1.jpg",
        content=b"image-content",
    )

    now = datetime.datetime.now()
    with create_media_source_listener(hass):
        async_fire_time_changed(hass, now + datetime.timedelta(minutes=90))
        await hass.async_block_till_done()

    # Discovered a media item
    assert len(events) == 1
