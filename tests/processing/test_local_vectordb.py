"""Test loading the vector DB."""

from pathlib import Path
import hashlib
import datetime
import tempfile
import pathlib
import json

import pytest
import numpy as np
from syrupy import SnapshotAssertion

from custom_components.journal_assistant.processing.local_vectordb import (
    LocalVectorDB,
)
from custom_components.journal_assistant.processing.journal import (
    journal_from_yaml,
    create_indexable_document,
)
from custom_components.journal_assistant.vectordb import (
    QueryParams,
    IndexableDocument,
    Embedding,
    QueryResult,
)


class FakeEmbeddingFunction:
    """Fake embedding function for testing."""

    embeds: int = 0

    async def __call__(self, items: list[str]) -> list[Embedding]:
        results = []
        for item in items:
            emb = [ord(c) for c in hashlib.sha256(item.encode()).hexdigest()][0:3]
            self.embeds += 1
            results.append(Embedding(embedding=np.array(emb)))
        return results


@pytest.fixture
def embedding_function() -> FakeEmbeddingFunction:
    """Return a fake embedding function."""
    return FakeEmbeddingFunction()


@pytest.fixture
def db(embedding_function: FakeEmbeddingFunction) -> LocalVectorDB:
    """Return a vector DB for testing."""
    return LocalVectorDB(embedding_function, embedding_function)


async def test_vectordb_loading(
    snapshot: SnapshotAssertion,
    embedding_function: FakeEmbeddingFunction,
    db: LocalVectorDB,
) -> None:
    """Test parsing a journal page."""

    entries = journal_from_yaml(Path("tests/fixtures"), {"Daily", "Monthly"}, "Journal")
    assert len(entries) == 3
    assert entries.keys() == {"Daily", "Journal", "Monthly"}

    # Add the first entry to the index
    first_calendar = next(iter(entries.values()))
    await db.upsert_index(
        [create_indexable_document(entry) for entry in first_calendar.journal]
    )
    assert embedding_function.embeds == 4

    # Add the rest, which skips the duplicate
    await db.upsert_index(
        [
            create_indexable_document(entry)
            for calendar in entries.values()
            for entry in calendar.journal
        ]
    )
    assert embedding_function.embeds == 7

    assert await db.count() == 7

    results = await db.query(QueryParams(query="tree", num_results=5))
    assert len(results) == 5
    assert results[0] == snapshot

    # Limit results to a single date
    results = await db.query(
        QueryParams(
            query="gifts",
            metadata={"category": "Daily"},
            start_date=datetime.datetime(
                2023, 12, 21, 0, 0, 0, tzinfo=datetime.timezone.utc
            ),
            end_date=datetime.datetime(
                2023, 12, 21, 23, 59, 59, tzinfo=datetime.timezone.utc
            ),
            num_results=5,
        )
    )
    assert len(results) == 1
    assert results[0] == snapshot


async def test_save_store(
    snapshot: SnapshotAssertion,
    embedding_function: FakeEmbeddingFunction,
    db: LocalVectorDB,
) -> None:
    """Test writing the db store to a file."""

    await db.upsert_index(
        [
            IndexableDocument(
                uid="uid-1",
                document="document-1",
                timestamp=datetime.datetime(
                    2023, 12, 21, 0, 0, 0, tzinfo=datetime.timezone.utc
                ),
                metadata={"category": "Daily", "name": "Journal 1"},
            )
        ]
    )

    filename = pathlib.Path(tempfile.mktemp())
    await db.save_store(filename)

    with filename.open("r") as tf:
        assert json.loads(tf.read()) == {
            "documents": {
                "uid-1": {
                    "uid": "uid-1",
                    "document": "document-1",
                    "timestamp": "2023-12-21T00:00:00+00:00",
                    "metadata": {"category": "Daily", "name": "Journal 1"},
                }
            },
            "embeddings": {"uid-1": [48, 100, 56]},
        }


async def test_load_store(
    snapshot: SnapshotAssertion,
    embedding_function: FakeEmbeddingFunction,
    db: LocalVectorDB,
) -> None:
    """Test writing the db store to a file."""

    filename = pathlib.Path(tempfile.mktemp())

    with filename.open("w") as tf:
        tf.write(
            json.dumps(
                {
                    "documents": {
                        "uid-1": {
                            "uid": "uid-1",
                            "document": "document-1",
                            "timestamp": "2023-12-21T00:00:00+00:00",
                            "metadata": {"category": "Daily", "name": "Journal 1"},
                        }
                    },
                    "embeddings": {"uid-1": [48, 100, 56]},
                }
            )
        )

    await db.load_store(filename)
    assert await db.count() == 1
    assert await db.query(QueryParams(query="document-1", num_results=5)) == [
        QueryResult(
            document=IndexableDocument(
                uid="uid-1",
                document="document-1",
                timestamp=datetime.datetime(
                    2023, 12, 21, 0, 0, 0, tzinfo=datetime.timezone.utc
                ),
                metadata={"category": "Daily", "name": "Journal 1"},
            ),
            score=0.0,
        )
    ]
