"""Library for handling Journal Assistant storage."""

from pathlib import Path
import logging
from typing import cast

from ical.calendar import Calendar
from chromadb.errors import ChromaError

from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.config_entries import ConfigEntry

from .const import (
    DEFAULT_NOTE_NAME,
    CONF_NOTES,
    DOMAIN,
    CONF_CHROMADB_URL,
    CONF_API_KEY,
    CONF_CHROMADB_TENANT,
)
from .processing.journal import journal_from_yaml, write_journal_page_yaml
from .processing.vectordb import (
    VectorDB,
    indexable_notebooks_iterator,
    create_chromadb_client,
)
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
    return await hass.async_add_executor_job(  # type: ignore[no-any-return]
        journal_from_yaml,
        journal_storage_path(hass, entry.entry_id),
        set(entry.options[CONF_NOTES].split("\n")),
        DEFAULT_NOTE_NAME,
    )


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
    chromadb_url: str,
    tenant: str,
    api_key: str,
    entries: dict[str, Calendar],
) -> VectorDB:
    _LOGGER.debug("Creating VectorDB")
    try:
        client = create_chromadb_client(chromadb_url, tenant)
    except ChromaError as err:
        _LOGGER.error("Error creating ChromaDB client: %s", err)
        raise HomeAssistantError(f"Error creating ChromaDB client: {err}") from err
    vectordb = VectorDB(client, api_key)
    _LOGGER.debug("Upserting document index")
    for document_batch in indexable_notebooks_iterator(entries):
        vectordb.upsert_index(document_batch)
    return vectordb


async def create_vector_db(hass: HomeAssistant, entry: ConfigEntry) -> VectorDB:
    """Create a VectorDB instance."""
    entries = await load_journal_entries(hass, entry)
    return await hass.async_add_executor_job(  # type: ignore[no-any-return]
        _create_vector_db,
        entry.options[CONF_CHROMADB_URL],
        entry.options[CONF_CHROMADB_TENANT],
        entry.options[CONF_API_KEY],
        entries,
    )
