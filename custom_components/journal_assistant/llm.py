"""LLM APIs for Journal Assistant."""

import datetime
import logging
from typing import cast

import yaml
import voluptuous as vol

from homeassistant.helpers.llm import API, LLMContext, APIInstance, async_register_api
from homeassistant.helpers import (
    config_validation as cv,
)
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.llm import Tool, ToolInput
from homeassistant.util.json import JsonObjectType
from homeassistant.util import dt as dt_util

from .const import DOMAIN
from .vectordb import VectorDB, QueryParams
from .types import JournalAssistantConfigEntry

_LOGGER = logging.getLogger(__name__)

JOURNAL_DOMAIN = "calendar"
PROMPT = """You are a Journal Assistant for a user following the Bullet Journal method and you have access to their notebook.

The Bullet Journal method is a system that combines elements of mindfulness,
productivity, and self-discovery. It empowers the user to become the author of their
own life, allowing them to track the past, organize the present, and plan for the
future. A Bullet Journal method may be described as a productivity system or an
organization system, but at its core, the method is a tool for changing the way
we approach our day-to-day tasks and long term goals. The Bullet Journal method
is centered on one key idea: intentionality. Why do we do what we do? What makes
these goals meaningful to us? What tasks are the most relevant to  us at any
given point in time?

Rapid logging is the language of the bullet journal method and entries may be
tasks, events, or other observationsTasks within the Bullet Journal method
can then fall within any of the logs used depending on where they fall in the
author's timeline. Typically, journals contain a Daily Log, Weekly Log, a
Monthly Log.

When the user asks a question, you can call a tool to search their journal and
use the journal content to inform your response. The individual notebooks within
the journal are named and exposed as entities in the Home Assistant and are
listed below.
"""
NUM_RESULTS = 10


async def async_register_llm_apis(
    hass: HomeAssistant, entry: JournalAssistantConfigEntry
) -> None:
    """Register LLM APIs for Journal Assistant."""

    # The config entry may be reloaded, but we only register a single LLM API.
    # We keep track of the id then lookup any details at runtime in case objects
    # on the config entry are reloaded or changed.
    try:
        async_register_api(
            hass, JournalLLMApi(hass, entry.title, entry.entry_id, entry.title)
        )
    except HomeAssistantError as err:
        _LOGGER.debug("Error registering Journal Assistant LLM APIs: %s", err)


class VectorSearchTool(Tool):
    """Journal Assistant vector search tool."""

    name = "search_journal"
    description = "Perform a free-text vector search on one or more journals returning relevant document chunks."
    parameters = vol.Schema(
        {
            vol.Required(
                "query",
                description="Free-text query used to search and rank document chunks across journals.",
            ): cv.string,
            vol.Optional(
                "notebook_name",
                description="Optional notebook name to restrict search results, otherwise searches all notebooks.",
            ): cv.string,
            vol.Optional(
                "date_range",
                description="Optional date range to restrict search within (inclusive), in ISO 8601 format.",
            ): vol.Schema(
                {
                    vol.Optional(
                        "start",
                        description="Only include document chunks on or after this date",
                    ): cv.date,
                    vol.Optional(
                        "end",
                        description="Only include document chunks on or before this date",
                    ): cv.date,
                }
            ),
        }
    )

    def __init__(self, db: VectorDB, entry_title: str) -> None:
        """Initialize the tool."""
        self._db = db
        self._entry_title = entry_title

    async def async_call(
        self, hass: HomeAssistant, tool_input: ToolInput, llm_context: LLMContext
    ) -> JsonObjectType:
        """Call the tool."""
        _LOGGER.debug("Calling search_journal tool with %s", tool_input.tool_args)
        args = self.parameters(tool_input.tool_args)
        query_params = QueryParams(
            query=args.get("query"),
            num_results=NUM_RESULTS,
        )
        if category := args.get("notebook_name"):
            if category.startswith(self._entry_title):
                category = category[len(self._entry_title) + 1 :]
            query_params.metadata = {"category": category}
        if args.get("date_range"):
            if start_date := args["date_range"].get("start"):
                if isinstance(start_date, str):
                    start_date = datetime.date.fromisoformat(start_date)  # type: ignore[unreachable]
                query_params.start_date = dt_util.start_of_local_day(start_date)
            if end_date := args["date_range"].get("end"):
                if isinstance(end_date, str):
                    end_date = datetime.date.fromisoformat(end_date)  # type: ignore[unreachable]
                query_params.end_date = dt_util.start_of_local_day(end_date)
        results = await self._db.query(query_params)
        _LOGGER.debug("Search results: %s", results)
        return cast(
            JsonObjectType,
            {
                "query": query_params.to_dict(omit_none=True),
                "results": [result.to_dict() for result in results],
            },
        )


class JournalLLMApi(API):
    """Journal Assistant LLM API."""

    def __init__(
        self, hass: HomeAssistant, name: str, entry_id: str, entry_title: str
    ) -> None:
        """Initialize the LLM API."""
        self.hass = hass
        self.id = f"{DOMAIN}-{entry_id}"
        self.name = name
        self._entry_id = entry_id
        self._entry_title = entry_title

    async def async_get_api_instance(self, llm_context: LLMContext) -> APIInstance:
        """Return the instance of the API."""
        config_entry: JournalAssistantConfigEntry = self.hass.config_entries.async_get_entry(self._entry_id)  # type: ignore[assignment]
        vector_db = config_entry.runtime_data.vector_db
        exposed_entities = _get_exposed_entities(self.hass)
        prompt = "\n".join([PROMPT, yaml.dump(list(exposed_entities.values()))])
        return APIInstance(
            api=self,
            api_prompt=prompt,
            llm_context=llm_context,
            tools=[VectorSearchTool(vector_db, self._entry_title)],
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
