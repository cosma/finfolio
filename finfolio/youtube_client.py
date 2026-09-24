"""YouTube Data API v3 wrapper for video discovery and transcript fetching."""
import json
from datetime import UTC, datetime
from typing import Any

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api.formatters import TextFormatter


class YouTubeClient:
    """Client for YouTube Data API v3 and transcript fetching."""

    def __init__(self, api_key: str) -> None:
        """Initialize YouTube API client."""
        self.api_key = api_key
        self.youtube = build("youtube", "v3", developerKey=api_key)
        self.quota_used = {"search": 0}

    def search_channel_videos(
        self, channel_id: str, after_timestamp: datetime | None = None
    ) -> list[dict[str, Any]]:
        """Search channel for videos published after timestamp."""
        try:
            published_after = after_timestamp.isoformat() + "Z" if after_timestamp else None

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
        """Fetch transcript for a video."""
        try:
            # Fetch transcript using youtube-transcript-api
            transcript = YouTubeTranscriptApi.get_transcript(video_id)

            # Format transcript as plain text
            formatter = TextFormatter()
            text_transcript = formatter.format_transcript(transcript)
            return text_transcript
        except Exception as e:
            # No transcript available or fetch failed
            print(json.dumps({
                "timestamp": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
                "event": "transcript_fetch_failed",
                "status": "failed",
                "video_id": video_id,
                "error": str(e)
            }))
            return None

    def get_quota_units_used(self) -> dict[str, int]:
        """Get total quota units consumed (search only, transcripts don't use quota)."""
        return self.quota_used.copy()
