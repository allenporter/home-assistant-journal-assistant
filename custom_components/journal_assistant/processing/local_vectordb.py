"""Journal Assistant vector search database."""

import itertools
import logging
from dataclasses import dataclass
from collections.abc import Callable, Awaitable

import numpy as np


from custom_components.journal_assistant.vectordb import (
    VectorDB,
    IndexableDocument,
    QueryParams,
    QueryResult,
)

_LOGGER = logging.getLogger(__name__)


DEFAULT_MAX_RESULTS = 10
COLLECTION_NAME = "journal_assistant"
MODEL = "models/text-embedding-004"
EMPTY_QUERY = "task"  # Arbitrary query to use when no query is provided


@dataclass(kw_only=True)
class Embedding:
    """An embedding."""

    embedding: np.ndarray
    """The embedding."""


EmbeddingFunction = Callable[[str], Awaitable[Embedding]]


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

    async def upsert_index(self, documents: list[IndexableDocument]) -> None:
        """Add notebooks to the index."""
        _LOGGER.debug("Upserting %d documents in the index", len(documents))

        for document in documents:
            if existing_document := self._documents.get(document.uid):
                if existing_document.timestamp == document.timestamp:
                    # Skip if the document is already in the index
                    continue
            self._documents[document.uid] = document
            self._embeddings[document.uid] = await self._index_fn(document.document)

    async def count(self) -> int:
        """Return the number of documents in the collection."""
        return len(self._documents)

    async def query(self, params: QueryParams) -> list[QueryResult]:
        """Search the VectorDB for relevant documents."""

        # The results will be sorted by the query embedding
        query_embedding: Embedding | None = None
        if params.query:
            query_embedding = await self._query_fn(params.query)

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
            return np.linalg.norm(  # type: ignore[return-value]
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
