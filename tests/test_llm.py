"""Tests for the Journal Assistant LLM API."""

import pytest

from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.llm import (
    LLMContext,
    ToolInput,
    async_get_api,
)


@pytest.mark.usefixtures("setup_integration")
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
        == """The Journal Assistant API allows you to search the users journal.
When the user asks a question, you can call a tool to search their journal and
use the journal content to inform your response. The individual notes in the
journal are exposed as entities in the Home Assistant and are listed below.

- entity_id: calendar.my_journal_daily
  name: 'My Journal: Daily'
- entity_id: calendar.my_journal_journal
  name: 'My Journal: Journal'
- entity_id: calendar.my_journal_monthly
  name: 'My Journal: Monthly'
"""
    )

    assert len(llm_api.tools) == 1
    assert llm_api.tools[0].name == "search_journal"
    assert llm_api.tools[0].description

    tool_input = ToolInput(
        tool_name="search_journal",
        tool_args={"entity_id": "calendar.my_journal_daily", "query": "today"},
    )
    function_response = await llm_api.async_call_tool(tool_input)
    assert function_response == {
        "query": "today",
        "results": [
            {
                "content": "document",
                "id": "098f6bcd4621d373cade4e832627b4f6",
                "notebook": "Daily",
            },
        ],
    }
