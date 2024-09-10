"""Tests for the journal_assistant component."""

import pytest

from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr

from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    async_mock_service,
)

from custom_components.journal_assistant.const import (
    DOMAIN,
)


@pytest.fixture(autouse=True)
def mock_setup_integration(config_entry: MockConfigEntry) -> None:
    """Setup the integration"""
