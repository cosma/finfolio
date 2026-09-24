"""Unit tests for YouTube client module."""
from unittest.mock import MagicMock

import pytest
from googleapiclient.errors import HttpError

from finfolio.youtube_client import YouTubeClient


@pytest.mark.unit
class TestYouTubeClient:
    """Test YouTube Data API v3 client."""

    def test_initialization_stores_api_key(self):
        """Test client stores API key on initialization."""
        client = YouTubeClient(api_key="test-key")
        assert client.api_key == "test-key"

    def test_initialization_sets_quota_tracking(self):
        """Test client initializes quota tracking."""
        client = YouTubeClient(api_key="test-key")
        quota = client.get_quota_units_used()
        assert quota == {"search": 0, "caption.list": 0, "caption.download": 0}

    def test_search_channel_videos_returns_video_list(self):
        """Test search returns list of videos with metadata."""
        mock_youtube = MagicMock()
        mock_request = MagicMock()
        mock_youtube.search().list.return_value = mock_request
        mock_request.execute.return_value = {
            "items": [
                {
                    "id": {"videoId": "vid123"},
                    "snippet": {
                        "title": "Test Video",
                        "publishedAt": "2026-09-24T10:00:00Z"
                    }
                }
            ]
        }

        client = YouTubeClient(api_key="test-key")
        client.youtube = mock_youtube

        videos = client.search_channel_videos("UCtest", after_timestamp=None)

        assert len(videos) == 1
        assert videos[0]["video_id"] == "vid123"

    def test_search_channel_videos_tracks_quota(self):
        """Test search operation tracks 100 quota units."""
        mock_youtube = MagicMock()
        mock_request = MagicMock()
        mock_youtube.search().list.return_value = mock_request
        mock_request.execute.return_value = {"items": []}

        client = YouTubeClient(api_key="test-key")
        client.youtube = mock_youtube

        client.search_channel_videos("UCtest")
        quota = client.get_quota_units_used()

        assert quota["search"] == 100

    def test_fetch_captions_returns_text(self):
        """Test caption fetch returns raw caption text."""
        mock_youtube = MagicMock()
        mock_captions_list = MagicMock()
        mock_captions_download = MagicMock()

        mock_youtube.captions().list.return_value = mock_captions_list
        mock_captions_list.execute.return_value = {"items": [{"id": "caption123"}]}

        mock_youtube.captions().download.return_value = mock_captions_download
        mock_captions_download.execute.return_value = b"Caption text"

        client = YouTubeClient(api_key="test-key")
        client.youtube = mock_youtube

        captions = client.fetch_captions("vid123")
        assert captions is not None

    def test_fetch_captions_returns_none_when_unavailable(self):
        """Test caption fetch returns None when video has no captions."""
        mock_youtube = MagicMock()
        mock_captions_list = MagicMock()
        mock_youtube.captions().list.return_value = mock_captions_list
        mock_captions_list.execute.return_value = {"items": []}

        client = YouTubeClient(api_key="test-key")
        client.youtube = mock_youtube

        captions = client.fetch_captions("vid123")
        assert captions is None

    def test_fetch_captions_handles_404_no_captions(self):
        """Test caption fetch handles 404 (no captions) gracefully."""
        mock_youtube = MagicMock()
        mock_captions_list = MagicMock()
        mock_youtube.captions().list.return_value = mock_captions_list
        http_error = HttpError(MagicMock(status=404), b"Not Found")
        mock_captions_list.execute.side_effect = http_error

        client = YouTubeClient(api_key="test-key")
        client.youtube = mock_youtube

        captions = client.fetch_captions("vid123")
        assert captions is None
