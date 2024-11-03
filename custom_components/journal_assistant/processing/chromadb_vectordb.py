"""Journal Assistant vector search database."""

import logging
from typing import Any
from pathlib import Path
from urllib.parse import urlparse
import datetime

import chromadb
from chromadb.errors import ChromaError
from chromadb.api.types import IncludeEnum
from chromadb.config import DEFAULT_TENANT, DEFAULT_DATABASE, Settings
from chromadb.utils.embedding_functions import google_embedding_function

from homeassistant.core import HomeAssistant

from custom_components.journal_assistant.vectordb import (
    VectorDB,
    IndexableDocument,
    QueryParams,
    VectorDBError,
    QueryResult,
)

_LOGGER = logging.getLogger(__name__)


DEFAULT_MAX_RESULTS = 10
COLLECTION_NAME = "journal_assistant"
MODEL = "models/text-embedding-004"
EMPTY_QUERY = "task"  # Arbitrary query to use when no query is provided


def _as_query_args(params: QueryParams) -> dict[str, Any]:
    """Return the query arguments for vectordb query."""
    args: dict[str, Any] = {}
    args["query_texts"] = [params.query if params.query else EMPTY_QUERY]
    filters: list[dict[str, Any]] = []
    if params.metadata is not None:
        filters.append(params.metadata)
    if params.start_date is not None:
        filters.append({"date": {"$gte": params.start_date.timestamp()}})
    if params.end_date is not None:
        filters.append({"date": {"$lte": params.end_date.timestamp()}})
    if len(filters) > 1:
        args["where"] = {"$and": filters}
    elif len(filters) == 1:
        args["where"] = filters[0]
    args["n_results"] = params.num_results or DEFAULT_MAX_RESULTS
    return args


def _create_chromadb_client(chromadb_url: str, tenant: str) -> chromadb.api.ClientAPI:
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


class ChromaVectorDB:
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
        metadatas: list[dict[str, str]] = []
        for document in upsert_documents:
            metadata = {
                **document.metadata,
            }
            if document.timestamp:
                metadata["date"] = document.timestamp.timestamp()
            metadatas.append(metadata)
        collection.upsert(
            documents=[document.document for document in upsert_documents],
            metadatas=metadatas,  # type: ignore[arg-type]
            ids=[document.uid for document in upsert_documents],
        )

    def count(self) -> int:
        """Return the number of documents in the collection."""
        collection = self._query_collection()
        return collection.count()

    def query(self, params: QueryParams) -> list[QueryResult]:
        """Search the VectorDB for relevant documents."""
        collection = self._query_collection()
        query_args = _as_query_args(params)
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
            QueryResult(
                document=IndexableDocument(
                    uid=ids[index],
                    document=documents[index],
                    timestamp=datetime.datetime.fromtimestamp(
                        float(metadatas[index].get("date"))  # type: ignore[arg-type]
                    ),
                    metadata={**metadatas[index]},
                ),
                score=distances[index],
            )
            for index in range(len(ids))
        ]


class AsyncChromaVectorDB(VectorDB):
    """Journal Assistant vector search database."""

    def __init__(self, hass: HomeAssistant, chroma_vectordb: ChromaVectorDB) -> None:
        """Initialize the vector database."""
        self._hass = hass
        self._chroma_vectordb = chroma_vectordb

    async def upsert_index(self, documents: list[IndexableDocument]) -> None:
        """Add notebooks to the index."""
        await self._hass.async_add_executor_job(
            self._chroma_vectordb.upsert_index, documents
        )

    async def count(self) -> int:
        """Return the number of documents in the collection."""
        return self._chroma_vectordb.count()

    async def query(self, params: QueryParams) -> list[QueryResult]:
        """Search the VectorDB for relevant documents."""
        return await self._hass.async_add_executor_job(
            self._chroma_vectordb.query, params
        )


def create_chroma_db(
    hass: HomeAssistant,
    chromadb_url: str,
    tenant: str,
    api_key: str,
) -> VectorDB:
    _LOGGER.debug("Creating VectorDB")
    try:
        client = _create_chromadb_client(chromadb_url, tenant)
    except ChromaError as err:
        _LOGGER.error("Error creating ChromaDB client: %s", err)
        raise VectorDBError(f"Error creating ChromaDB client: {err}") from err
    db = ChromaVectorDB(client, api_key)
    return AsyncChromaVectorDB(hass, db)
