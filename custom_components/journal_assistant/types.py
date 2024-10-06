"""Journal Assistant types."""

from dataclasses import dataclass
from .processing.vectordb import VectorDB

from homeassistant.config_entries import ConfigEntry


@dataclass
class JournalAssistantData:
    """Journal Assistant config entry."""

    vector_db: VectorDB

type JournalAssistantConfigEntry = ConfigEntry[JournalAssistantData]  # type: ignore[valid-type]
