"""YouTube Data API v3 wrapper for video discovery and caption fetching."""
import json
from datetime import UTC, datetime
from typing import Any

from google.auth.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError


class YouTubeClient:
    """Client for YouTube Data API v3 using service account authentication."""

    def __init__(self, credentials: Credentials) -> None:
        """Initialize YouTube API client with service account credentials."""
        self.credentials = credentials
        self.youtube = build("youtube", "v3", credentials=credentials)
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
                "timestamp": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
                "event": "api_error",
                "status": "failed",
                "channel_id": channel_id,
                "error": str(e)
            }))
            raise

    def fetch_captions(self, video_id: str) -> str | None:
        """Fetch captions for a video using official YouTube Data API v3."""
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

            # Download first available caption (usually auto-generated or manual)
            caption_id = items[0]["id"]
            caption_data = self.youtube.captions().download(
                id=caption_id,
                tfmt="srt",  # SubRip format includes timing
            ).execute()
            self.quota_used["caption.download"] += 200

            # Parse SRT format and extract timestamps and text
            caption_text = caption_data.decode("utf-8") if isinstance(caption_data, bytes) else caption_data

            # Format captions with MM:SS timestamps
            formatted_transcript = self._format_transcript_with_timestamps(caption_text)
            return formatted_transcript
        except HttpError as e:
            if e.resp.status == 404:
                # No captions available for this video
                return None
            print(json.dumps({
                "timestamp": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
                "event": "caption_fetch_failed",
                "status": "failed",
                "video_id": video_id,
                "error": str(e)
            }))
            return None

    def _format_transcript_with_timestamps(self, srt_content: str) -> str:
        """Convert SRT format to 'MM:SS caption text' format."""
        lines = srt_content.strip().split('\n')
        formatted_lines = []
        i = 0

        while i < len(lines):
            line = lines[i].strip()

            # Skip empty lines
            if not line:
                i += 1
                continue

            # Check if this is a timestamp line (format: HH:MM:SS,mmm --> HH:MM:SS,mmm)
            if '-->' in line:
                # Extract start time
                start_time = line.split(' --> ')[0].strip()
                # Convert HH:MM:SS,mmm to MM:SS
                time_parts = start_time.split(':')
                minutes = int(time_parts[1])
                seconds = int(time_parts[2].split(',')[0])
                timestamp = f"{minutes:02d}:{seconds:02d}"

                # Next line should be the caption text
                i += 1
                if i < len(lines):
                    caption_text = lines[i].strip()
                    if caption_text and '-->' not in caption_text:
                        formatted_lines.append(f"{timestamp} {caption_text}")

            i += 1

        return '\n'.join(formatted_lines)

    def get_quota_units_used(self) -> dict[str, int]:
        """Get total quota units consumed per operation type."""
        return self.quota_used.copy()
