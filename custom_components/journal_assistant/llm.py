"""LLM APIs for Journal Assistant."""

import logging

import yaml
import voluptuous as vol

from homeassistant.helpers.llm import API, LLMContext, APIInstance, async_register_api
from homeassistant.helpers import (
    config_validation as cv,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.llm import Tool, ToolInput
from homeassistant.util.json import JsonObjectType

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

JOURNAL_DOMAIN = "calendar"
PROMPT = """The Journal Assistant API allows you to search the users journal.
When the user asks a question, you can call a tool to search their journal and
use the journal content to inform your response. The individual notes in the
journal are exposed as entities in the Home Assistant and are listed below.
"""


def async_register_llm_apis(hass: HomeAssistant) -> None:
    """Register LLM APIs for Journal Assistant."""
    async_register_api(hass, JournalLLMApi(hass))


class VectorSearchTool(Tool):
    """Journal Assistant vector search tool."""

    name = "search_journal"
    description = "Perform a free-text vector search on the journal returning relevant document chunks."
    parameters = vol.Schema(
        {
            "entity_id": cv.entity_id,
            "query": cv.string,
        }
    )

    async def async_call(
        self, hass: HomeAssistant, tool_input: ToolInput, llm_context: LLMContext
    ) -> JsonObjectType:
        """Call the tool."""
        entity_id = tool_input.tool_args["entity_id"]
        query = tool_input.tool_args["query"]
        return {
            "entity_id": entity_id,
            "query": query,
        }


class JournalLLMApi(API):
    """Journal Assistant LLM API."""

    id = DOMAIN
    name = "Journal Assistant"

    def __init__(self, hass: HomeAssistant) -> None:
        """Initialize the LLM API."""
        self.hass = hass

    async def async_get_api_instance(self, llm_context: LLMContext) -> APIInstance:
        """Return the instance of the API."""
        exposed_entities: dict | None = _get_exposed_entities(self.hass)
        return APIInstance(
            api=self,
            api_prompt=self._async_get_api_prompt(llm_context, exposed_entities),
            llm_context=llm_context,
            tools=self._async_get_tools(llm_context, exposed_entities),
            # custom_serializer=_selector_serializer,
        )

    @callback
    def _async_get_api_prompt(
        self, llm_context: LLMContext, exposed_entities: dict[str, dict[str, str]]
    ) -> str:
        """Return the prompt for the API."""
        return "\n".join([PROMPT, yaml.dump(list(exposed_entities.values()))])

    @callback
    def _async_get_tools(
        self, llm_context: LLMContext, exposed_entities: dict | None
    ) -> list[Tool]:
        """Return a list of LLM tools."""
        return [VectorSearchTool()]


def _get_exposed_entities(hass: HomeAssistant) -> dict[str, dict[str, str]]:
    """Get exposed journal entities."""
    entities: dict[str, dict[str, str]] = {}
    for state in hass.states.async_all():
        if state.domain != JOURNAL_DOMAIN:
            continue
        entities[state.entity_id] = {
            "entity_id": state.entity_id,
            "name": state.name,
        }
    return entities
