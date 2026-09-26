"""Unit tests for channel monitor module."""

from unittest.mock import patch

import pytest

from finfolio.channel_monitor import ChannelMonitor


@pytest.mark.unit
class TestChannelMonitor:
    """Test channel monitoring and video discovery."""

    def test_check_channel_returns_new_videos(self, mock_youtube_client):
        """Test check_channel returns list of new videos."""
        monitor = ChannelMonitor(mock_youtube_client)

        mock_youtube_client.search_channel_videos.return_value = [
            {
                "video_id": "vid1",
                "title": "Video 1",
                "channel_id": "UCtest",
                "published_at": "2026-09-24T10:00:00Z",
            },
            {
                "video_id": "vid2",
                "title": "Video 2",
                "channel_id": "UCtest",
                "published_at": "2026-09-24T11:00:00Z",
            },
        ]

        with patch("finfolio.channel_monitor.has_transcript", return_value=False):
            videos = monitor.check_channel("UCtest", "Test Channel")
            assert len(videos) == 2

    def test_check_channel_raises_on_api_error(self, mock_youtube_client):
        """Test check_channel propagates API errors."""
        monitor = ChannelMonitor(mock_youtube_client)
        mock_youtube_client.search_channel_videos.side_effect = Exception("API Error")

        with pytest.raises(Exception, match="API Error"):
            monitor.check_channel("UCtest", "Test Channel")
