"""Tests for Journal Assistant services."""

import pytest
import voluptuous as vol
from unittest.mock import patch

from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ServiceValidationError
from homeassistant.components.media_source import (
    BrowseMediaSource,
    PlayMedia,
)

from custom_components.journal_assistant.const import DOMAIN
from custom_components.journal_assistant.processing.journal import JournalPage

from pytest_homeassistant_custom_component.common import MockConfigEntry
from pytest_homeassistant_custom_component.test_util.aiohttp import AiohttpClientMocker

from .conftest import MEDIA_SOURCE_PREFIX, MockMediaSource, TEST_DOMAIN


@pytest.fixture(autouse=True)
async def setup_testss(
    mock_media_source_platform: None,
) -> None:
    """Set up the tests pre-requisites."""
    pass


@pytest.mark.usefixtures("setup_integration")
async def test_process_media(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    mock_media_source: MockMediaSource,
    aioclient_mock: AiohttpClientMocker,
) -> None:
    """Test service call to process media content."""
    assert hass.services.has_service(DOMAIN, "process_media")

    mock_media_source.browse_response = {
        "Daily-01-P20221030210760068713clbdtpKcEWTi.note": BrowseMediaSource(
            domain=TEST_DOMAIN,
            identifier=f"{MEDIA_SOURCE_PREFIX}/Daily-01-P20221030210760068713clbdtpKcEWTi.note",
            media_class="image",
            media_content_type="image/jpeg",
            title="Daily-01-P20221030210760068713clbdtpKcEWTi",
            can_play=True,
            can_expand=False,
        )
    }
    mock_media_source.resolve_response = {
        "Daily-01-P20221030210760068713clbdtpKcEWTi.note": PlayMedia(
            url="http://localhost/Daily-01-P20221030210760068713clbdtpKcEWTi.png",
            mime_type="image/jpeg",
        ),
    }
    aioclient_mock.get(
        "http://localhost/Daily-01-P20221030210760068713clbdtpKcEWTi.png",
        content=b"image-content",
    )

    with patch(
        "custom_components.journal_assistant.VisionModel.process_journal_page"
    ) as mock_process, patch(
        "custom_components.journal_assistant.processing.journal.write_content"
    ):
        mock_process.return_value = JournalPage(
            filename="Daily-01-P20221030210760068713clbdtpKcEWTi.png",
            created_at="2022-10-30T21:07:00",
            label="daily",
            date="2022-10-30",
        )

        await hass.services.async_call(
            DOMAIN,
            "process_media",
            {
                "media_source": f"{MEDIA_SOURCE_PREFIX}/Daily-01-P20221030210760068713clbdtpKcEWTi.note",
                "config_entry_id": config_entry.entry_id,
            },
            blocking=True,
        )


@pytest.mark.usefixtures("setup_integration")
async def test_invalid_media_source_uri(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
) -> None:
    """Test service call with invalid media source URI."""
    assert hass.services.has_service(DOMAIN, "process_media")

    with pytest.raises(vol.Invalid):
        await hass.services.async_call(
            DOMAIN,
            "process_media",
            {
                "media_source": "invalid-media-source",
                "config_entry_id": config_entry.entry_id,
            },
            blocking=True,
        )


@pytest.mark.usefixtures("setup_integration")
async def test_invalid_config_entry(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
) -> None:
    """Test service call with invalid media source URI."""
    assert hass.services.has_service(DOMAIN, "process_media")

    with pytest.raises(ServiceValidationError, match="not found in registry"):
        await hass.services.async_call(
            DOMAIN,
            "process_media",
            {
                "media_source": f"{MEDIA_SOURCE_PREFIX}/Daily-01-P20221030210760068713clbdtpKcEWTi.note",
                "config_entry_id": "invalid-config-entry",
            },
            blocking=True,
        )


@pytest.mark.usefixtures("setup_integration")
async def test_process_journal_page(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
) -> None:
    """Test service call to process a journal page."""
    assert hass.services.has_service(DOMAIN, "process_media")

    with pytest.raises(ServiceValidationError, match="not found in registry"):
        await hass.services.async_call(
            DOMAIN,
            "process_media",
            {
                "media_source": f"{MEDIA_SOURCE_PREFIX}/Daily-01-P20221030210760068713clbdtpKcEWTi.note",
                "config_entry_id": "invalid-config-entry",
            },
            blocking=True,
        )
