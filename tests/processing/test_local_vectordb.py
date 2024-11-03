"""Test loading the vector DB."""

from pathlib import Path
from collections.abc import Generator
from typing import Any
from unittest.mock import patch
import hashlib
import tempfile
import datetime

import numpy as np
from syrupy import SnapshotAssertion
import pytest

from custom_components.journal_assistant.const import DOMAIN
from custom_components.journal_assistant.processing.local_vectordb import Embedding, EmbeddingFunction, LocalVectorDB
from custom_components.journal_assistant.processing.journal import journal_from_yaml, create_indexable_document
from custom_components.journal_assistant.vectordb import (
    QueryParams,
)


class FakeEmbeddingFunction(EmbeddingFunction):
    """Fake embedding function for testing."""

    embeds: int = 0

    def __call__(self, item: str) -> Embedding:
        result = [ord(c) for c in hashlib.sha256(item.encode()).hexdigest()][0:3]
        self.embeds += 1
        return Embedding(
            embedding=np.array(result),
        )


def test_vectordb_loading(
    snapshot: SnapshotAssertion,
) -> None:
    """Test parsing a journal page."""

    entries = journal_from_yaml(Path("tests/fixtures"), {"Daily", "Monthly"}, "Journal")
    assert len(entries) == 3
    assert entries.keys() == {"Daily", "Journal", "Monthly"}

    embedding_function = FakeEmbeddingFunction()

    # Add the first entry to the index
    first_calendar = next(iter(entries.values()))
    db = LocalVectorDB(embedding_function, embedding_function)
    db.upsert_index(
        [
            create_indexable_document(entry)
            for entry in first_calendar.journal
        ]
    )
    assert embedding_function.embeds == 4

    # Add the rest, which skips the duplicate
    db.upsert_index(
        [
            create_indexable_document(entry)
            for calendar in entries.values()
            for entry in calendar.journal
        ]
    )
    assert embedding_function.embeds == 7

    assert db.count() == 7

    results = db.query(QueryParams(query="tree", num_results=5))
    assert len(results) == 5
    assert results[0] == snapshot

    # Limit results to a single date
    results = db.query(
        QueryParams(
            query="gifts",
            metadata={"category": "Daily"},
            start_date=datetime.datetime(2023, 12, 21, 0, 0, 0, tzinfo=datetime.timezone.utc),
            end_date=datetime.datetime(2023, 12, 21, 23, 59, 59, tzinfo=datetime.timezone.utc),
            num_results=5,
        )
    )
    assert len(results) == 1
    assert results[0] == snapshot
