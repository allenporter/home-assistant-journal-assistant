"""Test a calendar entity."""

from homeassistant.core import HomeAssistant


async def test_calendar(hass: HomeAssistant, setup_integration: None) -> None:
    """Test a calendar entity."""

    state = hass.states.get("calendar.my_journal")
    assert state is not None
    assert state.state == "off"
