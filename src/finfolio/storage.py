"""Filesystem abstraction for transcript and state storage."""

import json
import logging
import os
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class StoredFileError(ValueError):
    """A stored file exists but cannot be parsed. The message names the item."""


STORAGE_DIR = Path("storage")
TRANSCRIPTS_DIR = STORAGE_DIR / "transcripts"
SUMMARIES_DIR = STORAGE_DIR / "summaries"
STATE_FILE = STORAGE_DIR / ".finfolio-state.json"
LOCK_FILE = STORAGE_DIR / ".finfolio.lock"


def _log_operation(event: str, status: str, **kwargs: Any) -> None:
    """Log structured JSON operation to stdout."""
    log_entry = {
        "timestamp": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "event": event,
        "status": status,
        **kwargs,
    }
    print(json.dumps(log_entry, default=str))
    sys.stdout.flush()


def ensure_storage_dir() -> None:
    """Create storage directories if missing."""
    TRANSCRIPTS_DIR.mkdir(parents=True, exist_ok=True)
    _log_operation("storage_init", "success", message="Storage directories ready")


def save_transcript(video_id: str, text: str, publication_timestamp: str | None = None) -> None:
    """Save transcript as JSON with publication_timestamp and content.

    Args:
        video_id: YouTube video ID
        text: Transcript text content
        publication_timestamp: ISO 8601 UTC publication timestamp (optional)
    """
    ensure_storage_dir()
    transcript_file = TRANSCRIPTS_DIR / f"{video_id}.json"
    tmp_file = TRANSCRIPTS_DIR / f"{video_id}.json.tmp"

    try:
        transcript_data = {"publication_timestamp": publication_timestamp, "content": text}
        tmp_file.write_text(json.dumps(transcript_data, indent=2), encoding="utf-8")
        tmp_file.replace(transcript_file)
        _log_operation(
            "transcript_saved",
            "success",
            video_id=video_id,
            publication_timestamp=publication_timestamp,
        )
    except Exception as e:
        _log_operation("transcript_save_failed", "failed", video_id=video_id, error=str(e))
        raise


def has_transcript(video_id: str) -> bool:
    """Check if transcript file exists (supports both .json and legacy .txt)."""
    json_file = TRANSCRIPTS_DIR / f"{video_id}.json"
    txt_file = TRANSCRIPTS_DIR / f"{video_id}.txt"
    return json_file.exists() or txt_file.exists()


def load_transcript(video_id: str) -> dict[str, Any] | None:
    """Load transcript from JSON file, return None if not found."""
    json_file = TRANSCRIPTS_DIR / f"{video_id}.json"
    if json_file.exists():
        try:
            transcript: dict[str, Any] = json.loads(json_file.read_text())
            return transcript
        except Exception as e:
            logger.error(f"Failed to load transcript {video_id}: {e}")
            return None
    return None


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
        state: dict[str, Any] = json.loads(STATE_FILE.read_text())
        return state
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
        "url": f"https://www.youtube.com/watch?v={video_id}",
    }
    save_state(state)
    _log_operation("video_metadata_saved", "success", video_id=video_id, title=title)


def get_video_metadata(video_id: str) -> dict[str, Any] | None:
    """Retrieve video metadata from state file."""
    state = load_state()
    if "videos" not in state or video_id not in state["videos"]:
        return None
    video: dict[str, Any] = state["videos"][video_id]
    return video


def get_videos_by_channel(channel_id: str) -> list[dict[str, Any]]:
    """Retrieve all videos fetched from a specific channel."""
    state = load_state()
    if "videos" not in state:
        return []

    videos = []
    for video_id, metadata in state["videos"].items():
        if metadata.get("channel_id") == channel_id:
            videos.append({**metadata, "video_id": video_id})

    return videos


def ensure_summaries_dir() -> None:
    """Create storage/summaries/ directory if missing."""
    SUMMARIES_DIR.mkdir(parents=True, exist_ok=True)
    _log_operation("storage_init", "success", message="Summaries directory ready")


def has_summary(video_id: str) -> bool:
    """Check if summary file exists for a video."""
    return (SUMMARIES_DIR / f"{video_id}.json").exists()


def get_summaries_dir() -> Path:
    """Return path to summaries directory."""
    return SUMMARIES_DIR


