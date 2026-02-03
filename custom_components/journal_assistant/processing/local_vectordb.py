"""Journal Assistant vector search database."""

import itertools
import logging
import asyncio
import json
from typing import Any
import pathlib

import numpy as np

from custom_components.journal_assistant.vectordb import (
    VectorDB,
    IndexableDocument,
    QueryParams,
    QueryResult,
    Embedding,
    EmbeddingFunction,
)

_LOGGER = logging.getLogger(__name__)


DEFAULT_MAX_RESULTS = 10
COLLECTION_NAME = "journal_assistant"
MODEL = "models/text-embedding-004"
EMPTY_QUERY = "task"  # Arbitrary query to use when no query is provided


class LocalVectorDB(VectorDB):
    """Local vector search database."""

    def __init__(
        self, index_fn: EmbeddingFunction, query_fn: EmbeddingFunction
    ) -> None:
        """Initialize the vector database."""
        self._index_fn = index_fn
        self._query_fn = query_fn
        self._documents: dict[str, IndexableDocument] = {}
        self._embeddings: dict[str, Embedding] = {}

    async def load_store(self, path: pathlib.Path) -> None:
        """Load the store contents from disk."""
        _LOGGER.debug("Loading store from %s", path)

        def _load_store() -> dict[str, Any] | None:
            """Load the store contents from disk."""
            _LOGGER.debug("Loading store from %s", path)
            if path.exists():
                with path.open("r") as file:
                    data = json.load(file)
                    if isinstance(data, dict):
                        return data
            return None

        loop = asyncio.get_event_loop()
        data = await loop.run_in_executor(None, _load_store)
        if data is None:
            return
        self._documents = {
            uid: IndexableDocument.from_dict(document)
            for uid, document in data["documents"].items()
        }
        self._embeddings = {
            uid: Embedding(embedding=np.array(embedding))
            for uid, embedding in data["embeddings"].items()
        }

    async def save_store(self, path: pathlib.Path) -> None:
        """Save the store contents to disk."""
        _LOGGER.debug("Saving store to %s (%d documents)", path, len(self._documents))

        def _save_store(data: dict[str, Any]) -> None:
            """Save the store contents to disk."""
            _LOGGER.debug("Saving store to %s", path)
            with path.open("w") as file:
                json.dump(data, file)

        data = {
            "documents": {
                uid: document.to_dict(omit_none=True)
                for uid, document in self._documents.items()
            },
            "embeddings": {
                uid: embedding.embedding.tolist()
                for uid, embedding in self._embeddings.items()
            },
        }
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, _save_store, data)

    async def upsert_index(self, documents: list[IndexableDocument]) -> None:
        """Add notebooks to the index."""
        _LOGGER.debug("Upserting %d documents in the index", len(documents))

        embed_docs: list[IndexableDocument] = []
        for document in documents:
            if existing_document := self._documents.get(document.uid):
                if existing_document.timestamp == document.timestamp:
                    # Skip if the document is already in the index
                    continue
            embed_docs.append(document)

        embeddings = await self._index_fn([doc.document for doc in embed_docs])
        for document, embedding in zip(embed_docs, embeddings):
            self._documents[document.uid] = document
            self._embeddings[document.uid] = embedding

    async def count(self) -> int:
        """Return the number of documents in the collection."""
        return len(self._documents)

    async def query(self, params: QueryParams) -> list[QueryResult]:
        """Search the VectorDB for relevant documents."""

        # The results will be sorted by the query embedding
        query_embedding: Embedding | None = None
        if params.query:
            query_embedding = (await self._query_fn([params.query]))[0]

        def document_filter(document: IndexableDocument) -> bool:
            if params.start_date is not None and (
                document.timestamp is None or document.timestamp < params.start_date
            ):
                return False
            if params.end_date is not None and (
                document.timestamp is None or document.timestamp > params.end_date
            ):
                return False
            if params.metadata is not None:
                for key, value in params.metadata.items():
                    if document.metadata.get(key) != value:
                        return False
            return True

        def compute_distance(document: IndexableDocument) -> float:
            if query_embedding is None:
                return 0.0
            return np.linalg.norm(
                query_embedding.embedding - self._embeddings[document.uid].embedding
            )

        distances = sorted(
            (
                QueryResult(
                    score=compute_distance(document),
                    document=document,
                )
                for document in self._documents.values()
                if document_filter(document)
            ),
            key=lambda result: result.score,
        )
        return list(
            itertools.islice(distances, params.num_results or DEFAULT_MAX_RESULTS)
        )
