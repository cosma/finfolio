"""Integration tests for channel monitoring."""
import pytest


@pytest.mark.integration
class TestChannelMonitorIntegration:
    """Integration tests for full channel monitoring flow."""

    def test_check_channel_with_real_storage(self, temp_storage_dir, mock_youtube_client):
        """Test channel monitor with real storage backend."""
        from finfolio.channel_monitor import ChannelMonitor

        monitor = ChannelMonitor(mock_youtube_client)
        videos = monitor.check_channel("UCtest", "Test Channel")

        assert isinstance(videos, list)

    def test_idempotency_skips_existing_videos(self, temp_storage_dir, mock_youtube_client):
        """Test repeated monitoring skips already-fetched videos."""
        from finfolio import storage
        from finfolio.channel_monitor import ChannelMonitor

        monitor = ChannelMonitor(mock_youtube_client)
        videos = monitor.check_channel("UCtest", "Test Channel")

        if videos:
            storage.save_transcript(videos[0]["video_id"], "test transcript")
            videos_2 = monitor.check_channel("UCtest", "Test Channel")
            assert len(videos_2) < len(videos)
