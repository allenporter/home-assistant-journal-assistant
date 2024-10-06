"""Journal Assistant types."""

from dataclasses import dataclass

from homeassistant.config_entries import ConfigEntry

from .processing.vision_model import VisionModel
from .processing.vectordb import VectorDB


@dataclass
class JournalAssistantData:
    """Journal Assistant config entry."""

    vector_db: VectorDB
    vision_model: VisionModel


type JournalAssistantConfigEntry = ConfigEntry[JournalAssistantData]  # type: ignore[valid-type]
