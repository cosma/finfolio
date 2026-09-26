"""Unit tests for storage module."""

from datetime import UTC, datetime
from unittest.mock import patch

import pytest

from finfolio import storage


@pytest.mark.unit
class TestStorage:
    """Test storage operations."""

    def test_ensure_storage_dir_creates_directory(self, tmp_path):
        """Test that ensure_storage_dir creates transcripts directory."""
        storage_dir = tmp_path / "storage"
        transcripts_dir = storage_dir / "transcripts"

        with patch("finfolio.storage.STORAGE_DIR", storage_dir):
            with patch("finfolio.storage.TRANSCRIPTS_DIR", transcripts_dir):
                storage.ensure_storage_dir()
                assert transcripts_dir.exists()

    def test_save_transcript_writes_file(self, tmp_path):
        """Test that save_transcript writes transcript to disk."""
        storage_dir = tmp_path / "storage"
        transcripts_dir = storage_dir / "transcripts"
        transcripts_dir.mkdir(parents=True)

        with patch("finfolio.storage.STORAGE_DIR", storage_dir):
            with patch("finfolio.storage.TRANSCRIPTS_DIR", transcripts_dir):
                video_id = "test_video_123"
                text = "Test transcript content"

                storage.save_transcript(video_id, text)

                transcript_file = transcripts_dir / f"{video_id}.txt"
                assert transcript_file.exists()
                assert transcript_file.read_text() == text

    def test_has_transcript_returns_true_for_existing(self, tmp_path):
        """Test that has_transcript returns True for existing files."""
        storage_dir = tmp_path / "storage"
        transcripts_dir = storage_dir / "transcripts"
        transcripts_dir.mkdir(parents=True)

        with patch("finfolio.storage.STORAGE_DIR", storage_dir):
            with patch("finfolio.storage.TRANSCRIPTS_DIR", transcripts_dir):
                video_id = "existing_video"
                (transcripts_dir / f"{video_id}.txt").write_text("content")

                assert storage.has_transcript(video_id) is True

    def test_has_transcript_returns_false_for_missing(self, tmp_path):
        """Test that has_transcript returns False for missing files."""
        storage_dir = tmp_path / "storage"
        transcripts_dir = storage_dir / "transcripts"
        transcripts_dir.mkdir(parents=True)

        with patch("finfolio.storage.STORAGE_DIR", storage_dir):
            with patch("finfolio.storage.TRANSCRIPTS_DIR", transcripts_dir):
                video_id = "missing_video"
                assert storage.has_transcript(video_id) is False

    def test_acquire_lock_creates_lock_file(self, tmp_path):
        """Test that acquire_lock creates lock file."""
        storage_dir = tmp_path / "storage"
        storage_dir.mkdir()
        lock_file = storage_dir / ".finfolio.lock"

        with patch("finfolio.storage.STORAGE_DIR", storage_dir):
            with patch("finfolio.storage.LOCK_FILE", lock_file):
                with patch("finfolio.storage.TRANSCRIPTS_DIR", storage_dir / "transcripts"):
                    result = storage.acquire_lock()

                    assert result is True
                    assert lock_file.exists()

    def test_acquire_lock_returns_false_if_already_locked(self, tmp_path):
        """Test that acquire_lock returns False if already locked."""
        storage_dir = tmp_path / "storage"
        storage_dir.mkdir()
        lock_file = storage_dir / ".finfolio.lock"
        lock_file.touch()

        with patch("finfolio.storage.STORAGE_DIR", storage_dir):
            with patch("finfolio.storage.LOCK_FILE", lock_file):
                with patch("finfolio.storage.TRANSCRIPTS_DIR", storage_dir / "transcripts"):
                    result = storage.acquire_lock()

                    assert result is False

    def test_release_lock_deletes_lock_file(self, tmp_path):
        """Test that release_lock deletes lock file."""
        storage_dir = tmp_path / "storage"
        storage_dir.mkdir()
        lock_file = storage_dir / ".finfolio.lock"
        lock_file.touch()

        with patch("finfolio.storage.STORAGE_DIR", storage_dir):
            with patch("finfolio.storage.LOCK_FILE", lock_file):
                storage.release_lock()

                assert not lock_file.exists()

    def test_save_and_load_state(self, tmp_path):
        """Test state save and load round-trip."""
        storage_dir = tmp_path / "storage"
        storage_dir.mkdir()
        state_file = storage_dir / ".finfolio-state.json"

        with patch("finfolio.storage.STORAGE_DIR", storage_dir):
            with patch("finfolio.storage.STATE_FILE", state_file):
                with patch("finfolio.storage.TRANSCRIPTS_DIR", storage_dir / "transcripts"):
                    test_state = {"channels": {"UCxxxxx": {"last_fetch": "2026-09-24T10:00:00Z"}}}

                    storage.save_state(test_state)
                    loaded_state = storage.load_state()

                    assert loaded_state == test_state

    def test_load_state_returns_empty_dict_if_missing(self, tmp_path):
        """Test that load_state returns {} if state file doesn't exist."""
        storage_dir = tmp_path / "storage"
        state_file = storage_dir / ".finfolio-state.json"

        with patch("finfolio.storage.STATE_FILE", state_file):
            loaded_state = storage.load_state()

            assert loaded_state == {}


