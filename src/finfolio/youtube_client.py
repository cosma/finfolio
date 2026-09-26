"""YouTube Data API v3 wrapper for video discovery and transcript fetching."""
import json
from datetime import UTC, datetime
from typing import Any

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from youtube_transcript_api import YouTubeTranscriptApi


class YouTubeClient:
    """Client for YouTube Data API v3 (search) and transcript fetching via youtube-transcript-api."""

    def __init__(self, api_key: str) -> None:
        """Initialize YouTube API client with API key."""
        self.api_key = api_key
        self.youtube = build("youtube", "v3", developerKey=api_key)
        self.quota_used = {"search": 0}

    def search_channel_videos(
        self, channel_id: str, after_timestamp: datetime | None = None
    ) -> list[dict[str, Any]]:
        """Search channel for videos published after timestamp."""
        try:
            # Format timestamp for YouTube API (RFC 3339 without offset, just Z)
            published_after = None
            if after_timestamp:
                # Remove timezone info, format as UTC string, then add Z
                published_after = (
                    after_timestamp.replace(microsecond=0, tzinfo=None).isoformat() + "Z"
                )

            request = self.youtube.search().list(
                part="snippet",
                channelId=channel_id,
                type="video",
                order="date",
                publishedAfter=published_after,
                maxResults=50,
            )

            response = request.execute()
            self.quota_used["search"] += 100  # Estimated quota for search

            videos = []
            for item in response.get("items", []):
                video_id = item["id"]["videoId"]
                title = item["snippet"]["title"]
                published_at = item["snippet"]["publishedAt"]
                videos.append({
                    "video_id": video_id,
                    "title": title,
                    "channel_id": channel_id,
                    "published_at": published_at,
                })

            return videos
        except HttpError as e:
            print(json.dumps({
                "timestamp": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
                "event": "api_error",
                "status": "failed",
                "channel_id": channel_id,
                "error": str(e)
            }))
            raise

    def fetch_captions(self, video_id: str) -> str | None:
        """Fetch transcript for a video using youtube-transcript-api."""
        try:
            # Fetch transcript using youtube-transcript-api
            transcript = YouTubeTranscriptApi().fetch(video_id)

            # Format transcript with MM:SS timestamps
            formatted_lines = []
            for entry in transcript.snippets:
                start_seconds = int(entry.start)
                minutes = start_seconds // 60
                seconds = start_seconds % 60
                timestamp = f"{minutes:02d}:{seconds:02d}"
                text = entry.text
                formatted_lines.append(f"{timestamp} {text}")

            return "\n".join(formatted_lines)
        except Exception as e:
            error_str = str(e)
            print(json.dumps({
                "timestamp": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
                "event": "transcript_fetch_failed",
                "status": "failed",
                "video_id": video_id,
                "error": error_str
            }))

            # Re-raise IP block errors so caller can stop immediately
            if "too many requests" in error_str.lower() or "blocked" in error_str.lower():
                raise

            # For other errors (no captions, etc.), just return None
            return None


    def get_quota_units_used(self) -> dict[str, int]:
        """Get total quota units consumed per operation type."""
        return self.quota_used.copy()
