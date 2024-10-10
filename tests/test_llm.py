"""Tests for the Journal Assistant LLM API."""

import pytest

from homeassistant.core import HomeAssistant
from homeassistant.const import Platform
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.llm import (
    LLMContext,
    ToolInput,
    async_get_api,
)


@pytest.fixture(name="platforms")
def mock_platforms_fixture() -> list[Platform]:
    """Fixture for platforms loaded by the integration."""
    return [Platform.CALENDAR]


@pytest.mark.usefixtures("config_entry")
async def test_journal_llm_api(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
) -> None:
    """Test the Journal Assistant LLM API is registered."""

    llm_context = LLMContext(
        platform="assistant",
        context=None,
        user_prompt="What's on my todo list today?",
        language="en",
        assistant=None,
        device_id=None,
    )
    llm_api = await async_get_api(
        hass,
        f"journal_assistant-{config_entry.entry_id}",
        llm_context,
    )
    assert (
        llm_api.api_prompt
        == """You are a Journal Assistant for a user following the Bullet Journal method and you have access to their notebook.

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
tasks, events, or other observations.  Tasks within the Bullet Journal method
can then fall within any of the logs used depending on where they fall in the
author's timeline. Typically, journals contain a Daily Log, Weekly Log, a
Monthly Log.

When the user asks a question, you can call a tool to search their journal and
use the journal content to inform your response. The individual notes in the
journal are exposed as entities in the Home Assistant and are listed below.

- entity_id: calendar.my_journal_daily
  name: My Journal Daily
- entity_id: calendar.my_journal_journal
  name: My Journal Journal
- entity_id: calendar.my_journal_monthly
  name: My Journal Monthly
"""
    )

    assert len(llm_api.tools) == 1
    assert llm_api.tools[0].name == "search_journal"
    assert llm_api.tools[0].description

    tool_input = ToolInput(
        tool_name="search_journal",
        tool_args={"query": "today"},
    )
    function_response = await llm_api.async_call_tool(tool_input)
    assert function_response == {
        "query": {"query": "today", "num_results": 10},
        "results": [
            {
                "content": "document",
                "id": "9f86d081884c7d659a2feaa0c55ad015a3bf4f1b2b0b822cd15d6c15b0f00a08",
                "notebook": "Daily",
            },
        ],
    }