def save_summary(video_id: str, summary_data: dict[str, Any]) -> None:
    """Save summary to file using atomic .tmp pattern."""
    ensure_summaries_dir()
    summary_file = SUMMARIES_DIR / f"{video_id}.json"
    tmp_file = SUMMARIES_DIR / f"{video_id}.json.tmp"

    try:
        # Write to temporary file first
        tmp_file.write_text(json.dumps(summary_data, indent=2, default=str), encoding="utf-8")
        # Atomic rename
        tmp_file.replace(summary_file)
        _log_operation("summary_saved", "success", video_id=video_id)
    except Exception as e:
        _log_operation("summary_save_failed", "failed", video_id=video_id, error=str(e))
        raise


# Fact-checking module (Module 3) storage functions

REPORTS_DIR = STORAGE_DIR / "reports" / "videos"


def ensure_reports_dir() -> None:
    """Create storage/reports/videos/ directory if missing."""
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    _log_operation("storage_init", "success", message="Reports directory ready")


def save_report(video_id: str, report_data: dict[str, Any]) -> None:
    """Save fact-checking report to file using atomic .tmp pattern.

    Validates report_data against ReportModel schema before writing.
    Creates storage/reports/videos/ directory if missing.
    """
    from finfolio.models import ReportModel

    ensure_reports_dir()

    try:
        # Validate report_data against schema
        ReportModel(**report_data)
    except Exception as e:
        _log_operation("report_validation_failed", "failed", video_id=video_id, error=str(e))
        raise

    report_file = REPORTS_DIR / f"{video_id}.json"
    tmp_file = REPORTS_DIR / f"{video_id}.json.tmp"

    try:
        # Write to temporary file first
        tmp_file.write_text(json.dumps(report_data, indent=2, default=str), encoding="utf-8")
        # Atomic rename
        tmp_file.replace(report_file)
        _log_operation("report_saved", "success", video_id=video_id)
    except Exception as e:
        _log_operation("report_save_failed", "failed", video_id=video_id, error=str(e))
        raise


def has_report(video_id: str) -> bool:
    """Check if fact-checking report exists for a video.

    Returns False if reports directory is missing.
    """
    if not REPORTS_DIR.exists():
        _log_operation(
            "reports_dir_missing",
            "warning",
            message="storage/reports/videos/ directory does not exist",
        )
        return False
    return (REPORTS_DIR / f"{video_id}.json").exists()


def load_summary(video_id: str) -> dict[str, Any] | None:
    """Load summary from storage/summaries/{video_id}.json.

    Returns None if missing.
    Raises ValueError if JSON is invalid.
    """
    summary_file = SUMMARIES_DIR / f"{video_id}.json"

    if not summary_file.exists():
        return None

    try:
        content = summary_file.read_text(encoding="utf-8")
        summary: dict[str, Any] = json.loads(content)
        return summary
    except json.JSONDecodeError as e:
        _log_operation(
            "summary_load_failed", "failed", video_id=video_id, error=f"Invalid JSON: {str(e)}"
        )
        raise ValueError(f"Invalid JSON in summary file for {video_id}: {str(e)}") from e
    except Exception as e:
        _log_operation("summary_load_failed", "failed", video_id=video_id, error=str(e))
        raise


def list_pending_videos() -> list[str]:
    """List video IDs with summaries but no reports.

    Scans storage/summaries/ and returns video_ids that don't have
    corresponding reports in storage/reports/videos/.
    """
    ensure_summaries_dir()

    if not SUMMARIES_DIR.exists():
        return []

    pending = []
    for summary_file in SUMMARIES_DIR.glob("*.json"):
        video_id = summary_file.stem  # filename without .json
        if not has_report(video_id):
            pending.append(video_id)

    return sorted(pending)


# Monthly Digest Module (Module 4) storage functions

DIGESTS_DIR = STORAGE_DIR / "reports" / "monthly"


def list_reports_for_month(year: int, month: int) -> list[Path]:
    """List all reports for a given month based on publication_date.

    Scans storage/reports/videos/ for JSON files and filters by
    summary.metadata.publication_date month.

    Args:
        year: 4-digit year
        month: Month number (1-12)

    Returns:
        List of report file paths matching the month
    """
    if not REPORTS_DIR.exists():
        return []

    reports = []
    month_str = f"{year:04d}-{month:02d}"

    for report_file in REPORTS_DIR.glob("*.json"):
        try:
            content = json.loads(report_file.read_text(encoding="utf-8"))
            pub_date = content.get("summary", {}).get("metadata", {}).get("publication_date", "")
            if pub_date.startswith(month_str):
                reports.append(report_file)
        except (OSError, json.JSONDecodeError):
            continue

    return sorted(reports)


