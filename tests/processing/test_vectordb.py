"""Test loading the vector DB."""

from pathlib import Path
from collections.abc import Generator
from typing import Any
from unittest.mock import patch
import hashlib
import tempfile
import datetime

import chromadb
import numpy as np

import pytest

from custom_components.journal_assistant.const import DOMAIN
from custom_components.journal_assistant.processing import vectordb
from custom_components.journal_assistant.processing.journal import journal_from_yaml


@pytest.fixture(autouse=True)
def mock_disable_posthog() -> Generator[None, None, None]:
    """Disable chromadb posthog since it starts daemon threads during tests."""
    with patch(
        "chromadb.telemetry.product.posthog.Posthog",
        autospec=True,
    ):
        yield


@pytest.fixture(name="storage_path")
def mock_vectordb_storage_path() -> Generator[Path, None, None]:
    """Fake out the storage path to load from the fixtures directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


class FakeEmbeddingFunction(chromadb.EmbeddingFunction):
    """Fake embedding function for testing."""

    embeds: int = 0

    def __call__(self, input: Any) -> chromadb.Embeddings:
        result: chromadb.Embeddings = []
        for item in input:
            self.embeds += 1
            result.append(
                np.array(
                    [ord(c) for c in hashlib.sha256(item.encode()).hexdigest()][0:3]
                )
            )
        return result


@pytest.fixture(name="embedding_function")
def mock_embedding_function() -> Generator[FakeEmbeddingFunction, None, None]:
    """Fixture to mock the embedding function."""
    fake_embedding = FakeEmbeddingFunction()
    with patch(
        f"custom_components.{DOMAIN}.processing.vectordb.google_embedding_function.GoogleGenerativeAiEmbeddingFunction",
        return_value=fake_embedding,
    ):
        yield fake_embedding


def test_vectordb_loading(
    storage_path: Path, embedding_function: FakeEmbeddingFunction
) -> None:
    """Test parsing a journal page."""

    entries = journal_from_yaml(Path("tests/fixtures"), {"Daily", "Monthly"}, "Journal")
    assert len(entries) == 3
    assert entries.keys() == {"Daily", "Journal", "Monthly"}

    # Add the first entry to the index
    k_v = next(iter(entries.items()))
    first_entry = {k_v[0]: k_v[1]}

    db = vectordb.VectorDB(storage_path, "12345")
    db.upsert_index(first_entry)
    assert embedding_function.embeds == 4

    # Add the rest, which skips the duplicate
    db.upsert_index(entries)
    assert embedding_function.embeds == 6

    assert db.count() == 6

    results = db.query(vectordb.QueryParams(query="example", num_results=5))
    assert len(results) == 5
    assert results[0].keys() == {"id", "content", "date", "name", "category", "score"}
    assert results[0]["category"] in ("Daily", "Journal", "Monthly")
    assert (
        results[0]["content"]
        == """categories:
- Daily
description: '- migrate Dec to supernote

  - set Plans w/ mom

  - call Dad re xmas plan

  - gifts info to mom & Sam

  - prod readiness pass

  - xmas tree

  - Dot template: darker 5mm'
dtstart: 2023-12-19
summary: Daily 2023-12-19
"""
    )

    results = db.query(
        vectordb.QueryParams(
            query="note",
            category="Daily",
            date_range=(datetime.date(2023, 12, 21), datetime.date(2023, 12, 21)),
            num_results=5,
        )
    )
    assert len(results) == 1
    assert results[0].keys() == {"id", "content", "date", "name", "category", "score"}
    assert results[0]["category"] == "Daily"
    assert (
        results[0]["content"]
        == """categories:
- Daily
description: '- cardboard breakdown

  - Bowling w/ Q

  - flux-local helm

  - todo urls?

  - gifts plan

  - windows xmas lights

  - fitbit python'
dtstart: 2023-12-21
summary: Daily 2023-12-21
"""
    )
