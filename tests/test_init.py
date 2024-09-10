"""Tests for the journal_assistant component."""

from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant

from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
)


async def test_init(
    hass: HomeAssistant, config_entry: MockConfigEntry, setup_integration: None
) -> None:
    """Setup the integration"""

    assert config_entry.state is ConfigEntryState.LOADED

    assert await hass.config_entries.async_unload(config_entry.entry_id)
    await hass.async_block_till_done()

    assert (
        config_entry.state is ConfigEntryState.NOT_LOADED  # type: ignore[comparison-overlap]
    )
