"""Journal Assistant vector search database."""

import itertools
import logging
from typing import Any
from pathlib import Path
import yaml


import chromadb
from chromadb.api.types import IncludeEnum
from chromadb.config import DEFAULT_TENANT, DEFAULT_DATABASE, Settings
from chromadb.utils.embedding_functions import google_embedding_function

from ical.calendar import Calendar
from ical.journal import Journal


_LOGGER = logging.getLogger(__name__)

BATCH_SIZE = 10
COLLECTION_NAME = "journal_assistant"
MODEL = "models/text-embedding-004"


def serialize_content(item: Journal) -> str:
    """Serialize a journal entry."""
    return yaml.dump(item.dict(exclude={"uid", "dtsamp"}, exclude_unset=True, exclude_none=True))  # type: ignore[no-any-return]


class VectorDB:
    """Journal Assistant vector search database."""

    def __init__(self, storage_path: Path, google_api_key: str) -> None:
        """Initialize the vector database."""
        _LOGGER.debug("Creating ChromaDB System")
        settings = Settings(
            anonymized_telemetry=False,
        )
        self.system = chromadb.config.System(settings)
        _LOGGER.debug("Creating Google embedding function")
        # Separate embedding functions are used for idnexing vs querying
        self.index_embedding_function = (
            google_embedding_function.GoogleGenerativeAiEmbeddingFunction(
                api_key=google_api_key, model_name=MODEL, task_type="RETRIEVAL_DOCUMENT"
            )
        )
        self.query_embedding_function = (
            google_embedding_function.GoogleGenerativeAiEmbeddingFunction(
                api_key=google_api_key, model_name=MODEL, task_type="RETRIEVAL_QUERY"
            )
        )
        self.client = chromadb.PersistentClient(
            path=str(storage_path),
            settings=settings,
            tenant=DEFAULT_TENANT,
            database=DEFAULT_DATABASE,
        )
        _LOGGER.debug("Creating collection: %s", COLLECTION_NAME)

    def upsert_index(self, notebooks: dict[str, Calendar]) -> None:
        """Add notebooks to the index."""
        _LOGGER.debug("Adding notebooks to index")

        collection = self.client.get_or_create_collection(
            name=COLLECTION_NAME, embedding_function=self.index_embedding_function  # type: ignore[arg-type]
        )

        for note_name, calendar in notebooks.items():
            _LOGGER.debug(
                "Indexing %s with %s entries", note_name, len(calendar.journal)
            )
            for found_journal_entries in itertools.batched(
                calendar.journal, BATCH_SIZE
            ):
                _LOGGER.debug(
                    "Examining batch of %s to index", len(found_journal_entries)
                )
                ids = [
                    journal_entry.uid or "" for journal_entry in found_journal_entries
                ]
                results = collection.get(ids=ids, include=[IncludeEnum.documents])
                _LOGGER.debug("Results: %s", results)
                existing_ids = {
                    uid: documents
                    for uid, documents in zip(
                        results["ids"], results.get("documents") or []
                    )
                }
                if existing_ids:
                    _LOGGER.debug("Found %s existing documents", len(existing_ids))
                # Determine which journal entries are entirely new or have
                # updated descriptions
                journal_entries = []
                documents = []
                metadatas = []
                for journal_entry in found_journal_entries:
                    existing_content = existing_ids.get(journal_entry.uid)
                    entry_content = serialize_content(journal_entry)
                    if existing_content is None or entry_content != existing_content:
                        journal_entries.append(journal_entry)
                        documents.append(entry_content)
                        metadatas.append(
                            {
                                "category": (
                                    journal_entry.categories[0]
                                    if journal_entry.categories
                                    else ""
                                ),
                                "date": journal_entry.dtstart.isoformat(),
                                "name": journal_entry.summary or "",
                            }
                        )
                ids = [journal_entry.uid or "" for journal_entry in journal_entries]
                if not ids:
                    _LOGGER.debug("Skipping batch of unchanged documents")
                    continue
                _LOGGER.debug("Upserting batch of %s to index", len(journal_entries))
                collection.upsert(
                    documents=documents,
                    metadatas=metadatas,  # type: ignore[arg-type]
                    ids=ids,
                )

    def count(self) -> int:
        """Return the number of documents in the collection."""
        collection = self.client.get_collection(
            name=COLLECTION_NAME, embedding_function=self.query_embedding_function  # type: ignore[arg-type]
        )
        return collection.count()

    def query(self, query: str, num_results: int) -> list[dict[str, Any]]:
        """Search the VectorDB for relevant documents."""
        collection = self.client.get_collection(
            name=COLLECTION_NAME, embedding_function=self.query_embedding_function  # type: ignore[arg-type]
        )

        results: chromadb.QueryResult = collection.query(
            query_texts=query,
            n_results=num_results,
        )
        if (
            (id_list := results.get("ids")) is None
            or (metadata_list := results.get("metadatas")) is None
            or (document_list := results.get("documents")) is None
        ):
            raise ValueError(f"Invalid query results: {results}")
        # Get the results for the first (and only) query
        ids = id_list[0]
        metadatas = metadata_list[0]
        documents = document_list[0]
        return [
            {
                "id": ids[index],
                "content": documents[index],
                **metadatas[index],
            }
            for index in range(len(ids))
        ]