def save_monthly_digest(year: int, month: int, digest_data: dict[str, Any]) -> Path:
    """Save monthly digest to file using atomic .tmp pattern.

    Args:
        year: 4-digit year
        month: Month number (1-12)
        digest_data: Digest dictionary to save

    Returns:
        Path to saved digest file

    Raises:
        Exception: If write fails
    """
    DIGESTS_DIR.mkdir(parents=True, exist_ok=True)

    digest_file = DIGESTS_DIR / f"{year:04d}-{month:02d}.json"
    tmp_file = DIGESTS_DIR / f"{year:04d}-{month:02d}.json.tmp"

    try:
        tmp_file.write_text(json.dumps(digest_data, indent=2, default=str), encoding="utf-8")
        tmp_file.replace(digest_file)
        month_str = f"{year:04d}-{month:02d}"
        _log_operation("digest_saved", "success", month=month_str, path=str(digest_file))
        return digest_file
    except Exception as e:
        month_str = f"{year:04d}-{month:02d}"
        _log_operation("digest_save_failed", "failed", month=month_str, error=str(e))
        raise


# Read helpers for the API layer (Module 5)


def list_report_ids() -> list[str]:
    """List video IDs that have a stored report, sorted.

    Returns an empty list if storage/reports/videos/ is missing.
    """
    if not REPORTS_DIR.exists():
        return []
    return sorted(p.stem for p in REPORTS_DIR.glob("*.json"))


def load_report(video_id: str) -> dict[str, Any] | None:
    """Load a per-video report from storage/reports/videos/{video_id}.json.

    Returns None if missing.
    Raises ValueError if JSON is invalid.
    """
    report_file = REPORTS_DIR / f"{video_id}.json"
    if not report_file.exists():
        return None
    try:
        report: dict[str, Any] = json.loads(report_file.read_text(encoding="utf-8"))
        return report
    except json.JSONDecodeError as e:
        _log_operation(
            "report_load_failed", "failed", video_id=video_id, error=f"Invalid JSON: {e}"
        )
        raise StoredFileError(f"Invalid JSON in report file for {video_id}: {e}") from e


def list_digest_months() -> list[str]:
    """List months (YYYY-MM) that have a stored monthly digest, sorted.

    Returns an empty list if storage/reports/monthly/ is missing.
    """
    if not DIGESTS_DIR.exists():
        return []
    return sorted(p.stem for p in DIGESTS_DIR.glob("*.json"))


def load_monthly_digest(year: int, month: int) -> dict[str, Any] | None:
    """Load a monthly digest from storage/reports/monthly/YYYY-MM.json.

    Returns None if missing.
    Raises ValueError if JSON is invalid.
    """
    month_str = f"{year:04d}-{month:02d}"
    digest_file = DIGESTS_DIR / f"{month_str}.json"
    if not digest_file.exists():
        return None
    try:
        digest: dict[str, Any] = json.loads(digest_file.read_text(encoding="utf-8"))
        return digest
    except json.JSONDecodeError as e:
        _log_operation("digest_load_failed", "failed", month=month_str, error=f"Invalid JSON: {e}")
        raise StoredFileError(f"Invalid JSON in digest file for {month_str}: {e}") from e


def index_file_path() -> Path:
    """Location of the derived API index (inside storage/, gitignored)."""
    return STORAGE_DIR / ".finfolio-api-index.sqlite"


def prepare_index_build(tmp: Path) -> None:
    """Create the index directory and clear any leftover temp file from an interrupted build."""
    tmp.parent.mkdir(parents=True, exist_ok=True)
    tmp.unlink(missing_ok=True)


def discard_index_build(tmp: Path) -> None:
    """Remove a temp index file after a failed build."""
    tmp.unlink(missing_ok=True)


def publish_index_build(tmp: Path, live: Path) -> None:
    """Atomically replace the live index with a finished build."""
    os.replace(tmp, live)
