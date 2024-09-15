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

    def __call__(self, input: Any) -> chromadb.Embeddings:
        result: chromadb.Embeddings = []
        for item in input:
            result.append([ord(c) for c in hashlib.md5(item.encode()).hexdigest()][0:3])
        return result


@pytest.fixture(autouse=True)
def mock_embedding_function() -> Generator[None, None, None]:
    """Fixture to mock the embedding function."""
    with patch(
        f"custom_components.{DOMAIN}.processing.vectordb.embedding_functions.GoogleGenerativeAiEmbeddingFunction",
        return_value=FakeEmbeddingFunction(),
    ):
        yield


def test_vectordb_loading(storage_path: Path) -> None:
    """Test parsing a journal page."""

    entries = journal_from_yaml(Path("tests/fixtures"), {"Daily", "Monthly"}, "Journal")
    assert entries.keys() == {"Daily", "Journal", "Monthly"}

    db = vectordb.VectorDB(storage_path, "12345")
    db.add_to_index(entries)
    results = db.query("example", num_results=5)
    assert len(results) == 5
    assert results[0].keys() == {"id", "content", "date", "name", "notebook"}
    assert results[0]["notebook"] in ("Daily", "Journal", "Monthly")
