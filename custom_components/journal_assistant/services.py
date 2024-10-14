"""Journal assistant services."""

import re
from typing import Any
import pathlib
import logging

import aiohttp
import voluptuous as vol

from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.config_entries import ConfigEntry
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers import config_validation as cv, aiohttp_client
from homeassistant.components.media_source import (
    async_browse_media,
    async_resolve_media,
)
from homeassistant.components.media_player.browse_media import (
    async_process_play_media_url,
)

from .const import CONF_MEDIA_SOURCE, CONF_CONFIG_ENTRY_ID, DOMAIN
from .storage import save_journal_entry

_LOGGER = logging.getLogger(__name__)

MEDIA_SOURCE_URI_RE = re.compile(r"media-source://.+")


def ensure_media_source_uri(value: Any) -> str:
    """Validate that the value is media-source URI string."""
    value_str = str(value)
    if not MEDIA_SOURCE_URI_RE.search(value_str):
        raise vol.Invalid(
            f"The value should be a media source uri like media-source://<path>: {value}"
        )
    return value_str


PROCESS_MEDIA_SERVICE = "process_media"
PROCESS_MEDIA_SERVICE_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_MEDIA_SOURCE): vol.All(cv.string, ensure_media_source_uri),
        vol.Required(CONF_CONFIG_ENTRY_ID): cv.string,
    }
)


def async_register_services(hass: HomeAssistant) -> None:
    """Register Journal Assistant services."""

    async def async_process_media(call: ServiceCall) -> None:
        """Generate content from text and optionally images."""
        config_entry: ConfigEntry | None = hass.config_entries.async_get_entry(
            call.data[CONF_CONFIG_ENTRY_ID]
        )
        if not config_entry:
            raise ServiceValidationError(
                translation_domain=DOMAIN,
                translation_key="integration_not_found",
                translation_placeholders={"target": DOMAIN},
            )

        identifier = call.data[CONF_MEDIA_SOURCE]
        browse = await async_browse_media(hass, identifier)
        if not browse:
            raise ServiceValidationError(
                translation_domain=DOMAIN,
                translation_key="media_source_not_found",
                translation_placeholders={"media_source": identifier},
            )
        play_media = await async_resolve_media(
            hass, identifier, target_media_player=None
        )
        if not play_media:
            raise ServiceValidationError(
                translation_domain=DOMAIN,
                translation_key="media_source_not_resolved",
                translation_placeholders={"media_source": identifier},
            )
        session = aiohttp_client.async_get_clientsession(hass)

        url = async_process_play_media_url(hass, play_media.url)
        _LOGGER.debug("Downloading content from %s", url)

        try:
            response = await session.request("get", url)
            response.raise_for_status()
        except aiohttp.ClientError as err:
            _LOGGER.error("Error downloading content: %s", str(err))
            raise ServiceValidationError(
                translation_domain=DOMAIN,
                translation_key="media_source_download_error",
                translation_placeholders={"media_source": identifier},
            ) from err
        try:
            content = await response.read()
        except aiohttp.ClientError as err:
            _LOGGER.error("Error reading content: %s", str(err))
            raise ServiceValidationError(
                translation_domain=DOMAIN,
                translation_key="media_source_download_error",
                translation_placeholders={"media_source": identifier},
            ) from err
        vision_model = config_entry.runtime_data.vision_model
        try:
            journal_page = await vision_model.process_journal_page(
                pathlib.Path(browse.title), content
            )
        except (ValueError, AttributeError) as err:
            _LOGGER.error("Error processing journal content: %s", err)
            raise ServiceValidationError(
                translation_domain=DOMAIN,
                translation_key="journal_page_processing_error",
                translation_placeholders={"media_source": identifier},
            ) from err

        await save_journal_entry(
            hass, config_entry.entry_id, browse.title, journal_page
        )

    if not hass.services.has_service(DOMAIN, PROCESS_MEDIA_SERVICE):
        hass.services.async_register(
            DOMAIN,
            PROCESS_MEDIA_SERVICE,
            async_process_media,
            schema=PROCESS_MEDIA_SERVICE_SCHEMA,
        )