@pytest.mark.unit
class TestChannelState:
    """Test channel state management."""

    def test_update_and_get_channel_last_fetch(self, tmp_path):
        """Test updating and retrieving channel last fetch timestamp."""
        storage_dir = tmp_path / "storage"
        storage_dir.mkdir()
        state_file = storage_dir / ".finfolio-state.json"

        with patch("finfolio.storage.STORAGE_DIR", storage_dir):
            with patch("finfolio.storage.STATE_FILE", state_file):
                with patch("finfolio.storage.TRANSCRIPTS_DIR", storage_dir / "transcripts"):
                    channel_id = "UCxxxxx"
                    now = datetime.now(UTC)

                    storage.update_channel_last_fetch(channel_id, now)
                    retrieved = storage.get_channel_last_fetch(channel_id)

                    assert retrieved is not None
                    assert abs((retrieved - now).total_seconds()) < 1


@pytest.mark.unit
class TestFactCheckingReportStorage:
    """Test fact-checking report storage functions (Module 3)."""

    def test_has_report_missing_returns_false(self, tmp_path):
        """Test has_report returns False when report doesn't exist."""
        reports_dir = tmp_path / "reports" / "videos"

        with patch("finfolio.storage.REPORTS_DIR", reports_dir):
            result = storage.has_report("nonexistent_video")
            assert result is False

    def test_has_report_missing_dir_returns_false(self, tmp_path):
        """Test has_report returns False when reports directory is missing."""
        reports_dir = tmp_path / "reports" / "videos"
        # Don't create the directory

        with patch("finfolio.storage.REPORTS_DIR", reports_dir):
            result = storage.has_report("test_video")
            assert result is False

    def test_has_report_existing_returns_true(self, tmp_path):
        """Test has_report returns True when report exists."""
        reports_dir = tmp_path / "reports" / "videos"
        reports_dir.mkdir(parents=True, exist_ok=True)
        video_id = "test_video_001"
        report_path = reports_dir / f"{video_id}.json"
        report_path.write_text("{}")

        with patch("finfolio.storage.REPORTS_DIR", reports_dir):
            result = storage.has_report(video_id)
            assert result is True

    def test_save_report_creates_directory(self, tmp_path):
        """Test save_report creates storage directory if missing."""
        reports_dir = tmp_path / "reports" / "videos"
        video_id = "test_video_002"

        report_data = {
            "video_id": video_id,
            "title": "Test Video",
            "channel_name": "Test Channel",
            "channel_url": "https://example.com",
            "source_url": "https://youtube.com/watch?v=test",
            "transcript_source": "YouTube API",
            "fact_checked_at": "2026-09-25T15:30:00Z",
            "fact_check_duration_seconds": 10.0,
            "search_provider": "Tavily",
            "llm_model": "claude-haiku-4-5-20251001",
            "cost": {"search_usd": 0.0, "llm_usd": 0.0, "total_usd": 0.0},
            "summary": {},
            "verdicts": [],
            "claim_count": 0,
            "verdict_count": 0,
            "verdict_breakdown": {
                "True": 0,
                "Partially supported/overstated": 0,
                "Unverified": 0,
                "False": 0,
            },
            "disclaimer": "FinFolio reports facts and their accuracy. This is not financial advice.",
        }

        with patch("finfolio.storage.REPORTS_DIR", reports_dir):
            storage.save_report(video_id, report_data)
            report_path = reports_dir / f"{video_id}.json"
            assert report_path.exists()

    def test_save_report_validates_against_schema(self, tmp_path):
        """Test save_report validates report_data against ReportModel."""
        reports_dir = tmp_path / "reports" / "videos"
        video_id = "test_video_003"

        invalid_report_data = {
            "video_id": video_id,
            "title": "Test",
            # Missing required fields
        }

        with patch("finfolio.storage.REPORTS_DIR", reports_dir):
            with pytest.raises(Exception):  # Should raise validation error
                storage.save_report(video_id, invalid_report_data)

    def test_save_report_uses_atomic_write(self, tmp_path):
        """Test save_report uses atomic .tmp pattern."""
        reports_dir = tmp_path / "reports" / "videos"
        video_id = "test_video_004"

        report_data = {
            "video_id": video_id,
            "title": "Test Video",
            "channel_name": "Test Channel",
            "channel_url": "https://example.com",
            "source_url": "https://youtube.com/watch?v=test",
            "transcript_source": "YouTube API",
            "fact_checked_at": "2026-09-25T15:30:00Z",
            "fact_check_duration_seconds": 10.0,
            "search_provider": "Tavily",
            "llm_model": "claude-haiku-4-5-20251001",
            "cost": {"search_usd": 0.0, "llm_usd": 0.0, "total_usd": 0.0},
            "summary": {},
            "verdicts": [],
            "claim_count": 0,
            "verdict_count": 0,
            "verdict_breakdown": {
                "True": 0,
                "Partially supported/overstated": 0,
                "Unverified": 0,
                "False": 0,
            },
            "disclaimer": "FinFolio reports facts and their accuracy. This is not financial advice.",
        }

        with patch("finfolio.storage.REPORTS_DIR", reports_dir):
            storage.save_report(video_id, report_data)

            report_path = reports_dir / f"{video_id}.json"
            tmp_path_check = reports_dir / f"{video_id}.json.tmp"

            # Final file should exist
            assert report_path.exists()
            # No .tmp files should remain
            assert not tmp_path_check.exists()


