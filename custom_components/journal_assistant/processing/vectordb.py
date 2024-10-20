"""Journal Assistant vector search database."""

import itertools
import logging
from typing import Any
from collections.abc import Generator
from pathlib import Path
import yaml
from dataclasses import dataclass
import datetime
from urllib.parse import urlparse

import chromadb
from chromadb.api.types import IncludeEnum
from chromadb.config import DEFAULT_TENANT, DEFAULT_DATABASE, Settings
from chromadb.utils.embedding_functions import google_embedding_function
from ical.calendar import Calendar
from ical.journal import Journal
from mashumaro.mixins.json import DataClassJSONMixin
from mashumaro.config import BaseConfig

from homeassistant.util import dt as dt_util


_LOGGER = logging.getLogger(__name__)

INDEX_BATCH_SIZE = 25
DEFAULT_MAX_RESULTS = 10
COLLECTION_NAME = "journal_assistant"
MODEL = "models/text-embedding-004"
EMPTY_QUERY = "task"  # Arbitrary query to use when no query is provided


@dataclass(kw_only=True)
class QueryParams(DataClassJSONMixin):
    """Query parameters for the VectorDB."""

    query: str | None = None
    date_range: tuple[datetime.date | None, datetime.date | None] | None = None
    category: str | None = None  # Notebook name in practice
    num_results: int | None = None

    def as_query_args(self) -> dict[str, Any]:
        """Return the query arguments for vectordb query."""
        args: dict[str, Any] = {}
        args["query_texts"] = [self.query if self.query else EMPTY_QUERY]
        filters: list[dict[str, Any]] = []
        if self.category is not None:
            filters.append({"category": self.category})
        if self.date_range is not None:
            start, end = self.date_range
            if start is not None:
                filters.append(
                    {"date": {"$gte": dt_util.start_of_local_day(start).timestamp()}}
                )
            if end is not None:
                filters.append(
                    {"date": {"$lte": dt_util.start_of_local_day(end).timestamp()}}
                )
        if len(filters) > 1:
            args["where"] = {"$and": filters}
        elif len(filters) == 1:
            args["where"] = filters[0]
        args["n_results"] = self.num_results or DEFAULT_MAX_RESULTS
        return args

    class Config(BaseConfig):
        omit_none = False
        code_generation_options = ["TO_DICT_ADD_OMIT_NONE_FLAG"]


@dataclass
class IndexableDocument:
    """An indexable document."""

    uid: str
    metadata: dict[str, Any]
    document: str


def _serialize_content(item: Journal) -> str:
    """Serialize a journal entry."""
    return yaml.dump(item.dict(exclude={"uid", "dtsamp"}, exclude_unset=True, exclude_none=True))  # type: ignore[no-any-return]


def create_indexable_document(journal_entry: Journal) -> IndexableDocument:
    """Create an indexable document from a journal entry."""
    return IndexableDocument(
        uid=journal_entry.uid or "",
        document=_serialize_content(journal_entry),
        metadata={
            "category": (next(iter(journal_entry.categories), "")),
            "date": dt_util.start_of_local_day(journal_entry.dtstart).timestamp(),
            "name": journal_entry.summary or "",
        },
    )


def indexable_notebooks_iterator(
    notebooks: dict[str, Calendar], batch_size: int | None = None
) -> Generator[list[IndexableDocument]]:
    """Iterate over notebooks in batches."""
    total = sum(len(calendar.journal) for calendar in notebooks.values())
    count = 0
    for calendar in notebooks.values():
        for found_journal_entries in itertools.batched(
            calendar.journal, batch_size or INDEX_BATCH_SIZE
        ):
            count += len(found_journal_entries)
            _LOGGER.debug("Processing batch %s of %s", count, total)
            yield [
                create_indexable_document(journal_entry)
                for journal_entry in found_journal_entries
            ]


def create_chromadb_client(chromadb_url: str, tenant: str) -> chromadb.api.ClientAPI:
    """Create a ChromaDB client."""
    _LOGGER.debug("Creating ChromaDB client for tenant: %s", tenant)
    url = urlparse(chromadb_url)
    port = 80
    if url.port:
        port = url.port
    elif url.scheme == "https":
        port = 443
    return chromadb.HttpClient(
        settings=Settings(
            anonymized_telemetry=False,
        ),
        host=url.hostname or "",
        port=port,
        ssl=(url.scheme == "https"),
        tenant=tenant,
        database=DEFAULT_DATABASE,
    )


