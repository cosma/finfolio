"""Unit tests for transcript fetcher module."""

from unittest.mock import MagicMock

import pytest

from finfolio.transcript_fetcher import TranscriptFetcher


@pytest.mark.unit
class TestTranscriptFetcher:
    """Test transcript fetching and storage."""

    def test_fetch_and_save_success(self, mock_youtube_client):
        """Test successful transcript fetch and save."""
        mock_storage = MagicMock()
        mock_youtube_client.fetch_captions.return_value = "Caption text\nMore captions\n"
        mock_youtube_client.get_video_details.return_value = {"published_at": "2026-09-27T12:00:00Z"}

        fetcher = TranscriptFetcher(mock_youtube_client, mock_storage)

        result = fetcher.fetch_and_save("vid123")

        assert result is True
        mock_youtube_client.fetch_captions.assert_called_once_with("vid123")
        mock_youtube_client.get_video_details.assert_called_once_with("vid123")
        mock_storage.save_transcript.assert_called_once_with(
            "vid123", "Caption text\nMore captions\n", "2026-09-27T12:00:00Z"
        )

    def test_fetch_and_save_returns_false_when_no_captions(self, mock_youtube_client):
        """Test fetch_and_save returns False when captions unavailable."""
        mock_storage = MagicMock()
        mock_youtube_client.fetch_captions.return_value = None

        fetcher = TranscriptFetcher(mock_youtube_client, mock_storage)

        result = fetcher.fetch_and_save("vid123")

        assert result is False
        mock_storage.save_transcript.assert_not_called()

    def test_fetch_and_save_propagates_errors(self, mock_youtube_client):
        """Test fetch_and_save raises on storage errors."""
        mock_storage = MagicMock()
        mock_youtube_client.fetch_captions.return_value = "Caption text"
        mock_storage.save_transcript.side_effect = Exception("Storage error")

        fetcher = TranscriptFetcher(mock_youtube_client, mock_storage)

        with pytest.raises(Exception, match="Storage error"):
            fetcher.fetch_and_save("vid123")

    def test_has_transcript_checks_storage(self, mock_youtube_client):
        """Test has_transcript delegates to storage module."""
        mock_storage = MagicMock()
        mock_storage.has_transcript.return_value = True

        fetcher = TranscriptFetcher(mock_youtube_client, mock_storage)

        result = fetcher.has_transcript("vid123")

        assert result is True
        mock_storage.has_transcript.assert_called_once_with("vid123")

    def test_has_transcript_returns_false_when_missing(self, mock_youtube_client):
        """Test has_transcript returns False for missing transcripts."""
        mock_storage = MagicMock()
        mock_storage.has_transcript.return_value = False

        fetcher = TranscriptFetcher(mock_youtube_client, mock_storage)

        result = fetcher.has_transcript("vid123")

        assert result is False
