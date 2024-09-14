"""Journal assistant services."""

import re
from typing import Any

import voluptuous as vol

from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.config_entries import ConfigEntry
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers import config_validation as cv

from .const import CONF_MEDIA_SOURCE, CONF_CONFIG_ENTRY_ID, DOMAIN


MEDIA_SOURCE_URI_RE = re.compile(r"media-source://media_source/.+")


def ensure_media_source_uri(value: Any) -> str:
    """Validate that the value is media-source URI string."""
    value_str = str(value)
    if not MEDIA_SOURCE_URI_RE.search(value_str):
        raise vol.Invalid(
            f"The value should be a media source uri like media-source://media_source/<path>: {value}"
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

    if not hass.services.has_service(DOMAIN, PROCESS_MEDIA_SERVICE):
        hass.services.async_register(
            DOMAIN,
            PROCESS_MEDIA_SERVICE,
            async_process_media,
            schema=PROCESS_MEDIA_SERVICE_SCHEMA,
        )
