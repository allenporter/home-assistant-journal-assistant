"""Tests for the prompts module."""

from pathlib import Path

from custom_components.journal_assistant.processing.prompts import (
    get_dynamic_prompts,
    get_file_prompt,
)


def test_get_dynamic_prompts() -> None:
    """Test getting dynamic prompts."""
    page_filename = Path("tests/fixtures/Daily-2023-12-19.yaml")
    prompts = get_dynamic_prompts(page_filename)
    assert [Path(prompt.filename).stem for prompt in prompts] == [
        "default",
        "rapid_log_legend",
        "profile",
        "daily",
    ]


def test_get_file_prompt() -> None:
    """Test getting a file prompt."""
    prompt = get_file_prompt(
        Path("tests/fixtures/Daily-00-P20231220073139675669IR1ax1C4F76D.yaml")
    )
    assert (
        prompt
        == """Please answer in json with no other formatting since the answer will be parsed programmatically.

Filename: Daily-00-P20231220073139675669IR1ax1C4F76D.yaml
Created At: 2023-12-20T07:31:39.675669
Content:
"""
    )