@pytest.mark.unit
class TestSummaryLoading:
    """Test summary loading functions."""

    def test_load_summary_returns_none_when_missing(self, tmp_path):
        """Test load_summary returns None when summary doesn't exist."""
        summaries_dir = tmp_path / "summaries"

        with patch("finfolio.storage.SUMMARIES_DIR", summaries_dir):
            result = storage.load_summary("nonexistent_video")
            assert result is None

    def test_load_summary_returns_data_when_exists(self, tmp_path):
        """Test load_summary returns data when summary exists."""
        video_id = "test_video_005"
        summary_data = {
            "video_id": video_id,
            "title": "Test Summary",
            "claims": [],
        }

        summaries_dir = tmp_path / "summaries"
        summaries_dir.mkdir(parents=True, exist_ok=True)
        summary_path = summaries_dir / f"{video_id}.json"
        import json

        summary_path.write_text(json.dumps(summary_data))

        with patch("finfolio.storage.SUMMARIES_DIR", summaries_dir):
            result = storage.load_summary(video_id)
            assert result == summary_data

    def test_load_summary_raises_on_invalid_json(self, tmp_path):
        """Test load_summary raises ValueError for invalid JSON."""
        video_id = "test_video_006"
        summaries_dir = tmp_path / "summaries"
        summaries_dir.mkdir(parents=True, exist_ok=True)
        summary_path = summaries_dir / f"{video_id}.json"
        summary_path.write_text("{ invalid json }")

        with patch("finfolio.storage.SUMMARIES_DIR", summaries_dir):
            with pytest.raises(ValueError):
                storage.load_summary(video_id)


