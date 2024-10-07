"""Journal Assistant types."""

from dataclasses import dataclass

from homeassistant.config_entries import ConfigEntry

from .processing.vision_model import VisionModel
from .processing.vectordb import VectorDB
from .media_source_listener import MediaSourceListener


@dataclass
class JournalAssistantData:
    """Journal Assistant config entry."""

    vector_db: VectorDB
    vision_model: VisionModel
    media_source_listener: MediaSourceListener


type JournalAssistantConfigEntry = ConfigEntry[JournalAssistantData]  # type: ignore[valid-type]
