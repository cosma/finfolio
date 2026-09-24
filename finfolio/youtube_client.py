"""YouTube Data API v3 wrapper for video discovery and caption fetching."""
import json
from datetime import datetime
from typing import Any

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError


class YouTubeClient:
    """Client for YouTube Data API v3 interactions."""

    def __init__(self, api_key: str) -> None:
        """Initialize YouTube API client."""
        self.api_key = api_key
        self.youtube = build("youtube", "v3", developerKey=api_key)
        self.quota_used = {"search": 0, "caption.list": 0, "caption.download": 0}

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
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "event": "api_error",
                "status": "failed",
                "channel_id": channel_id,
                "error": str(e)
            }))
            raise

    def fetch_captions(self, video_id: str) -> str | None:
        """Fetch captions for a video."""
        try:
            # List available captions
            captions_list = self.youtube.captions().list(
                part="snippet",
                videoId=video_id,
            ).execute()
            self.quota_used["caption.list"] += 50

            items = captions_list.get("items", [])
            if not items:
                return None

            # Download first available caption
            caption_id = items[0]["id"]
            caption_track = self.youtube.captions().download(
                id=caption_id,
                tfmt="srt",  # SubRip format for text-based captions
            ).execute()
            self.quota_used["caption.download"] += 200

            return caption_track.decode("utf-8") if isinstance(caption_track, bytes) else caption_track
        except HttpError as e:
            if e.resp.status == 404:
                # No captions available
                return None
            print(json.dumps({
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "event": "caption_fetch_failed",
                "status": "failed",
                "video_id": video_id,
                "error": str(e)
            }))
            raise

    def get_quota_units_used(self) -> dict[str, int]:
        """Get total quota units consumed."""
        return self.quota_used.copy()
