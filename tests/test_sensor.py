"""Test a calendar entity."""

import pytest

from homeassistant.core import HomeAssistant
from homeassistant.const import Platform


@pytest.fixture(name="platforms")
def mock_platforms_fixture() -> list[Platform]:
    """Fixture for platforms loaded by the integration."""
    return [Platform.SENSOR]


@pytest.mark.usefixtures("config_entry")
async def test_vector_db_count(
    hass: HomeAssistant,
) -> None:
    """Test a sensor for vector db count."""

    state = hass.states.get("sensor.my_journal_vector_db_count")
    assert state is not None
    assert state.state == "7"


@pytest.mark.usefixtures("config_entry")
@pytest.mark.parametrize(
    ("entity_id", "expected_state"),
    [
        ("sensor.my_journal_scanned_folders", "0"),
        ("sensor.my_journal_scanned_files", "0"),
        ("sensor.my_journal_processed_files", "0"),
        ("sensor.my_journal_skipped_items", "0"),
        ("sensor.my_journal_errors", "0"),
        ("sensor.my_journal_last_scan_start", "unknown"),
        ("sensor.my_journal_last_scan_end", "unknown"),
    ],
)
async def test_scan_stats(
    hass: HomeAssistant,
    entity_id: str,
    expected_state: str,
) -> None:
    """Test sensor entity exposed for scanner stats."""

    state = hass.states.get(entity_id)
    assert state is not None
    assert state.state == expected_state
