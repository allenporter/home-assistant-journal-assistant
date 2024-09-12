"""Data model for bullet journal llm."""

import pathlib
from typing import Any

import yaml
from dataclasses import dataclass, field
from mashumaro.config import BaseConfig
from mashumaro.mixins.yaml import DataClassYAMLMixin
from mashumaro.mixins.json import DataClassJSONMixin


@dataclass
class Prompt(DataClassYAMLMixin, DataClassJSONMixin):
    """A bullet journal prompt."""

    prompt: str | None = None
    filename: str | None = None
    created_at: str | None = None
    content: str | None = None

    def as_prompt(self) -> str:
        """Return the prompt."""
        parts = []
        if self.prompt:
            parts.append(self.prompt)
        if self.filename:
            parts.append(f"filename: {self.filename}")
        if self.created_at:
            parts.append(f"created_at: {self.created_at}")
        if self.content:
            parts.append("content:")
            parts.append(self.content)
        return "\n".join(parts)

    class Config(BaseConfig):
        omit_none = False
        code_generation_options = ["TO_DICT_ADD_OMIT_NONE_FLAG"]


@dataclass
class RapidLogEntry:
    """A rapid log entry."""

    type: str
    content: str
    status: str | None = None
    label: str | None = None
    critical: bool | None = None
    date: str | None = None
    entries: list[str] | None = None

    class Config(BaseConfig):
        omit_none = False
        code_generation_options = ["TO_DICT_ADD_OMIT_NONE_FLAG"]


@dataclass
class JournalPage(DataClassYAMLMixin, DataClassJSONMixin):
    """A parsed notebook entry."""

    filename: str
    created_at: str
    label: str | None = None
    date: str | None = None
    content: str | Any | None = None
    records: list[RapidLogEntry] | None = None

    class Config(BaseConfig):
        omit_none = False
        code_generation_options = ["TO_DICT_ADD_OMIT_NONE_FLAG"]


@dataclass
class DynamicPrompt(DataClassYAMLMixin, DataClassJSONMixin):
    """A dynamic prompt."""

    filename: str
    prompt: Prompt
    pages: list[JournalPage] = field(default_factory=list)

    @classmethod
    def from_file(cls, filename: pathlib.Path) -> "DynamicPrompt":
        """Create a dynamic prompt from a file."""
        content = filename.read_text()
        docs = list(yaml.load_all(content, Loader=yaml.CSafeLoader))
        if not docs:
            raise ValueError(f"Failed to parse {filename}")

        prompt = Prompt.from_dict(docs[0])
        pages = [JournalPage.from_dict(doc) for doc in docs[1:]]

        return cls(filename=str(filename), prompt=prompt, pages=pages)

    def as_prompt(self) -> str:
        """Return the prompt."""
        return "\n\n".join(
            [self.prompt.as_prompt(), *(str(page.to_json()) for page in self.pages)]
        )

    class Config(BaseConfig):
        omit_none = False
        code_generation_options = ["TO_DICT_ADD_OMIT_NONE_FLAG"]
