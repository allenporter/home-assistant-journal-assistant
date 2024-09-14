"""Tests for the config flow."""

from unittest.mock import patch

from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.core import HomeAssistant
from homeassistant.const import CONF_NAME


from custom_components.journal_assistant.const import (
    DOMAIN,
    CONF_MEDIA_SOURCE,
    CONF_NOTES,
    CONF_CONVERSATION_AGENT_ID,
)


async def test_select_device(
    hass: HomeAssistant,
) -> None:
    """Test selecting a device in the configuration flow."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result.get("type") is FlowResultType.FORM
    assert result.get("errors") is None

    with patch(
        f"custom_components.{DOMAIN}.async_setup_entry", return_value=True
    ) as mock_setup:
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                CONF_NAME: "Title",
                CONF_MEDIA_SOURCE: "media-source://example",
                CONF_CONVERSATION_AGENT_ID: "conversation_agent.example",
            },
        )
        await hass.async_block_till_done()

    assert result.get("type") is FlowResultType.CREATE_ENTRY
    assert result.get("title") == "Title"
    assert result.get("data") == {}
    assert result.get("options") == {
        CONF_NAME: "Title",
        CONF_MEDIA_SOURCE: "media-source://example",
        CONF_NOTES: "Daily\nWeekly\nMonthly",
        CONF_CONVERSATION_AGENT_ID: "conversation_agent.example",
    }
    assert len(mock_setup.mock_calls) == 1
