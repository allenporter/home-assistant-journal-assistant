"""Tests for the media source listener module."""

import pytest
import datetime
from http import HTTPStatus
import logging
from typing import Any
from unittest.mock import Mock, patch, AsyncMock
from collections.abc import Generator

from homeassistant.core import HomeAssistant
from homeassistant.components.media_player import MediaClass, MediaType
from homeassistant.components.media_source import (
    BrowseMediaSource,
    PlayMedia,
)

from pytest_homeassistant_custom_component.common import (
    async_fire_time_changed,
)
from pytest_homeassistant_custom_component.test_util.aiohttp import AiohttpClientMocker

from .conftest import MEDIA_SOURCE_PREFIX, TEST_DOMAIN, MockMediaSource

_LOGGER = logging.getLogger(__name__)

TEST_EVENT_NAME = "my-listener"
TEST_CONFIG_ENTRY_ID = "test_config_entry_id"


@pytest.fixture(autouse=True)
async def setup_testss(
    mock_media_source_platform: None,
) -> None:
    """Set up the tests pre-requisites."""
    pass


@pytest.fixture(autouse=True, name="mock_process_item")
def mock_process_item_fixture() -> Generator[Mock]:
    """Mock the process item."""
    with patch(
        "custom_components.journal_assistant.ProcessMediaServiceCall"
    ) as mock_call:
        mock_call.return_value.process = AsyncMock()
        mock_call.return_value.process.return_value = True
        yield mock_call.return_value.process  # mock_process.return_value.process_item


async def test_empty_media_source(
    hass: HomeAssistant,
    mock_process_item: Mock,
    mock_media_source: MockMediaSource,
    setup_integration: Any,
) -> None:
    """Test processing an empty media source."""

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

    async_fire_time_changed(hass, now + datetime.timedelta(minutes=90))
    await hass.async_block_till_done()

    mock_process_item.assert_not_awaited()


async def test_process_new_media_content(
    hass: HomeAssistant,
    mock_process_item: Mock,
    mock_media_source: MockMediaSource,
    aioclient_mock: AiohttpClientMocker,
    setup_integration: Any,
    # config_entry: MockConfigEntry,
) -> None:
    """Test processing new content from a media source."""

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

    mock_process_item.assert_not_awaited()

    now = datetime.datetime.now()
    async_fire_time_changed(hass, now + datetime.timedelta(minutes=90))
    await hass.async_block_till_done()

    mock_process_item.assert_awaited()
    mock_process_item.reset_mock()

    # Run again and verify no additional event is fired since the hash has not changed
    async_fire_time_changed(hass, now + datetime.timedelta(minutes=150))
    await hass.async_block_till_done()

    mock_process_item.assert_not_awaited()

    # Update the content and run again
    aioclient_mock.clear_requests()
    aioclient_mock.get(
        "http://localhost/image-1.jpg",
        content=b"image-content-updated",
    )
    async_fire_time_changed(hass, now + datetime.timedelta(minutes=190))
    await hass.async_block_till_done()

    mock_process_item.assert_awaited()


async def test_process_failure(
    hass: HomeAssistant,
    mock_process_item: Mock,
    mock_media_source: MockMediaSource,
    aioclient_mock: AiohttpClientMocker,
    setup_integration: Any,
) -> None:
    """Test the case where an error occurs while processing content."""

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
    async_fire_time_changed(hass, now + datetime.timedelta(minutes=90))
    await hass.async_block_till_done()

    # The event should not be fired as the download failed
    mock_process_item.process.assert_not_awaited


async def test_nested_folders(
    hass: HomeAssistant,
    mock_process_item: Mock,
    mock_media_source: MockMediaSource,
    aioclient_mock: AiohttpClientMocker,
    setup_integration: Any,
) -> None:
    """Test processing new content from a media source."""
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
    async_fire_time_changed(hass, now + datetime.timedelta(minutes=90))
    await hass.async_block_till_done()

    # Discovered a media item
    mock_process_item.assert_awaited()
