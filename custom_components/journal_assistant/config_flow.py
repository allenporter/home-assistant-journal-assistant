"""Config flow for journal_assistant integration."""

from __future__ import annotations

import logging
from collections.abc import Mapping
from typing import Any, cast

import voluptuous as vol

from homeassistant.const import CONF_NAME
from homeassistant.helpers import (
    config_validation as cv,
    selector,
)
from homeassistant.helpers.schema_config_entry_flow import (
    SchemaConfigFlowHandler,
    SchemaFlowFormStep,
    SchemaCommonFlowHandler,
)
from .const import (
    DOMAIN,
    CONF_NOTES,
    DEFAULT_NOTES,
    CONF_API_KEY,
    CONF_MEDIA_SOURCE,
)

_LOGGER = logging.getLogger(__name__)


async def validate_user_input(
    handler: SchemaCommonFlowHandler, user_input: dict[str, Any]
) -> dict[str, Any]:
    """Validate user input."""
    handler.parent_handler._async_abort_entries_match(  # noqa: SLF001
        {CONF_NAME: user_input[CONF_NAME]}
    )
    return user_input


CONFIG_FLOW = {
    "user": SchemaFlowFormStep(
        vol.Schema(
            {
                vol.Required(CONF_NAME): cv.string,
                vol.Required(CONF_API_KEY): cv.string,
                vol.Required(CONF_MEDIA_SOURCE): selector.TextSelector(
                    selector.TextSelectorConfig(multiline=False)
                ),
                vol.Required(
                    CONF_NOTES, default="\n".join(DEFAULT_NOTES)
                ): selector.TextSelector(selector.TextSelectorConfig(multiline=True)),
            }
        ),
        validate_user_input=validate_user_input,
    )
}

OPTIONS_FLOW = {
    "init": SchemaFlowFormStep(),
}


class JournalAssistantConfigFlowHandler(SchemaConfigFlowHandler, domain=DOMAIN):
    """Handle a config flow for Switch as X."""

    config_flow = CONFIG_FLOW
    options_flow = OPTIONS_FLOW

    VERSION = 1
    MINOR_VERSION = 1

    def async_config_entry_title(self, options: Mapping[str, Any]) -> str:
        """Return config entry title."""
        return cast(str, options[CONF_NAME])
