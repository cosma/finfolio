"""Integration tests for summary storage operations."""

import json

import pytest

from finfolio import storage


@pytest.fixture
def clean_summaries_dir(tmp_path, monkeypatch):
    """Create a temporary summaries directory for testing."""
    summaries_dir = tmp_path / "summaries"
    summaries_dir.mkdir()
    monkeypatch.setattr(storage, "SUMMARIES_DIR", summaries_dir)
    return summaries_dir


def test_ensure_summaries_dir_creates_directory(tmp_path, monkeypatch):
    """Test that ensure_summaries_dir creates directory if missing."""
    summaries_dir = tmp_path / "summaries"
    monkeypatch.setattr(storage, "SUMMARIES_DIR", summaries_dir)

    assert not summaries_dir.exists()
    storage.ensure_summaries_dir()
    assert summaries_dir.exists()


def test_has_summary_returns_false_when_missing(clean_summaries_dir):
    """Test has_summary returns False when summary doesn't exist."""
    assert not storage.has_summary("nonexistent-video")


def test_has_summary_returns_true_when_exists(clean_summaries_dir):
    """Test has_summary returns True when summary exists."""
    video_id = "test-video-1"
    summary_file = clean_summaries_dir / f"{video_id}.json"
    summary_file.write_text(json.dumps({"summary": "test"}))

    assert storage.has_summary(video_id)


def test_save_summary_creates_file(clean_summaries_dir):
    """Test save_summary creates JSON file atomically."""
    video_id = "test-video-1"
    summary_data = {"summary": "Test summary", "claims": []}

    storage.save_summary(video_id, summary_data)

    summary_file = clean_summaries_dir / f"{video_id}.json"
    assert summary_file.exists()

    # Verify content
    saved_data = json.loads(summary_file.read_text())
    assert saved_data == summary_data


def test_save_summary_is_atomic(clean_summaries_dir):
    """Test save_summary uses atomic .tmp pattern."""
    video_id = "test-video-1"
    summary_data = {"summary": "Test summary"}

    storage.save_summary(video_id, summary_data)

    # Verify no .tmp file left behind
    tmp_file = clean_summaries_dir / f"{video_id}.json.tmp"
    assert not tmp_file.exists()


def test_get_summaries_dir_returns_path(clean_summaries_dir):
    """Test get_summaries_dir returns correct path."""
    result = storage.get_summaries_dir()
    assert result == clean_summaries_dir
