"""Vector DB component for Home Assistant."""

from dataclasses import dataclass, field
from abc import ABC, abstractmethod
from typing import Any
import datetime
from collections.abc import Callable, Awaitable

from mashumaro.mixins.json import DataClassJSONMixin
from mashumaro.config import BaseConfig
import numpy as np


class VectorDBError(Exception):
    """Base class for VectorDB errors."""


@dataclass(kw_only=True)
class Embedding:
    """An embedding."""

    embedding: np.ndarray
    """The embedding."""


EmbeddingFunction = Callable[[list[str]], Awaitable[list[Embedding]]]
"""A function that takes a string and returns an embedding."""


@dataclass(kw_only=True)
class IndexableDocument(DataClassJSONMixin):
    """An indexable document."""

    uid: str
    """Unique identifier for the document."""

    timestamp: datetime.datetime | None
    """Timestamp of the document used for date restricts."""

    metadata: dict[str, Any] = field(default_factory=dict)
    """Metadata fields the document that can be searched."""

    document: str
    """The document content that will be indexed."""

    class Config(BaseConfig):
        omit_none = False
        code_generation_options = ["TO_DICT_ADD_OMIT_NONE_FLAG"]


@dataclass(kw_only=True)
class QueryParams(DataClassJSONMixin):
    """Query parameters for the VectorDB."""

    query: str | None = None
    """The query string."""

    start_date: datetime.datetime | None = None
    """Only include document chunks on or after this date."""

    end_date: datetime.datetime | None = None
    """Only include document chunks on or before this date."""

    metadata: dict[str, Any] | None = None

    num_results: int | None = None
    """Maximum number of results to return."""

    class Config(BaseConfig):
        omit_none = False
        code_generation_options = ["TO_DICT_ADD_OMIT_NONE_FLAG"]


@dataclass(kw_only=True)
class QueryResult(DataClassJSONMixin):
    """Query result from the VectorDB."""

    document: IndexableDocument
    """The document that was found."""

    score: float
    """The similarity score of the document."""


class VectorDB(ABC):
    """Journal Assistant vector search database."""

    @abstractmethod
    async def upsert_index(self, documents: list[IndexableDocument]) -> None:
        """Add notebooks to the index."""

    @abstractmethod
    async def count(self) -> int:
        """Return the number of documents in the collection."""

    @abstractmethod
    async def query(self, params: QueryParams) -> list[QueryResult]:
        """Search the VectorDB for relevant documents."""