@pytest.mark.unit
class TestListPendingVideos:
    """Test list_pending_videos function."""

    def test_list_pending_videos_empty(self, tmp_path):
        """Test list_pending_videos returns empty list when no summaries exist."""
        summaries_dir = tmp_path / "summaries"
        reports_dir = tmp_path / "reports" / "videos"

        with patch("finfolio.storage.SUMMARIES_DIR", summaries_dir):
            with patch("finfolio.storage.REPORTS_DIR", reports_dir):
                result = storage.list_pending_videos()
                assert result == []

    def test_list_pending_videos_returns_without_reports(self, tmp_path):
        """Test list_pending_videos returns videos with summaries but no reports."""
        summaries_dir = tmp_path / "summaries"
        reports_dir = tmp_path / "reports" / "videos"

        # Create summaries
        summaries_dir.mkdir(parents=True, exist_ok=True)
        (summaries_dir / "video_001.json").write_text('{"video_id": "video_001"}')
        (summaries_dir / "video_002.json").write_text('{"video_id": "video_002"}')
        (summaries_dir / "video_003.json").write_text('{"video_id": "video_003"}')

        # Create report for only video_001
        reports_dir.mkdir(parents=True, exist_ok=True)
        (reports_dir / "video_001.json").write_text("{}")

        with patch("finfolio.storage.SUMMARIES_DIR", summaries_dir):
            with patch("finfolio.storage.REPORTS_DIR", reports_dir):
                result = storage.list_pending_videos()
                assert set(result) == {"video_002", "video_003"}

    def test_list_pending_videos_ignores_non_json_files(self, tmp_path):
        """Test list_pending_videos ignores non-JSON files in summaries."""
        summaries_dir = tmp_path / "summaries"
        reports_dir = tmp_path / "reports" / "videos"

        summaries_dir.mkdir(parents=True, exist_ok=True)
        (summaries_dir / "video_001.json").write_text('{"video_id": "video_001"}')
        (summaries_dir / "README.md").write_text("# Summaries")
        (summaries_dir / ".DS_Store").write_text("mac os")

        reports_dir.mkdir(parents=True, exist_ok=True)

        with patch("finfolio.storage.SUMMARIES_DIR", summaries_dir):
            with patch("finfolio.storage.REPORTS_DIR", reports_dir):
                result = storage.list_pending_videos()
                assert result == ["video_001"]

    def test_list_pending_videos_sorted(self, tmp_path):
        """Test list_pending_videos returns results in sorted order."""
        summaries_dir = tmp_path / "summaries"
        reports_dir = tmp_path / "reports" / "videos"

        # Create summaries in random order
        summaries_dir.mkdir(parents=True, exist_ok=True)
        (summaries_dir / "zulu.json").write_text('{"video_id": "zulu"}')
        (summaries_dir / "alpha.json").write_text('{"video_id": "alpha"}')
        (summaries_dir / "bravo.json").write_text('{"video_id": "bravo"}')

        reports_dir.mkdir(parents=True, exist_ok=True)

        with patch("finfolio.storage.SUMMARIES_DIR", summaries_dir):
            with patch("finfolio.storage.REPORTS_DIR", reports_dir):
                result = storage.list_pending_videos()
                assert result == ["alpha", "bravo", "zulu"]
