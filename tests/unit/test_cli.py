"""Unit tests for CLI module."""
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from finfolio.cli import main


@pytest.fixture
def mock_config(tmp_path):
    """Create mock config with test channels."""
    return {
        "config_path": str(tmp_path / "channels.yaml"),
        "channels": [
            {"channel_id": "UCtest1", "display_name": "Test Channel 1"},
            {"channel_id": "UCtest2", "display_name": "Test Channel 2"},
        ]
    }


@pytest.fixture
def mock_youtube_client_full(mock_youtube_client):
    """Extend mock with fetch transcript capability."""
    mock_youtube_client.fetch_captions.return_value = "Sample caption text"
    return mock_youtube_client


@pytest.mark.unit
class TestFetchCommand:
    """Test finfolio fetch command."""

    def test_fetch_initializes_with_config_path(self, mock_config):
        """Test fetch command initializes with provided config path."""
        from click.testing import CliRunner
        runner = CliRunner()

        # Create a temporary channels.yaml
        config_file = Path(mock_config["config_path"])
        config_file.write_text("channels:\n  - channel_id: UCtest1\n    display_name: Test\n")

        with patch("finfolio.cli.load_api_key", return_value="test-key"):
            with patch("finfolio.cli.load_config", return_value=mock_config["channels"]):
                with patch("finfolio.cli.storage.acquire_lock", return_value=True):
                    with patch("finfolio.cli.storage.release_lock"):
                        with patch("finfolio.cli.YouTubeClient"):
                            with patch("finfolio.cli.ChannelMonitor"):
                                with patch("finfolio.cli.TranscriptFetcher"):
                                    result = runner.invoke(main, ["fetch"])
                                    assert result.exit_code == 0

    def test_fetch_handles_missing_api_key(self, temp_storage_dir):
        """Test fetch fails gracefully with missing API key."""
        from click.testing import CliRunner
        runner = CliRunner()

        with patch("finfolio.cli.load_api_key", side_effect=ValueError("API key not found")):
            result = runner.invoke(main, ["fetch"])
            assert result.exit_code == 1

    def test_fetch_acquires_lock_before_processing(self, mock_config):
        """Test fetch acquires lock to prevent concurrent runs."""
        from click.testing import CliRunner
        runner = CliRunner()

        mock_acquire_lock = MagicMock(return_value=True)

        config_file = Path(mock_config["config_path"])
        config_file.write_text("channels:\n  - channel_id: UCtest1\n    display_name: Test\n")

        with patch("finfolio.cli.load_api_key", return_value="test-key"):
            with patch("finfolio.cli.load_config", return_value=mock_config["channels"]):
                with patch("finfolio.cli.storage.acquire_lock", mock_acquire_lock):
                    with patch("finfolio.cli.storage.release_lock"):
                        with patch("finfolio.cli.YouTubeClient"):
                            with patch("finfolio.cli.ChannelMonitor"):
                                with patch("finfolio.cli.TranscriptFetcher"):
                                    runner.invoke(main, ["fetch"])
                                    mock_acquire_lock.assert_called_once()

    def test_fetch_fails_when_already_locked(self, mock_config):
        """Test fetch exits with error when lock already held."""
        from click.testing import CliRunner
        runner = CliRunner()

        config_file = Path(mock_config["config_path"])
        config_file.write_text("channels:\n  - channel_id: UCtest1\n    display_name: Test\n")

        with patch("finfolio.cli.load_api_key", return_value="test-key"):
            with patch("finfolio.cli.load_config", return_value=mock_config["channels"]):
                with patch("finfolio.cli.storage.acquire_lock", return_value=False):
                    result = runner.invoke(main, ["fetch"])
                    assert result.exit_code == 2

    def test_fetch_releases_lock_on_completion(self, mock_config):
        """Test fetch releases lock after processing completes."""
        from click.testing import CliRunner
        runner = CliRunner()

        mock_release_lock = MagicMock()

        config_file = Path(mock_config["config_path"])
        config_file.write_text("channels:\n  - channel_id: UCtest1\n    display_name: Test\n")

        with patch("finfolio.cli.load_api_key", return_value="test-key"):
            with patch("finfolio.cli.load_config", return_value=mock_config["channels"]):
                with patch("finfolio.cli.storage.acquire_lock", return_value=True):
                    with patch("finfolio.cli.storage.release_lock", mock_release_lock):
                        with patch("finfolio.cli.YouTubeClient"):
                            with patch("finfolio.cli.ChannelMonitor", return_value=MagicMock(check_channel=MagicMock(return_value=[]))):
                                with patch("finfolio.cli.TranscriptFetcher"):
                                    runner.invoke(main, ["fetch"])
                                    mock_release_lock.assert_called_once()

    def test_fetch_continues_on_channel_failure(self, mock_config, temp_storage_dir):
        """Test fetch continues processing other channels if one fails."""
        from click.testing import CliRunner
        runner = CliRunner()

        channels = [
            {"channel_id": "UCtest1", "display_name": "Test 1"},
            {"channel_id": "UCtest2", "display_name": "Test 2"},
        ]

        mock_monitor = MagicMock()
        mock_monitor.check_channel.side_effect = [Exception("API error"), []]

        with patch("finfolio.cli.load_api_key", return_value="test-key"):
            with patch("finfolio.cli.load_config", return_value=channels):
                with patch("finfolio.cli.storage.acquire_lock", return_value=True):
                    with patch("finfolio.cli.storage.release_lock"):
                        with patch("finfolio.cli.YouTubeClient"):
                            with patch("finfolio.cli.ChannelMonitor", return_value=mock_monitor):
                                with patch("finfolio.cli.TranscriptFetcher"):
                                    result = runner.invoke(main, ["fetch"])
                                    # Should complete successfully despite first channel failure
                                    assert result.exit_code == 0

    def test_fetch_saves_video_metadata(self, mock_config, temp_storage_dir):
        """Test fetch saves video metadata for each fetched video."""
        from click.testing import CliRunner
        runner = CliRunner()

        video_data = {
            "video_id": "test_vid",
            "title": "Test Video",
            "channel_id": "UCtest1",
            "published_at": "2026-09-24T10:00:00Z"
        }

        mock_monitor = MagicMock()
        mock_monitor.check_channel.return_value = [video_data]

        mock_fetcher = MagicMock()
        mock_fetcher.has_transcript.return_value = False
        mock_fetcher.fetch_and_save.return_value = True

        mock_save_metadata = MagicMock()

        with patch("finfolio.cli.load_api_key", return_value="test-key"):
            with patch("finfolio.cli.load_config", return_value=mock_config["channels"]):
                with patch("finfolio.cli.storage.acquire_lock", return_value=True):
                    with patch("finfolio.cli.storage.release_lock"):
                        with patch("finfolio.cli.storage.save_video_metadata", mock_save_metadata):
                            with patch("finfolio.cli.YouTubeClient"):
                                with patch("finfolio.cli.ChannelMonitor", return_value=mock_monitor):
                                    with patch("finfolio.cli.TranscriptFetcher", return_value=mock_fetcher):
                                        runner.invoke(main, ["fetch"])
                                        # Verify metadata saved for the video
                                        mock_save_metadata.assert_called()

    def test_fetch_handles_no_channels_configured(self):
        """Test fetch fails gracefully when no channels configured."""
        from click.testing import CliRunner
        runner = CliRunner()

        with patch("finfolio.cli.load_api_key", return_value="test-key"):
            with patch("finfolio.cli.load_config", return_value=[]):
                with patch("finfolio.cli.storage.acquire_lock", return_value=True):
                    with patch("finfolio.cli.storage.release_lock"):
                        result = runner.invoke(main, ["fetch"])
                        assert result.exit_code == 1
