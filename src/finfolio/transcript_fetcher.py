"""Transcript fetching and storage."""
import json
import sys
from datetime import UTC, datetime
from typing import Any

from finfolio.youtube_client import YouTubeClient


def _log_fetcher(event: str, status: str, **kwargs: Any) -> None:
    """Log fetcher operation as JSON."""
    log_entry = {
        "timestamp": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "event": event,
        "status": status,
        **kwargs
    }
    print(json.dumps(log_entry, default=str))
    sys.stdout.flush()


class TranscriptFetcher:
    """Fetch and store transcripts from YouTube videos."""

    def __init__(self, youtube_client: YouTubeClient, storage_module: Any) -> None:
        """Initialize transcript fetcher.

        Args:
            youtube_client: YouTube API client
            storage_module: Storage module for saving transcripts
        """
        self.youtube_client = youtube_client
        self.storage = storage_module
        _log_fetcher("transcript_fetcher_init", "success")

    def has_transcript(self, video_id: str) -> bool:
        """Check if transcript already exists for a video.

        Args:
            video_id: YouTube video ID

        Returns:
            True if transcript exists, False otherwise
        """
        exists = self.storage.has_transcript(video_id)
        _log_fetcher("has_transcript", "success", video_id=video_id, exists=exists)
        return exists

    def fetch_and_save(self, video_id: str) -> bool:
        """Fetch captions from YouTube and save transcript with publication_timestamp.

        Args:
            video_id: YouTube video ID

        Returns:
            True if transcript was successfully fetched and saved, False if no captions available

        Raises:
            Exception: On API or storage errors
        """
        try:
            # Fetch captions from YouTube
            caption_text = self.youtube_client.fetch_captions(video_id)

            if caption_text is None:
                _log_fetcher("fetch_and_save", "skipped", video_id=video_id,
                            reason="no_captions_available")
                return False

            # Fetch video details to get publication timestamp
            video_details = self.youtube_client.get_video_details(video_id)
            if not video_details:
                raise RuntimeError(f"Video details unavailable for {video_id}; not saving transcript")
            publication_timestamp = video_details["published_at"]

            # Save transcript to storage with publication_timestamp
            self.storage.save_transcript(video_id, caption_text, publication_timestamp)
            _log_fetcher("fetch_and_save", "success", video_id=video_id,
                        publication_timestamp=publication_timestamp)
            return True

        except Exception as e:
            _log_fetcher("fetch_and_save", "failed", video_id=video_id, error=str(e))
            raise
