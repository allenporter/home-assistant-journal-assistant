"""journal_assistant custom component."""

from __future__ import annotations

import logging


from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from .const import DOMAIN
from .services import async_register_services
from .llm import async_register_llm_apis

__all__ = [
    "DOMAIN",
]

_LOGGER = logging.getLogger(__name__)


PLATFORMS: tuple[Platform] = (Platform.CALENDAR,)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up a config entry."""
    await hass.config_entries.async_forward_entry_setups(
        entry,
        platforms=PLATFORMS,
    )
    async_register_services(hass)
    async_register_llm_apis(hass)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(
        entry,
        PLATFORMS,
    )
