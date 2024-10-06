"""Multi-modal vision model for processing journal pages."""

import io
import re
import logging
import json
import yaml
from typing import cast
import datetime
from pathlib import Path

import google.generativeai as genai
import PIL.Image
from mashumaro.exceptions import MissingField

from .prompts import get_dynamic_prompts
from .model import JournalPage

_LOGGER = logging.getLogger(__name__)

TIMESTAMP_RE = re.compile(r".*?-\d+-P(\d{20}).*.png")

FILE_PROMPT = """
Please answer in json with no other formatting since the answer will be parsed programmatically.

Filename: {filename}
Created At: {created_at}
Content:
"""
EXTRACT_JSON = re.compile("```json\n(.*?)\n```", re.DOTALL)


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

    return cast(str, yaml.dump(obj, explicit_start=True, sort_keys=False))


class VisionModel:
    """Multi-modal vision model for processing journal pages."""

    def __init__(self, model: genai.GenerativeModel) -> None:
        """Initialize the vision model."""
        self._model = model

    async def process_journal_page(
        self, page_name: Path, page_content: bytes
    ) -> JournalPage:
        """Process a journal page using a multi-modal vision model.

        The response is typically a yaml content string.
        """
        _LOGGER.debug("Extract content from page %s", str(page_name))

        created_at: datetime.datetime | None = None
        if (re_match := TIMESTAMP_RE.match(str(page_name))) is not None:
            created_at = datetime.datetime.strptime(re_match.group(1), "%Y%m%d%H%M%S%f")

        prompts = get_dynamic_prompts(page_name)
        prompt = "\n\n".join([p.as_prompt() for p in prompts])

        img = PIL.Image.open(io.BytesIO(page_content))

        response = await self._model.generate_content_async(
            [
                prompt,
                FILE_PROMPT.format(
                    filename=f"{page_name.stem}.png",
                    created_at=created_at.isoformat() if created_at else "N/A",
                ),
                img,
            ]
        )

        yaml_content = _parse_model_response(response.text)
        try:
            return JournalPage.from_yaml(yaml_content)
        except MissingField as err:
            raise ValueError(f"Error parsing journal page: {err}")
