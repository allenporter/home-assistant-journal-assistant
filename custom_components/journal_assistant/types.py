"""Journal Assistant types."""

from .processing.vectordb import VectorDB

from homeassistant.config_entries import ConfigEntry

type JournalAssistantConfigEntry = ConfigEntry[VectorDB]  # type: ignore[valid-type]
