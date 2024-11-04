"""Library for handling Journal Assistant storage."""

from pathlib import Path
import logging

from ical.calendar import Calendar

from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry

from .const import (
    DEFAULT_NOTE_NAME,
    CONF_NOTES,
    DOMAIN,
)
from .processing.journal import (
    journal_from_yaml,
    write_journal_page_yaml,
    indexable_notebooks_iterator,
)
from .processing.local_vectordb import LocalVectorDB
from .processing.model import JournalPage
from .vectordb import VectorDB
from .processing import vision_model


_LOGGER = logging.getLogger(__name__)

VECTOR_DB_STORAGE_PATH = f".storage/{DOMAIN}/{{config_entry_id}}/vectordb"
JOURNAL_STORAGE_PATH = f".storage/{DOMAIN}/{{config_entry_id}}/journal"
INDEX_BATCH_SIZE = 20
INDEX_PERSIST_SiZE = 100


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


async def create_vector_db(hass: HomeAssistant, entry: ConfigEntry) -> VectorDB:
    """Create a VectorDB instance."""
    entries = await load_journal_entries(hass, entry)

    vectordb = LocalVectorDB(
        query_fn=vision_model.embed_query_async,
        index_fn=vision_model.embed_document_async,
    )

    storage_path = vectordb_storage_path(hass, entry.entry_id)

    def _ensure_exsts(s) -> None:
        storage_path.parent.mkdir(parents=True, exist_ok=True)

    await hass.async_add_executor_job(_ensure_exsts)

    await vectordb.load_store(storage_path)

    _LOGGER.debug("Upserting document index")
    total = 0
    for document_batch in indexable_notebooks_iterator(
        entries, batch_size=INDEX_BATCH_SIZE
    ):
        await vectordb.upsert_index(document_batch)
        total += len(document_batch)
        if total % INDEX_PERSIST_SiZE == 0:
            _LOGGER.debug("Persisting index after %s documents", total)
            await vectordb.save_store(storage_path)
    await vectordb.save_store(storage_path)

    return vectordb
