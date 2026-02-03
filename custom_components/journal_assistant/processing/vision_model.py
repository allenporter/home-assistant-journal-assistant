"""Multi-modal vision model for processing journal pages."""

import asyncio
import re
import logging
import json
import yaml
import datetime
from pathlib import Path

import numpy as np
from google import genai
from google.genai import types
from mashumaro.exceptions import MissingField

from .prompts import get_dynamic_prompts
from .model import JournalPage
from custom_components.journal_assistant.vectordb import Embedding


_LOGGER = logging.getLogger(__name__)

TIMESTAMP_RE = re.compile(r".*?-\d+-P(\d{20}).*?")

FILE_PROMPT = """
Please answer in json with no other formatting since the answer will be parsed programmatically.

Filename: {filename}
Created At: {created_at}
Content:
"""
EXTRACT_JSON = re.compile("```json\n(.*?)\n```", re.DOTALL)

EMBED_MODEL = "models/text-embedding-004"


def _parse_model_response(response_text: str) -> str:
    """Parse the response from the model and return a yaml string."""

    if (match := EXTRACT_JSON.match(response_text)) is not None:
        text = match.group(1)
    else:
        text = response_text

    try:
        obj = json.loads(text)
    except ValueError as err:
        _LOGGER.error("Error processing: %s", err)
        return text

    for k, v in list(obj.items()):
        if v is None or v == "null":
            del obj[k]

    return yaml.dump(obj, explicit_start=True, sort_keys=False)


class VisionModel:
    """Multi-modal vision model for processing journal pages."""

    def __init__(self, client: genai.Client, model: str) -> None:
        """Initialize the vision model."""
        self._client = client
        self._model = model

    async def process_journal_page(
        self, page_name: Path, page_content: bytes
    ) -> JournalPage:
        """Process a journal page using a multi-modal vision model.

        The response is typically a yaml content string.
        """
        _LOGGER.debug("Extract content from page %s", str(page_name))

        if (re_match := TIMESTAMP_RE.match(str(page_name))) is None:
            raise ValueError(f"Error extracting timestamp from {str(page_name)}")
        _LOGGER.debug("Timestamp match: %s", re_match.group(1))
        created_at = datetime.datetime.strptime(re_match.group(1), "%Y%m%d%H%M%S%f")

        loop = asyncio.get_event_loop()
        prompts = await loop.run_in_executor(None, get_dynamic_prompts, page_name)

        contents = types.Content(
            parts=[
                types.Part(
                    text=FILE_PROMPT.format(
                        filename=page_name.name,
                        created_at=created_at.isoformat(),
                    )
                ),
                types.Part(
                    inline_data=types.Blob(
                        mime_type="image/png",
                        data=page_content,
                    )
                ),
            ]
        )
        response = await self._client.aio.models.generate_content(
            model=self._model,
            config=types.GenerateContentConfig(
                system_instruction=[p.as_prompt() for p in prompts],
            ),
            contents=contents,
        )

        try:
            text = response.text or ""
        except AttributeError as err:
            raise ValueError("AttributeError with response.text") from err
        yaml_content = _parse_model_response(text)
        try:
            return JournalPage.from_yaml(yaml_content)
        except MissingField as err:
            raise ValueError(f"Error parsing journal page: {err}")

    async def _embed_query_async(
        self, texts: list[str], task_type: str
    ) -> list[Embedding]:
        """Embed a text query."""
        if not texts:
            return []

        result = await self._client.aio.models.embed_content(
            model=EMBED_MODEL,
            contents=texts,  # type: ignore[invalid-argument-type]
            config=types.EmbedContentConfig(task_type=task_type),
        )
        embeddings = []
        for content_embedding in result.embeddings or ():
            if content_embedding.values is None:
                raise ValueError(
                    f"Error embedding content had no values: {content_embedding}"
                )
            embeddings.append(Embedding(embedding=np.array(content_embedding.values)))
        return embeddings

    async def embed_query_async(self, texts: list[str]) -> list[Embedding]:
        """Embed a text query."""
        return await self._embed_query_async(texts, "RETRIEVAL_QUERY")

    async def embed_document_async(self, texts: list[str]) -> list[Embedding]:
        """Embed a text query."""
        return await self._embed_query_async(texts, "RETRIEVAL_DOCUMENT")
