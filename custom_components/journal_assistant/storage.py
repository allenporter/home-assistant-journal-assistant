"""Library for handling Journal Assistant storage."""

from pathlib import Path
import logging
from typing import cast

from ical.calendar import Calendar

from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry

from .const import DEFAULT_NOTE_NAME, CONF_NOTES, DOMAIN
from .processing.journal import journal_from_yaml
from .processing.vectordb import VectorDB

_LOGGER = logging.getLogger(__name__)

STORAGE_PATH = f"{DOMAIN}/data"


def journal_storage_path(hass: HomeAssistant) -> Path:
    """Return the storage path for yaml notebook files."""
    _LOGGER.debug("Calling storage_path")
    return Path(hass.config.path(STORAGE_PATH))


def vectordb_storage_path(hass: HomeAssistant) -> Path:
    """Return the storage path for yaml notebook files."""
    _LOGGER.debug("Calling storage_path")
    return Path(hass.config.path(STORAGE_PATH))


async def load_journal_entries(
    hass: HomeAssistant, entry: ConfigEntry
) -> dict[str, Calendar]:
    result = await hass.async_add_executor_job(
        journal_from_yaml,
        journal_storage_path(hass),
        set(entry.options[CONF_NOTES].split("\n")),
        DEFAULT_NOTE_NAME,
    )
    return cast(dict[str, Calendar], result)


def _create_vector_db(
    storage_path: Path, api_key: str, entries: dict[str, Calendar]
) -> VectorDB:
    vectordb = VectorDB(storage_path, api_key)
    vectordb.upsert_index(entries)
    return vectordb


async def create_vector_db(hass: HomeAssistant, entry: ConfigEntry) -> VectorDB:
    """Create a VectorDB instance."""
    entries = await load_journal_entries(hass, entry)
    vectordb = await hass.async_add_executor_job(
        _create_vector_db,
        vectordb_storage_path(hass),
        entry.options["api_key"],
        entries,
    )
    return cast(VectorDB, vectordb)