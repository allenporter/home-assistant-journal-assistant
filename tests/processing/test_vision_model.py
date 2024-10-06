"""Test the vision model library."""

from pathlib import Path
from unittest.mock import patch, Mock, AsyncMock


from custom_components.journal_assistant.processing.vision_model import (
    VisionModel,
)


async def test_processing_markdown_response() -> None:
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
    mock_genai = AsyncMock()
    mock_genai.generate_content_async.return_value = mock_response

    vision_model = VisionModel(mock_genai)
    with patch(
        "custom_components.journal_assistant.processing.vision_model.PIL.Image.open"
    ):
        result = await vision_model.process_journal_page(
            Path("Daily-2023-12-19"), b"content"
        )
    assert result.filename == "Daily-01-P20221030210760068713clbdtpKcEWTi.png"
    assert result.created_at == "2022-10-30T21:07:60.068713"
    assert result.label == "daily"
    assert result.date == "2022-10-30"


async def test_processing_json_response() -> None:
    """Test processing a journal page."""
    mock_response = Mock()
    mock_response.text = """{
    "filename": "Daily-01-P20221030210760068713clbdtpKcEWTi.png",
    "created_at": "2022-10-30T21:07:60.068713",
    "label": "daily",
    "date": "2022-10-30"
}"""
    mock_genai = AsyncMock()
    mock_genai.generate_content_async.return_value = mock_response

    vision_model = VisionModel(mock_genai)
    with patch(
        "custom_components.journal_assistant.processing.vision_model.PIL.Image.open"
    ):
        result = await vision_model.process_journal_page(
            Path("Daily-2023-12-19"), b"content"
        )
    assert result.filename == "Daily-01-P20221030210760068713clbdtpKcEWTi.png"
    assert result.created_at == "2022-10-30T21:07:60.068713"
    assert result.label == "daily"
    assert result.date == "2022-10-30"
