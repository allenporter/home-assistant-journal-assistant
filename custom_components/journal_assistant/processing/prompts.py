"""Module for loading and managing prompts."""

import logging
from functools import cache
import re
import datetime
from pathlib import Path

from .model import DynamicPrompt

_LOGGER = logging.getLogger(__name__)

DYNAMIC_PROMPTS_DIR = Path(__file__).parent / "dynamic_prompts"
DEFAULT = [
    "default",
    "rapid_log_legend",
    "profile",
]
FILE_PREFIX_PROMPT_MAP = {
    "Daily": [
        *DEFAULT,
        "daily",
    ],
    "Weekly": [
        *DEFAULT,
        "weekly",
    ],
    "Monthly": [
        *DEFAULT,
        "monthly",
    ],
}

TIMESTAMP_RE = re.compile(r".*?-\d+-P(\d{20}).*")

FILE_PROMPT = """Please answer in json with no other formatting since the answer will be parsed programmatically.

Filename: {filename}
Created At: {created_at}
Content:
"""


@cache
def _load_dynamic_prompts() -> dict[str, DynamicPrompt]:
    """Load all dynamic prompts from the prompts directory."""

    dynamic_prompts = {}
    for filename in DYNAMIC_PROMPTS_DIR.glob("*.yaml"):
        _LOGGER.info(f"Loading dynamic prompt: {filename}")
        dynamic_prompts[filename.stem] = DynamicPrompt.from_file(filename)
    return dynamic_prompts


def get_dynamic_prompts(page_filename: Path) -> list[DynamicPrompt]:
    """Get a set of prompts that match the given prefix"""

    page_name = page_filename.stem
    prefix = page_name.split("-")[0]
    prompt_names = FILE_PREFIX_PROMPT_MAP.get(prefix, DEFAULT)
    dynamic_prompts = _load_dynamic_prompts()
    return [
        value
        for prompt_prefix in prompt_names
        for key, value in dynamic_prompts.items()
        if key.startswith(prompt_prefix)
    ]


def get_file_prompt(path: Path) -> str:
    """Get a prompt for a file."""
    re_match = TIMESTAMP_RE.match(str(path.name))
    if re_match is not None:
        created_at = datetime.datetime.strptime(re_match.group(1), "%Y%m%d%H%M%S%f")
    else:
        created_at = datetime.datetime.now()
    return FILE_PROMPT.format(
        filename=str(path.name), created_at=created_at.isoformat()
    )
