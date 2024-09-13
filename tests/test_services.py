"""Tests for Journal Assistant services."""

import pytest
import voluptuous as vol

from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ServiceValidationError

from custom_components.journal_assistant.const import DOMAIN

from pytest_homeassistant_custom_component.common import MockConfigEntry


@pytest.mark.usefixtures("setup_integration")
async def test_process_media(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
) -> None:
    """Test service call to process media content."""
    assert hass.services.has_service(DOMAIN, "process_media")

    await hass.services.async_call(
        DOMAIN,
        "process_media",
        {
            "media_source": "media-source://media_source/doorbell_snapshot.jpg",
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
                "media_source": "media-source://media_source/doorbell_snapshot.jpg",
                "config_entry_id": "invalid-config-entry",
            },
            blocking=True,
        )
