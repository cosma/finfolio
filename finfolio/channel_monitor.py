"""Channel monitoring for discovering new videos."""
from datetime import datetime
from typing import Any

from finfolio.storage import get_channel_last_fetch, has_transcript
from finfolio.youtube_client import YouTubeClient


class ChannelMonitor:
    """Monitor YouTube channels for new videos."""

    def __init__(self, youtube_client: YouTubeClient) -> None:
        """Initialize channel monitor."""
        self.youtube_client = youtube_client

    def check_channel(
        self, channel_id: str, display_name: str, last_fetch: datetime | None = None
    ) -> list[dict[str, Any]]:
        """Check channel for new videos since last fetch."""
        videos = self.youtube_client.search_channel_videos(channel_id, last_fetch)

        # Filter out videos that already have transcripts (idempotency check)
        new_videos = []
        for video in videos:
            if not has_transcript(video["video_id"]):
                new_videos.append(video)

        return new_videos

    def is_new_video(self, video_id: str) -> bool:
        """Check if video hasn't been transcribed yet."""
        return not has_transcript(video_id)