def create_tenant(chromadb_url: str, tenant: str) -> None:
    """Get or create a tenant."""
    url = urlparse(chromadb_url)
    port = 80
    if url.port:
        port = url.port
    elif url.scheme == "https":
        port = 443
    settings = Settings(
        chroma_api_impl="chromadb.api.fastapi.FastAPI",
        chroma_server_host=url.hostname,
        chroma_server_http_port=port,
        chroma_server_ssl_enabled=(url.scheme == "https"),
        anonymized_telemetry=False,
    )
    _LOGGER.debug("Creating tenant: %s", tenant)
    admin_client = chromadb.AdminClient(settings=settings)
    admin_client.create_tenant(tenant)
    admin_client.create_database(DEFAULT_DATABASE, tenant)
    _LOGGER.debug("Tenant created: %s", tenant)


def create_local_chroma_client(storage_path: Path) -> chromadb.api.ClientAPI:
    """Create a ChromaDB client."""
    return chromadb.PersistentClient(
        path=str(storage_path),
        settings=Settings(
            anonymized_telemetry=False,
        ),
        tenant=DEFAULT_TENANT,
        database=DEFAULT_DATABASE,
    )


class VectorDB:
    """Journal Assistant vector search database."""

    def __init__(self, client: chromadb.api.ClientAPI, google_api_key: str) -> None:
        """Initialize the vector database."""
        _LOGGER.debug("Creating ChromaDB System")
        self.client = client
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
        _LOGGER.debug("Creating collection: %s", COLLECTION_NAME)

    def _query_collection(self) -> chromadb.Collection:
        """Get the collection for the VectorDB."""
        return self.client.get_or_create_collection(
            name=COLLECTION_NAME, embedding_function=self.query_embedding_function  # type: ignore[arg-type]
        )

    def _index_collection(self) -> chromadb.Collection:
        """Get the collection for the VectorDB."""
        return self.client.get_or_create_collection(
            name=COLLECTION_NAME, embedding_function=self.index_embedding_function  # type: ignore[arg-type]
        )

    def upsert_index(self, documents: list[IndexableDocument]) -> None:
        """Add notebooks to the index."""
        _LOGGER.debug("Upserting %d documents in the index", len(documents))

        collection = self._index_collection()
        ids = [document.uid for document in documents]

        results = collection.get(ids=ids, include=[IncludeEnum.documents])
        existing_ids = {
            uid: documents
            for uid, documents in zip(results["ids"], results.get("documents") or [])
        }
        if existing_ids:
            _LOGGER.debug("Found %s existing documents", len(existing_ids))
        # Determine which documents entries are entirely new or have updated content
        upsert_documents = []
        for document in documents:
            if (
                existing_content := existing_ids.get(document.uid)
            ) is None or document.document != existing_content:
                upsert_documents.append(document)
        if not upsert_documents:
            _LOGGER.debug("Skipping batch of unchanged documents")
            return
        _LOGGER.debug("Upserting batch of %s to index", len(upsert_documents))
        collection.upsert(
            documents=[document.document for document in upsert_documents],
            metadatas=[document.metadata for document in upsert_documents],
            ids=[document.uid for document in upsert_documents],
        )

    def count(self) -> int:
        """Return the number of documents in the collection."""
        collection = self._query_collection()
        return collection.count()

    def query(self, params: QueryParams) -> list[dict[str, Any]]:
        """Search the VectorDB for relevant documents."""
        collection = self._query_collection()
        query_args = params.as_query_args()
        _LOGGER.debug("Querying collection %s with args %s", collection, query_args)
        results: chromadb.QueryResult = collection.query(**query_args)
        if (
            (id_list := results.get("ids")) is None
            or (metadata_list := results.get("metadatas")) is None
            or (document_list := results.get("documents")) is None
            or (distance_list := results.get("distances")) is None
        ):
            raise ValueError(f"Invalid query results: {results}")
        # Get the results for the first (and only) query
        ids = id_list[0]
        metadatas = metadata_list[0]
        documents = document_list[0]
        distances = distance_list[0]
        return [
            {
                "id": ids[index],
                "content": documents[index],
                "score": distances[index],
                **metadatas[index],
            }
            for index in range(len(ids))
        ]
