"""Tests for the Journal Assistant LLM API."""

import pytest

from voluptuous_openapi import convert
from syrupy import SnapshotAssertion

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
        f"journal_assistant-{config_entry.entry_id}",
        llm_context,
    )
    assert llm_api.api_prompt == snapshot

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
                "document": {
                    "uid": "9f86d081884c7d659a2feaa0c55ad015a3bf4f1b2b0b822cd15d6c15b0f00a08",
                    "document": "document",
                    "metadata": {"notebook": "Daily"},
                    "timestamp": "2021-01-01T12:34:00+00:00",
                },
                "score": 0.5,
            },
        ],
    }


@pytest.mark.usefixtures("config_entry")
async def test_llm_api_serialization(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    snapshot: SnapshotAssertion,
) -> None:
    """Test the that the LLM API is correctly serialized."""

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
    assert len(llm_api.tools) == 1
    assert convert(llm_api.tools[0].parameters) == snapshot


@pytest.mark.usefixtures("config_entry")
async def test_date_args(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    snapshot: SnapshotAssertion,
) -> None:
    """Test the Journal Assistant LLM API called with date args."""

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
    assert len(llm_api.tools) == 1
    assert llm_api.tools[0].name == "search_journal"
    assert llm_api.tools[0].description

    tool_input = ToolInput(
        tool_name="search_journal",
        tool_args={
            "query": "monthly review",
            "notebook_name": "Supernote Monthly",
            "date_range": {"start": "2024-09-01", "end": "2024-09-30"},
        },
    )
    function_response = await llm_api.async_call_tool(tool_input)
    assert function_response == {
        "query": {
            "metadata": {"category": "Supernote Monthly"},
            "start_date": "2024-09-01T00:00:00-06:00",
            "end_date": "2024-09-30T00:00:00-06:00",
            "num_results": 10,
            "query": "monthly review",
        },
        # Fake results not related to the query
        "results": [
            {
                "document": {
                    "uid": "9f86d081884c7d659a2feaa0c55ad015a3bf4f1b2b0b822cd15d6c15b0f00a08",
                    "document": "document",
                    "metadata": {"notebook": "Daily"},
                    "timestamp": "2021-01-01T12:34:00+00:00",
                },
                "score": 0.5,
            },
        ],
    }
