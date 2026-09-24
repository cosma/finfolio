"""Channel monitoring for discovering new videos."""
import json
import sys
from datetime import datetime
from typing import Any, Optional

from finfolio.storage import has_transcript
from finfolio.youtube_client import YouTubeClient


def _log_monitor(event: str, status: str, **kwargs: Any) -> None:
    """Log monitor operation as JSON."""
    log_entry = {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "event": event,
        "status": status,
        **kwargs
    }
    print(json.dumps(log_entry, default=str))
    sys.stdout.flush()


class ChannelMonitor:
    """Monitor YouTube channels for new videos."""

    def __init__(self, youtube_client: YouTubeClient) -> None:
        """Initialize channel monitor."""
        self.youtube_client = youtube_client
        _log_monitor("channel_monitor_init", "success")

    def check_channel(
        self, channel_id: str, display_name: str, last_fetch: Optional[datetime] = None
    ) -> list[dict[str, Any]]:
        """Check channel for new videos since last fetch.

        Args:
            channel_id: YouTube channel ID
            display_name: Human-readable channel name
            last_fetch: Optional timestamp to limit search (videos after this time)

        Returns:
            List of new videos (those without existing transcripts)
        """
        _log_monitor("check_channel_start", "success", channel_id=channel_id,
                     display_name=display_name)

        try:
            videos = self.youtube_client.search_channel_videos(channel_id, last_fetch)

            # Filter out videos that already have transcripts (idempotency check)
            new_videos = []
            for video in videos:
                if not has_transcript(video["video_id"]):
                    new_videos.append(video)

            _log_monitor("check_channel_complete", "success", channel_id=channel_id,
                        total_videos=len(videos), new_videos=len(new_videos))
            return new_videos
        except Exception as e:
            _log_monitor("check_channel_failed", "failed", channel_id=channel_id,
                        error=str(e))
            raise

    def is_new_video(self, video_id: str) -> bool:
        """Check if video hasn't been transcribed yet."""
        return not has_transcript(video_id)
