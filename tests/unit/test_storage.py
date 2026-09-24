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
                    test_state = {
                        "channels": {
                            "UCxxxxx": {"last_fetch": "2026-09-24T10:00:00Z"}
                        }
                    }

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
