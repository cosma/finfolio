"""Integration tests for summarizer CLI command."""

from pathlib import Path
from unittest.mock import patch

import pytest
from click.testing import CliRunner

from finfolio.cli import main
from finfolio.summarizer_schema import Claim, ClaimType, SummaryMetadata, SummaryOutput


@pytest.fixture
def cli_runner():
    """Create a Click CLI runner."""
    return CliRunner()


@pytest.fixture
def mock_summary_output():
    """Create a mock SummaryOutput."""
    return SummaryOutput(
        summary="The advisor discussed semiconductor companies, energy stocks, and fintech investments. "
        "Key points include Apple's iPhone 15 Pro release and Exxon's acquisition of Pioneer Natural Resources. "
        "Recommended monitoring AI chip demand and fintech consolidation trends.",
        claims=[
            Claim(
                type=ClaimType.DATE,
                claim="Apple released iPhone 15 Pro in September 2023",
                quote="Apple released the iPhone 15 Pro in September 2023",
                confidence_score=0.98,
            ),
            Claim(
                type=ClaimType.COMPANY_FACT,
                claim="Exxon Mobil announced $50 billion acquisition of Pioneer Natural Resources",
                quote="announced a $50 billion acquisition of Pioneer Natural Resources",
                confidence_score=0.95,
            ),
        ],
        metadata=SummaryMetadata(
            transcript_tokens=500,
            model="claude-haiku-4-5-20251001",
            temperature=0.3,
            timestamp="2026-09-25T14:30:00Z",
            cost_usd=0.034,
            input_tokens=500,
            output_tokens=120,
        ),
    )


def test_summarize_help(cli_runner):
    """Test that summarize command shows help."""
    result = cli_runner.invoke(main, ["summarize", "--help"])
    assert result.exit_code == 0
    assert "Summarize all unsummarized transcripts" in result.output
    assert "--batch-size" in result.output


def test_summarize_requires_api_key(cli_runner, tmp_path, monkeypatch):
    """Test that summarize requires ANTHROPIC_API_KEY."""
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.setenv("FINFOLIO_LLM_MODEL", "claude-haiku-4-5-20251001")

    with cli_runner.isolated_filesystem():
        Path("storage/transcripts").mkdir(parents=True)
        Path("storage/summaries").mkdir(parents=True)

        # Create a test transcript
        Path("storage/transcripts/test-video.txt").write_text("Test transcript content here.")

        result = cli_runner.invoke(main, ["summarize"])
        assert result.exit_code == 1
        assert "ANTHROPIC_API_KEY" in result.output


def test_summarize_missing_transcripts_directory(cli_runner, monkeypatch):
    """Test behavior when transcripts directory doesn't exist."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")

    with cli_runner.isolated_filesystem():
        # Don't create transcripts directory
        result = cli_runner.invoke(main, ["summarize"])
        assert result.exit_code == 1
        assert "Transcripts directory" in result.output


@patch("finfolio.summarizer.process_transcript_safe")
def test_summarize_batch_processing(mock_process, cli_runner, mock_summary_output, monkeypatch):
    """Test batch processing of multiple transcripts."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    mock_process.return_value = mock_summary_output

    with cli_runner.isolated_filesystem():
        # Create test transcripts
        Path("storage/transcripts").mkdir(parents=True)
        Path("storage/summaries").mkdir(parents=True)

        Path("storage/transcripts/video-001.txt").write_text("First test transcript. " * 20)
        Path("storage/transcripts/video-002.txt").write_text("Second test transcript. " * 20)

        result = cli_runner.invoke(main, ["summarize", "--batch-size", "10"])
        assert result.exit_code == 0
        assert "summarization_complete" in result.output
        assert mock_process.call_count == 2


@patch("finfolio.summarizer.process_transcript_safe")
def test_summarize_skips_already_summarized(mock_process, cli_runner, monkeypatch):
    """Test that already-summarized transcripts are skipped."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    mock_process.return_value = None  # Simulate skipped

    with cli_runner.isolated_filesystem():
        Path("storage/transcripts").mkdir(parents=True)
        Path("storage/summaries").mkdir(parents=True)

        Path("storage/transcripts/existing.txt").write_text("Existing transcript. " * 20)

        result = cli_runner.invoke(main, ["summarize"])
        assert result.exit_code == 0
        # Should have skipped (returned None)
        assert mock_process.call_count == 1


@patch("finfolio.summarizer.process_transcript_safe")
def test_summarize_handles_errors(mock_process, cli_runner, monkeypatch):
    """Test error handling during summarization."""
    from finfolio.summarizer import LLMAPIError

    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    mock_process.side_effect = LLMAPIError("API call failed")

    with cli_runner.isolated_filesystem():
        Path("storage/transcripts").mkdir(parents=True)
        Path("storage/summaries").mkdir(parents=True)

        Path("storage/transcripts/error-test.txt").write_text("Test transcript. " * 20)

        result = cli_runner.invoke(main, ["summarize"])
        assert result.exit_code == 1
        assert "summarization_failed" in result.output or "transcript_error" in result.output
