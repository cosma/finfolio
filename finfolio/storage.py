"""Filesystem abstraction for transcript and state storage."""
import json
import logging
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)
STORAGE_DIR = Path("storage")
TRANSCRIPTS_DIR = STORAGE_DIR / "transcripts"
STATE_FILE = STORAGE_DIR / ".finfolio-state.json"
LOCK_FILE = STORAGE_DIR / ".finfolio.lock"


def _log_operation(event: str, status: str, **kwargs: Any) -> None:
    """Log structured JSON operation to stdout."""
    log_entry = {
        "timestamp": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "event": event,
        "status": status,
        **kwargs
    }
    print(json.dumps(log_entry, default=str))
    sys.stdout.flush()


def ensure_storage_dir() -> None:
    """Create storage directories if missing."""
    TRANSCRIPTS_DIR.mkdir(parents=True, exist_ok=True)
    _log_operation("storage_init", "success", message="Storage directories ready")


def save_transcript(video_id: str, text: str) -> None:
    """Save transcript to file using atomic .tmp pattern."""
    ensure_storage_dir()
    transcript_file = TRANSCRIPTS_DIR / f"{video_id}.txt"
    tmp_file = TRANSCRIPTS_DIR / f"{video_id}.txt.tmp"

    try:
        # Write to temporary file first
        tmp_file.write_text(text, encoding="utf-8")
        # Atomic rename
        tmp_file.replace(transcript_file)
        _log_operation("transcript_saved", "success", video_id=video_id)
    except Exception as e:
        _log_operation("transcript_save_failed", "failed", video_id=video_id, error=str(e))
        raise


def has_transcript(video_id: str) -> bool:
    """Check if transcript file exists."""
    return (TRANSCRIPTS_DIR / f"{video_id}.txt").exists()


def acquire_lock() -> bool:
    """Acquire exclusive lock. Returns False if already locked."""
    ensure_storage_dir()
    if LOCK_FILE.exists():
        return False
    LOCK_FILE.touch()
    _log_operation("lock_acquired", "success")
    return True


def release_lock() -> None:
    """Release exclusive lock."""
    if LOCK_FILE.exists():
        LOCK_FILE.unlink()
    _log_operation("lock_released", "success")


def load_state() -> dict[str, Any]:
    """Load state from JSON file, return {} if missing."""
    if not STATE_FILE.exists():
        return {}
    try:
        return json.loads(STATE_FILE.read_text())
    except Exception as e:
        _log_operation("state_load_failed", "failed", error=str(e))
        return {}


def save_state(state: dict[str, Any]) -> None:
    """Save state to JSON file atomically."""
    ensure_storage_dir()
    tmp_file = STORAGE_DIR / ".finfolio-state.json.tmp"

    try:
        tmp_file.write_text(json.dumps(state, indent=2), encoding="utf-8")
        tmp_file.replace(STATE_FILE)
        _log_operation("state_saved", "success")
    except Exception as e:
        _log_operation("state_save_failed", "failed", error=str(e))
        raise


def cleanup_tmp_files() -> None:
    """Clean up leftover .tmp files from interrupted runs."""
    ensure_storage_dir()
    tmp_files = list(TRANSCRIPTS_DIR.glob("*.tmp"))
    for tmp_file in tmp_files:
        try:
            tmp_file.unlink()
            _log_operation("tmp_cleanup", "success", file=str(tmp_file))
        except Exception as e:
            _log_operation("tmp_cleanup_failed", "failed", file=str(tmp_file), error=str(e))


def update_channel_last_fetch(channel_id: str, timestamp: datetime) -> None:
    """Update last-fetch timestamp for a channel."""
    state = load_state()
    if "channels" not in state:
        state["channels"] = {}
    state["channels"][channel_id] = {"last_fetch": timestamp.isoformat().replace("+00:00", "Z")}
    save_state(state)


def get_channel_last_fetch(channel_id: str) -> datetime | None:
    """Get last-fetch timestamp for a channel."""
    state = load_state()
    if "channels" not in state or channel_id not in state["channels"]:
        return None
    timestamp_str = state["channels"][channel_id].get("last_fetch")
    if timestamp_str:
        # Parse ISO format timestamp
        return datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
    return None


def save_video_metadata(video_id: str, title: str, channel_id: str, published_at: str) -> None:
    """Save video metadata to state file for easy reference and linking."""
    state = load_state()
    if "videos" not in state:
        state["videos"] = {}
    state["videos"][video_id] = {
        "title": title,
        "channel_id": channel_id,
        "published_at": published_at,
        "url": f"https://www.youtube.com/watch?v={video_id}"
    }
    save_state(state)
    _log_operation("video_metadata_saved", "success", video_id=video_id, title=title)


def get_video_metadata(video_id: str) -> dict[str, Any] | None:
    """Retrieve video metadata from state file."""
    state = load_state()
    if "videos" not in state or video_id not in state["videos"]:
        return None
    return state["videos"][video_id]
