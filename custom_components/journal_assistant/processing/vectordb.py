"""Journal Assistant vector search database."""

import itertools
import logging
from typing import Any
from pathlib import Path

import chromadb
from chromadb.config import DEFAULT_TENANT, DEFAULT_DATABASE, Settings
import chromadb.utils.embedding_functions as embedding_functions

from ical.calendar import Calendar


_LOGGER = logging.getLogger(__name__)

BATCH_SIZE = 5
COLLECTION_NAME = "journal_assistant"


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
        self.embedding_function = (
            embedding_functions.GoogleGenerativeAiEmbeddingFunction(
                api_key=google_api_key
            )
        )
        self.client = chromadb.PersistentClient(
            path=str(storage_path),
            settings=settings,
            tenant=DEFAULT_TENANT,
            database=DEFAULT_DATABASE,
        )
        _LOGGER.debug("Creating collection: %s", COLLECTION_NAME)
        self.collection = self.client.get_or_create_collection(
            name=COLLECTION_NAME, embedding_function=self.embedding_function  # type: ignore[arg-type]
        )

    def add_to_index(self, notebooks: dict[str, Calendar]) -> None:
        """Add notebooks to the index."""
        _LOGGER.debug("Adding notebooks to index")
        for note_name, calendar in notebooks.items():
            for journal_entries in itertools.batched(calendar.journal, BATCH_SIZE):
                _LOGGER.debug("Adding batch of {len(journal_entries)} to index")
                self.collection.add(
                    documents=[
                        journal_entry.description or ""
                        for journal_entry in journal_entries
                    ],
                    metadatas=[
                        {
                            "notebook": note_name,
                            "date": journal_entry.dtstart.isoformat(),
                            "name": journal_entry.summary or "",
                        }
                        for journal_entry in journal_entries
                    ],
                    ids=[journal_entry.uid or "" for journal_entry in journal_entries],
                )

    def query(self, query: str, num_results: int) -> list[dict[str, Any]]:
        """Search the VectorDB for relevant documents."""
        results: chromadb.QueryResult = self.collection.query(
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
