"""Library for handling Journal Assistant storage."""

from pathlib import Path
import logging
from typing import cast

from ical.calendar import Calendar

from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry

from .const import DEFAULT_NOTE_NAME, CONF_NOTES, DOMAIN
from .processing.journal import journal_from_yaml, write_journal_page_yaml
from .processing.vectordb import VectorDB, indexable_notebooks_iterator
from .processing.model import JournalPage

_LOGGER = logging.getLogger(__name__)

VECTOR_DB_STORAGE_PATH = f".storage/{DOMAIN}/{{config_entry_id}}/vectordb"
JOURNAL_STORAGE_PATH = f".storage/{DOMAIN}/{{config_entry_id}}/journal"


def journal_storage_path(hass: HomeAssistant, config_entry_id: str) -> Path:
    """Return the storage path for yaml notebook files."""
    _LOGGER.debug("Calling storage_path")
    return Path(
        hass.config.path(JOURNAL_STORAGE_PATH.format(config_entry_id=config_entry_id))
    )


def vectordb_storage_path(hass: HomeAssistant, config_entry_id: str) -> Path:
    """Return the storage path for yaml notebook files."""
    _LOGGER.debug("Calling storage_path")
    return Path(
        hass.config.path(VECTOR_DB_STORAGE_PATH.format(config_entry_id=config_entry_id))
    )


async def load_journal_entries(
    hass: HomeAssistant, entry: ConfigEntry
) -> dict[str, Calendar]:
    result = await hass.async_add_executor_job(
        journal_from_yaml,
        journal_storage_path(hass, entry.entry_id),
        set(entry.options[CONF_NOTES].split("\n")),
        DEFAULT_NOTE_NAME,
    )
    return cast(dict[str, Calendar], result)


async def save_journal_entry(
    hass: HomeAssistant,
    config_entry_id: str,
    note_name: str,
    page: JournalPage,
) -> None:
    await hass.async_add_executor_job(
        write_journal_page_yaml,
        journal_storage_path(hass, config_entry_id),
        note_name,
        page,
    )


def _create_vector_db(
    storage_path: Path, api_key: str, entries: dict[str, Calendar]
) -> VectorDB:
    _LOGGER.debug("Creating VectorDB")
    vectordb = VectorDB(storage_path, api_key)
    _LOGGER.debug("Upserting document index")
    for document_batch in indexable_notebooks_iterator(entries):
        vectordb.upsert_index(document_batch)
    return vectordb


async def create_vector_db(hass: HomeAssistant, entry: ConfigEntry) -> VectorDB:
    """Create a VectorDB instance."""
    entries = await load_journal_entries(hass, entry)
    vectordb = await hass.async_add_executor_job(
        _create_vector_db,
        vectordb_storage_path(hass, entry.entry_id),
        entry.options["api_key"],
        entries,
    )
    return cast(VectorDB, vectordb)
