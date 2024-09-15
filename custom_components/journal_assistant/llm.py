"""LLM APIs for Journal Assistant."""

import logging

import yaml
import voluptuous as vol

from homeassistant.helpers.llm import API, LLMContext, APIInstance, async_register_api
from homeassistant.helpers import (
    config_validation as cv,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.llm import Tool, ToolInput
from homeassistant.util.json import JsonObjectType

from .const import DOMAIN
from .processing.vectordb import VectorDB
from .types import JournalAssistantConfigEntry

_LOGGER = logging.getLogger(__name__)

JOURNAL_DOMAIN = "calendar"
PROMPT = """The Journal Assistant API allows you to search the users journal.
When the user asks a question, you can call a tool to search their journal and
use the journal content to inform your response. The individual notes in the
journal are exposed as entities in the Home Assistant and are listed below.
"""
NUM_RESULTS = 5


async def async_register_llm_apis(
    hass: HomeAssistant, entry: JournalAssistantConfigEntry
) -> None:
    """Register LLM APIs for Journal Assistant."""

    async_register_api(hass, JournalLLMApi(hass, entry))


class VectorSearchTool(Tool):
    """Journal Assistant vector search tool."""

    name = "search_journal"
    description = "Perform a free-text vector search on the journal returning relevant document chunks."
    parameters = vol.Schema(
        {
            "query": cv.string,
        }
    )

    def __init__(self, db: VectorDB) -> None:
        """Initialize the tool."""
        self.db = db

    async def async_call(
        self, hass: HomeAssistant, tool_input: ToolInput, llm_context: LLMContext
    ) -> JsonObjectType:
        """Call the tool."""
        _LOGGER.debug("Calling search_journal tool with %s", tool_input.tool_args)
        query = tool_input.tool_args["query"]
        results = await hass.async_add_executor_job(self.db.query, query, NUM_RESULTS)
        _LOGGER.debug("Search results: %s", results)
        return {
            "query": query,
            "results": results,
        }


class JournalLLMApi(API):
    """Journal Assistant LLM API."""

    def __init__(self, hass: HomeAssistant, entry: JournalAssistantConfigEntry) -> None:
        """Initialize the LLM API."""
        self.hass = hass
        self.id = f"{DOMAIN}-{entry.entry_id}"
        self.name = entry.title
        self.db = entry.runtime_data

    async def async_get_api_instance(self, llm_context: LLMContext) -> APIInstance:
        """Return the instance of the API."""
        exposed_entities = _get_exposed_entities(self.hass)
        prompt = "\n".join([PROMPT, yaml.dump(list(exposed_entities.values()))])
        return APIInstance(
            api=self,
            api_prompt=prompt,
            llm_context=llm_context,
            tools=[VectorSearchTool(self.db)],
            # custom_serializer=_selector_serializer,
        )


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
