"""Test loading the vector DB."""

from pathlib import Path
from collections.abc import Generator
from typing import Any
from unittest.mock import patch
import hashlib
import tempfile

import chromadb

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
            result.append([ord(c) for c in hashlib.sha256(item.encode()).hexdigest()][0:3])
        return result


@pytest.fixture(name="embedding_function")
def mock_embedding_function() -> Generator[FakeEmbeddingFunction, None, None]:
    """Fixture to mock the embedding function."""
    fake_embedding = FakeEmbeddingFunction()
    with patch(
        f"custom_components.{DOMAIN}.processing.vectordb.embedding_functions.GoogleGenerativeAiEmbeddingFunction",
        return_value=fake_embedding,
    ):
        yield fake_embedding


def test_vectordb_loading(storage_path: Path, embedding_function: FakeEmbeddingFunction) -> None:
    """Test parsing a journal page."""

    entries = journal_from_yaml(Path("tests/fixtures"), {"Daily", "Monthly"}, "Journal")
    assert len(entries) == 3
    assert entries.keys() == {"Daily", "Journal", "Monthly"}

    # Add the first entry to the index
    k_v = next(iter(entries.items()))
    first_entry = { k_v[0]: k_v[1] }

    db = vectordb.VectorDB(storage_path, "12345")
    db.upsert_index(first_entry)
    assert embedding_function.embeds == 4

    # Add the rest, which skips the duplicate
    db.upsert_index(entries)
    assert embedding_function.embeds == 6

    results = db.query("example", num_results=5)
    assert len(results) == 5
    assert results[0].keys() == {"id", "content", "date", "name", "category"}
    assert results[0]["category"] in ("Daily", "Journal", "Monthly")