"""Vector DB component for Home Assistant."""

from dataclasses import dataclass, field
from abc import ABC, abstractmethod
from typing import Any
import datetime

from mashumaro.mixins.json import DataClassJSONMixin
from mashumaro.config import BaseConfig


class VectorDBError(Exception):
    """Base class for VectorDB errors."""


@dataclass(kw_only=True)
class IndexableDocument:
    """An indexable document."""

    uid: str
    """Unique identifier for the document."""

    timestamp: datetime.datetime | None
    """Timestamp of the document used for date restricts."""

    metadata: dict[str, Any] = field(default_factory=dict)
    """Metadata fields the document that can be searched."""

    document: str
    """The document content that will be indexed."""


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


class VectorDB(ABC):
    """Journal Assistant vector search database."""

    @abstractmethod
    def upsert_index(self, documents: list[IndexableDocument]) -> None:
        """Add notebooks to the index."""

    @abstractmethod
    def count(self) -> int:
        """Return the number of documents in the collection."""

    @abstractmethod
    def query(self, params: QueryParams) -> list[dict[str, Any]]:
        """Search the VectorDB for relevant documents."""