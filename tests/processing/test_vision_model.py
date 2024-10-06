"""Test the vision model library."""

from pathlib import Path
from unittest.mock import patch, Mock


from custom_components.journal_assistant.processing.vision_model import (
    process_journal_page,
)


def test_processing_markdown_response() -> None:
    """Test processing a journal page."""
    mock_response = Mock()
    mock_response.text = """```json
{
    "filename": "Daily-01-P20221030210760068713clbdtpKcEWTi.png",
    "created_at": "2022-10-30T21:07:60.068713",
    "label": "daily",
    "date": "2022-10-30"
}
```"""
    mock_genai = Mock()
    mock_genai.generate_content.return_value = mock_response

    with patch(
        "custom_components.journal_assistant.processing.vision_model.PIL.Image.open"
    ):
        result = process_journal_page(mock_genai, Path("Daily-2023-12-19"), b"content")
    assert (
        result
        == """---
filename: Daily-01-P20221030210760068713clbdtpKcEWTi.png
created_at: '2022-10-30T21:07:60.068713'
label: daily
date: '2022-10-30'
"""
    )


def test_processing_json_response() -> None:
    """Test processing a journal page."""
    mock_response = Mock()
    mock_response.text = """{
    "filename": "Daily-01-P20221030210760068713clbdtpKcEWTi.png",
    "created_at": "2022-10-30T21:07:60.068713",
    "label": "daily",
    "date": "2022-10-30"
}"""
    mock_genai = Mock()
    mock_genai.generate_content.return_value = mock_response

    with patch(
        "custom_components.journal_assistant.processing.vision_model.PIL.Image.open"
    ):
        result = process_journal_page(mock_genai, Path("Daily-2023-12-19"), b"content")
    assert (
        result
        == """---
filename: Daily-01-P20221030210760068713clbdtpKcEWTi.png
created_at: '2022-10-30T21:07:60.068713'
label: daily
date: '2022-10-30'
"""
    )
