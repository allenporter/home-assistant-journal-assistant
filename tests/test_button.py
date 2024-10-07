"""Test a button entity."""

import pytest

from homeassistant.core import HomeAssistant
from homeassistant.const import Platform


@pytest.fixture(name="platforms")
def mock_platforms_fixture() -> list[Platform]:
    """Fixture for platforms loaded by the integration."""
    return [Platform.BUTTON]


@pytest.mark.usefixtures("config_entry")
async def test_button(
    hass: HomeAssistant,
) -> None:
    """Test a calendar entity."""

    state = hass.states.get("button.my_journal_process_media")
    assert state is not None
    assert state.state == "unknown"
