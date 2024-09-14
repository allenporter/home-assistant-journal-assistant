"""Journal Assistant vector search database."""

import itertools
import logging
from typing import Any

import chromadb
from ical.calendar import Calendar


_LOGGER = logging.getLogger(__name__)

BATCH_SIZE = 5


def create_index(notebooks: dict[str, Calendar]) -> chromadb.ClientAPI:
    """Create a search index for the journal."""
    client = chromadb.Client()
    for note_name, calendar in notebooks.items():
        collection = client.create_collection(name="note_name")
        for journal_entries in itertools.batched(calendar.journal, BATCH_SIZE):
            collection.add(
                documents=[
                    journal_entry.description or "" for journal_entry in journal_entries
                ],
                metadatas=[
                    {
                        "date": journal_entry.dtstart.isoformat(),
                        "name": journal_entry.summary or "",
                    }
                    for journal_entry in journal_entries
                ],
                ids=[journal_entry.uid or "" for journal_entry in journal_entries],
            )
    return client


def query_collection(
    client: chromadb.ClientAPI, entity_id: str, query: str, num_results: int
) -> list[dict[str, Any]]:
    """Query the search index for the journal."""
    collection = client.get_collection(entity_id)
    results = collection.query(
        query_texts=query,
        n_results=num_results,
    )
    return [
        {
            "id": results["ids"][index] if results["ids"] else "",
            "metadata": results["metadatas"][index] if results["metadatas"] else [],
            "document": results["documents"][index] if results["documents"] else "",
        }
        for index in range(len(results["ids"]))
    ]
