"""FinFolio: Fact-checking system for finance content with YouTube transcript ingestion."""

__version__ = "0.1.0"

from finfolio.channel_monitor import ChannelMonitor
from finfolio.config import load_api_key, load_config
from finfolio.storage import (
    acquire_lock,
    cleanup_tmp_files,
    ensure_storage_dir,
    get_channel_last_fetch,
    has_transcript,
    load_state,
    release_lock,
    save_state,
    save_transcript,
    update_channel_last_fetch,
)
from finfolio.transcript_fetcher import TranscriptFetcher
from finfolio.youtube_client import YouTubeClient

__all__ = [
    "ChannelMonitor",
    "TranscriptFetcher",
    "YouTubeClient",
    "load_api_key",
    "load_config",
    "acquire_lock",
    "cleanup_tmp_files",
    "ensure_storage_dir",
    "get_channel_last_fetch",
    "has_transcript",
    "load_state",
    "release_lock",
    "save_state",
    "save_transcript",
    "update_channel_last_fetch",
]
