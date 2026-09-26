"""Unit tests for YouTube client module."""

from unittest.mock import MagicMock, patch

import pytest

from finfolio.youtube_client import YouTubeClient


@pytest.mark.unit
class TestYouTubeClient:
    """Test YouTube Data API v3 client."""

    def test_initialization_stores_api_key(self):
        """Test client stores API key on initialization."""
        with patch("googleapiclient.discovery.build"):
            client = YouTubeClient("test-key-123")
            assert client.api_key == "test-key-123"

    def test_initialization_sets_quota_tracking(self):
        """Test client initializes quota tracking."""
        with patch("googleapiclient.discovery.build"):
            client = YouTubeClient("test-key-123")
            quota = client.get_quota_units_used()
            assert quota == {"search": 0}

    def test_search_channel_videos_returns_video_list(self):
        """Test search returns list of videos with metadata."""
        mock_request = MagicMock()
        mock_request.execute.return_value = {
            "items": [
                {
                    "id": {"videoId": "vid123"},
                    "snippet": {"title": "Test Video", "publishedAt": "2026-09-24T10:00:00Z"},
                }
            ]
        }

        mock_youtube = MagicMock()
        mock_youtube.search.return_value.list.return_value = mock_request

        with patch("finfolio.youtube_client.build", return_value=mock_youtube):
            client = YouTubeClient("test-key-123")
            videos = client.search_channel_videos("UCtest", after_timestamp=None)

        assert len(videos) == 1
        assert videos[0]["video_id"] == "vid123"

    def test_search_channel_videos_tracks_quota(self):
        """Test search operation tracks 100 quota units."""
        mock_request = MagicMock()
        mock_request.execute.return_value = {"items": []}

        mock_youtube = MagicMock()
        mock_youtube.search.return_value.list.return_value = mock_request

        with patch("finfolio.youtube_client.build", return_value=mock_youtube):
            client = YouTubeClient("test-key-123")
            client.search_channel_videos("UCtest")
            quota = client.get_quota_units_used()

        assert quota["search"] == 100

    def test_fetch_captions_returns_text(self):
        """Test caption fetch returns formatted transcript with timestamps."""
        mock_snippet_1 = MagicMock()
        mock_snippet_1.start = 0
        mock_snippet_1.text = "Welcome to the video"

        mock_snippet_2 = MagicMock()
        mock_snippet_2.start = 5
        mock_snippet_2.text = "Today we discuss"

        mock_snippet_3 = MagicMock()
        mock_snippet_3.start = 10
        mock_snippet_3.text = "An important topic"

        with patch("googleapiclient.discovery.build"):
            with patch("finfolio.youtube_client.YouTubeTranscriptApi") as mock_api_class:
                mock_instance = MagicMock()
                mock_transcript = MagicMock()
                mock_transcript.snippets = [mock_snippet_1, mock_snippet_2, mock_snippet_3]
                mock_instance.fetch.return_value = mock_transcript
                mock_api_class.return_value = mock_instance
                client = YouTubeClient("test-key-123")
                captions = client.fetch_captions("vid123")

        assert captions is not None
        assert "00:00 Welcome to the video" in captions
        assert "00:05 Today we discuss" in captions
        assert "00:10 An important topic" in captions

    def test_fetch_captions_returns_none_when_unavailable(self):
        """Test caption fetch returns None when video has no captions."""
        with patch("googleapiclient.discovery.build"):
            with patch("finfolio.youtube_client.YouTubeTranscriptApi") as mock_api_class:
                mock_instance = MagicMock()
                mock_instance.fetch.side_effect = Exception("No transcripts found")
                mock_api_class.return_value = mock_instance
                client = YouTubeClient("test-key-123")
                captions = client.fetch_captions("vid123")

        assert captions is None
        # Verify error was logged
        assert client.api_key == "test-key-123"

    def test_fetch_captions_handles_network_error(self):
        """Test caption fetch handles network errors gracefully."""
        with patch("googleapiclient.discovery.build"):
            with patch("finfolio.youtube_client.YouTubeTranscriptApi") as mock_api_class:
                mock_instance = MagicMock()
                mock_instance.fetch.side_effect = Exception("Network error")
                mock_api_class.return_value = mock_instance
                client = YouTubeClient("test-key-123")
                captions = client.fetch_captions("vid123")

        assert captions is None
