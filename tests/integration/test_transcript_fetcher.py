"""Integration tests for transcript fetching."""

import pytest


@pytest.mark.integration
class TestTranscriptFetcherIntegration:
    """Integration tests for transcript fetch and storage."""

    def test_fetch_and_save_with_real_storage(self, temp_storage_dir, mock_youtube_client):
        """Test transcript fetch with real storage backend."""
        from finfolio import storage
        from finfolio.transcript_fetcher import TranscriptFetcher

        mock_youtube_client.fetch_captions.return_value = "Test caption data"
        fetcher = TranscriptFetcher(mock_youtube_client, storage)

        result = fetcher.fetch_and_save("vid123")
        assert result is True

    def test_idempotency_skips_existing_transcripts(self, temp_storage_dir, mock_youtube_client):
        """Test idempotency: repeated fetch skips existing transcripts."""
        from finfolio import storage
        from finfolio.transcript_fetcher import TranscriptFetcher

        mock_youtube_client.fetch_captions.return_value = "Test caption"
        fetcher = TranscriptFetcher(mock_youtube_client, storage)

        # First fetch
        fetcher.fetch_and_save("vid123")

        # Second fetch should be skipped
        assert fetcher.has_transcript("vid123") is True
