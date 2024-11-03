"""Library for handling Journal Assistant storage."""

import asyncio
from pathlib import Path
import logging

from ical.calendar import Calendar

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
from .processing.journal import (
    journal_from_yaml,
    write_journal_page_yaml,
    indexable_notebooks_iterator,
)
from .processing.chromadb_vectordb import (
    create_chroma_db,
)
from .processing.model import JournalPage
from .vectordb import VectorDB, VectorDBError


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
    hass: HomeAssistant,
    chromadb_url: str,
    tenant: str,
    api_key: str,
    entries: dict[str, Calendar],
) -> VectorDB:
    _LOGGER.debug("Creating VectorDB")
    try:
        vectordb = create_chroma_db(hass, chromadb_url, tenant, api_key)
    except VectorDBError as err:
        _LOGGER.error("Error creating ChromaDB client: %s", err)
        raise HomeAssistantError(f"Error creating ChromaDB client: {err}") from err
    return vectordb


async def create_vector_db(hass: HomeAssistant, entry: ConfigEntry) -> VectorDB:
    """Create a VectorDB instance."""
    entries = await load_journal_entries(hass, entry)
    vectordb = await hass.async_add_executor_job(  # type: ignore[no-any-return]
        _create_vector_db,
        hass,
        entry.options[CONF_CHROMADB_URL],
        entry.options[CONF_CHROMADB_TENANT],
        entry.options[CONF_API_KEY],
        entries,
    )

    _LOGGER.debug("Upserting document index")
    tasks = []
    for document_batch in indexable_notebooks_iterator(entries):
        tasks.append(vectordb.upsert_index(document_batch))
    await asyncio.gather(*tasks)

    return vectordb
