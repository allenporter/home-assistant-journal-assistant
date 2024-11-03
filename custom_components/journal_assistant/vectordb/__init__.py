"""Vector DB component for Home Assistant."""

from dataclasses import dataclass
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
    metadata: dict[str, Any]
    document: str


@dataclass(kw_only=True)
class QueryParams(DataClassJSONMixin):
    """Query parameters for the VectorDB."""

    query: str | None = None
    start_date: datetime.date | None = None
    end_date: datetime.date | None = None
    category: str | None = None  # Notebook name in practice
    num_results: int | None = None

    class Config(BaseConfig):
        omit_none = False
        code_generation_options = ["TO_DICT_ADD_OMIT_NONE_FLAG"]


# class Embedding(ABC):
#     """Embedding for VectorDB."""

#     value: np.ndarray
#     """The embedding value."""


# class EmbeddingFunction(ABC):
#     """Embedding function for VectorDB."""

#     @abstractmethod
#     def __call__(self, document: str) -> Embedding:
#         """Return the embedding of the document."""


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
