"""Test a calendar entity."""

import pytest
from syrupy import SnapshotAssertion

from homeassistant.core import HomeAssistant

from pytest_homeassistant_custom_component.typing import (
    ClientSessionGenerator,
)


@pytest.mark.usefixtures("setup_integration")
async def test_calendar(
    hass: HomeAssistant,
    hass_client: ClientSessionGenerator,
    snapshot: SnapshotAssertion,
) -> None:
    """Test a calendar entity."""

    state = hass.states.get("sensor.my_journal_vector_db_count")
    assert state is not None
    assert state.state == "7"
