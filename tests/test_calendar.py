"""Test a sensor entity."""

import urllib
from http import HTTPStatus

import pytest
from syrupy import SnapshotAssertion

from homeassistant.core import HomeAssistant
from homeassistant.const import Platform

from pytest_homeassistant_custom_component.typing import (
    ClientSessionGenerator,
)


@pytest.fixture(name="platforms")
def mock_platforms_fixture() -> list[Platform]:
    """Fixture for platforms loaded by the integration."""
    return [Platform.CALENDAR]


@pytest.mark.usefixtures("config_entry")
async def test_calendar(
    hass: HomeAssistant,
    hass_client: ClientSessionGenerator,
    snapshot: SnapshotAssertion,
) -> None:
    """Test a calendar entity."""

    state = hass.states.get("calendar.my_journal_daily")
    assert state is not None
    assert state.state == "off"
    assert dict(state.attributes) == {
        "friendly_name": "My Journal Daily",
    }

    start = "2023-12-01T00:00:00Z"
    end = "2023-12-31T23:59:59Z"
    client = await hass_client()
    response = await client.get(
        f"/api/calendars/calendar.my_journal_daily?start={urllib.parse.quote(start)}&end={urllib.parse.quote(end)}"
    )
    assert response.status == HTTPStatus.OK
    resp = await response.json()
    assert [
        (event["start"], event["end"], event["summary"], event["description"])
        for event in resp
    ] == snapshot
