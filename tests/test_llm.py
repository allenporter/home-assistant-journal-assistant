"""Tests for the Journal Assistant LLM API."""

import pytest
from syrupy import SnapshotAssertion

from homeassistant.core import HomeAssistant
from homeassistant.helpers.llm import (
    LLMContext,
    ToolInput,
    async_get_api,
)


@pytest.mark.usefixtures("setup_integration")
async def test_journal_llm_api(
    hass: HomeAssistant,
    snapshot: SnapshotAssertion,
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
        "journal_assistant",
        llm_context,
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
        "entity_id": "calendar.my_journal_daily",
        "query": "today",
    }
