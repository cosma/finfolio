"""Pytest fixtures for finfolio tests."""

from collections.abc import Generator
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture
def temp_storage_dir(tmp_path: Path) -> Generator[Path, None, None]:
    """Create temporary storage directory for tests."""
    storage_dir = tmp_path / "storage"
    transcripts_dir = storage_dir / "transcripts"
    transcripts_dir.mkdir(parents=True, exist_ok=True)

    # Patch storage module constants
    with patch("finfolio.storage.STORAGE_DIR", storage_dir):
        with patch("finfolio.storage.TRANSCRIPTS_DIR", transcripts_dir):
            with patch("finfolio.storage.STATE_FILE", storage_dir / ".finfolio-state.json"):
                with patch("finfolio.storage.LOCK_FILE", storage_dir / ".finfolio.lock"):
                    yield storage_dir


@pytest.fixture
def temp_config_file(tmp_path: Path) -> str:
    """Create temporary channels.yaml config file for tests."""
    config_file = tmp_path / "channels.yaml"
    config_file.write_text("""channels:
  - channel_id: "UC7_ZLN2t-U-tZ7CgzQ0OoXw"
    display_name: "Graham Stephan"
  - channel_id: "UC_x5XG1OV2P6uZZ5FSM9Ttw"
    display_name: "Two Cents"
""")
    return str(config_file)


@pytest.fixture
def mock_youtube_client() -> MagicMock:
    """Create mock YouTube client with predefined responses."""
    mock_client = MagicMock()

    # Sample video data
    sample_videos = [
        {
            "video_id": "dQw4w9WgXcQ",
            "title": "Sample Video 1",
            "channel_id": "UC7_ZLN2t-U-tZ7CgzQ0OoXw",
            "published_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        },
        {
            "video_id": "jNQXAC9IVRw",
            "title": "Sample Video 2",
            "channel_id": "UC7_ZLN2t-U-tZ7CgzQ0OoXw",
            "published_at": (datetime.now(UTC) - timedelta(days=1))
            .isoformat()
            .replace("+00:00", "Z"),
        },
    ]

    mock_client.search_channel_videos.return_value = sample_videos

    # Sample caption text
    sample_caption = """1
00:00:00,000 --> 00:00:05,000
This is a sample caption.

2
00:00:05,000 --> 00:00:10,000
This is another line.
"""

    mock_client.fetch_captions.return_value = sample_caption
    mock_client.get_quota_units_used.return_value = {
        "search": 100,
        "caption.list": 50,
        "caption.download": 200,
    }

    return mock_client


@pytest.fixture
def sample_video_data() -> dict[str, Any]:
    """Provide sample video data for tests."""
    return {
        "video_id": "dQw4w9WgXcQ",
        "title": "Sample Finance Video",
        "channel_id": "UC7_ZLN2t-U-tZ7CgzQ0OoXw",
        "published_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
    }


@pytest.fixture
def sample_caption_text() -> str:
    """Provide sample caption text for tests."""
    return """1
00:00:00,000 --> 00:00:05,000
The stock market showed positive momentum today.

2
00:00:05,000 --> 00:00:10,000
Technology stocks led the gains.

3
00:00:10,000 --> 00:00:15,000
Investors remain cautious about inflation concerns.
"""
