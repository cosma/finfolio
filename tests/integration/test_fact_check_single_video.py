"""Integration test for single-video fact-checking (US1).

Tests the full fact-checking pipeline:
- Load summary
- Extract claims
- Perform searches
- Assign verdicts
- Generate and save report
"""

import json
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from finfolio.config import Config
from finfolio.fact_checker import FactChecker


@pytest.mark.integration
class TestFactCheckSingleVideo:
    """Integration tests for fact-checking a single video."""

    @pytest.fixture
    def temp_storage(self):
        """Create temporary storage directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage_path = Path(tmpdir)
            (storage_path / "summaries").mkdir(parents=True)
            (storage_path / "reports" / "videos").mkdir(parents=True)
            yield storage_path

    @pytest.fixture
    def mock_config(self):
        """Create mock config for testing."""
        config = MagicMock(spec=Config)
        config.llm_model = "claude-haiku-4-5-20251001"
        config.tavily_api_key = "test-key"
        config.anthropic_api_key = "test-key"
        config.search_timeout_seconds = 10.0
        config.log_level = "INFO"
        return config

    @pytest.fixture
    def fixture_summary(self):
        """Create fixture summary with 3 claims."""
        return {
            "video_id": "test_vid_001",
            "title": "Finance Discussion",
            "channel_name": "Finance Channel",
            "channel_url": "https://youtube.com/@FinanceChannel",
            "source_url": "https://youtube.com/watch?v=test_vid_001",
            "transcript_source": "YouTube API",
            "summary": "Video about finance",
            "claims": [
                {
                    "id": "claim_001",
                    "text": "Apple stock price is $195.42",
                    "quote": "Apple stock was at one ninety five forty two",
                    "type": "number",
                    "confidence": 0.92,
                    "timestamp": "12:34",
                    "is_opinion": False,
                    "is_forecast": False,
                },
                {
                    "id": "claim_002",
                    "text": "Tesla will double by year end",
                    "quote": "Tesla will double",
                    "type": "other",
                    "confidence": 0.5,
                    "timestamp": "05:20",
                    "is_opinion": False,
                    "is_forecast": True,
                },
                {
                    "id": "claim_003",
                    "text": "Bitcoin is a scam",
                    "quote": "Bitcoin is scam",
                    "type": "other",
                    "confidence": 0.3,
                    "timestamp": "08:15",
                    "is_opinion": True,
                    "is_forecast": False,
                },
            ],
        }

    def test_fact_check_single_video_end_to_end(self, mock_config, temp_storage, fixture_summary):
        """Test complete fact-checking pipeline for single video."""

        video_id = "test_vid_001"

        # Save fixture summary to storage
        summary_path = temp_storage / "summaries" / f"{video_id}.json"
        summary_path.write_text(json.dumps(fixture_summary))

        # Create fact checker with mocked LLM
        with patch.object(FactChecker, "_get_llm") as mock_get_llm:
            mock_llm = MagicMock()
            mock_get_llm.return_value = mock_llm

            # Mock LLM responses for each claim
            mock_responses = [
                MagicMock(
                    content='{"verdict": "True", "note": "Verified against finance data", "source_url": "https://finance.example.com", "source_title": "Finance Source", "source_date": "2026-09-25"}'
                ),
                # claim_002 is forecast, will be skipped
                # claim_003 is opinion, will be skipped
            ]
            mock_llm.invoke.side_effect = mock_responses

            checker = FactChecker(mock_config)

            # Mock storage functions
            with patch("finfolio.storage.has_report", return_value=False):
                with patch("finfolio.storage.load_summary", return_value=fixture_summary):
                    with patch("finfolio.storage.save_report") as mock_save:
                        with patch("finfolio.storage.SUMMARIES_DIR", temp_storage / "summaries"):
                            with patch(
                                "finfolio.storage.REPORTS_DIR", temp_storage / "reports" / "videos"
                            ):
                                # Run fact-checking
                                checker.run_fact_check_single_video(video_id)

                                # Verify report was saved
                                assert mock_save.called
                                saved_report = mock_save.call_args[0][1]

                                # Verify report structure
                                assert saved_report["video_id"] == video_id
                                assert saved_report["title"] == "Finance Discussion"
                                assert (
                                    len(saved_report["verdicts"]) == 1
                                )  # Only claim_001 (others skipped)
                                assert saved_report["verdict_count"] == 1
                                assert saved_report["claim_count"] == 3

    def test_fact_check_idempotency(self, mock_config, temp_storage, fixture_summary):
        """Test that running fact-check twice produces same results."""
        video_id = "test_vid_001"

        with patch.object(FactChecker, "_get_llm"):
            checker = FactChecker(mock_config)

            # First run: report doesn't exist
            with patch("finfolio.storage.has_report", return_value=False):
                with patch("finfolio.storage.load_summary", return_value=fixture_summary):
                    with patch("finfolio.storage.save_report") as mock_save_1:
                        with patch("finfolio.storage.SUMMARIES_DIR", temp_storage / "summaries"):
                            with patch(
                                "finfolio.storage.REPORTS_DIR", temp_storage / "reports" / "videos"
                            ):
                                mock_llm = MagicMock()
                                mock_response = MagicMock(
                                    content='{"verdict": "True", "note": "Verified", "source_url": "https://example.com", "source_title": "Source", "source_date": "2026-09-25"}'
                                )
                                mock_llm.invoke.return_value = mock_response

                                with patch.object(checker, "llm", mock_llm):
                                    checker.run_fact_check_single_video(video_id)
                                    assert mock_save_1.called

            # Second run: report exists, should skip
            with patch("finfolio.storage.has_report", return_value=True):
                with patch("finfolio.storage.save_report") as mock_save_2:
                    checker.run_fact_check_single_video(video_id)
                    # save_report should NOT be called on second run
                    assert not mock_save_2.called

    def test_fact_check_skips_opinions_and_forecasts(self, mock_config):
        """Test that opinion and forecast claims are skipped."""
        summary = {
            "video_id": "test_vid",
            "title": "Test",
            "channel_name": "Test",
            "channel_url": "https://example.com",
            "source_url": "https://youtube.com/watch?v=test",
            "transcript_source": "YouTube API",
            "claims": [
                {
                    "id": "factual_001",
                    "text": "Factual claim",
                    "quote": "factual",
                    "type": "number",
                    "confidence": 0.9,
                    "timestamp": "12:34",
                    "is_opinion": False,
                    "is_forecast": False,
                },
                {
                    "id": "opinion_001",
                    "text": "Opinion claim",
                    "quote": "opinion",
                    "type": "other",
                    "confidence": 0.5,
                    "timestamp": "05:20",
                    "is_opinion": True,
                    "is_forecast": False,
                },
                {
                    "id": "forecast_001",
                    "text": "Forecast claim",
                    "quote": "forecast",
                    "type": "other",
                    "confidence": 0.5,
                    "timestamp": "08:15",
                    "is_opinion": False,
                    "is_forecast": True,
                },
            ],
        }

        with patch.object(FactChecker, "_get_llm"):
            checker = FactChecker(mock_config)

            with patch("finfolio.storage.has_report", return_value=False):
                with patch("finfolio.storage.load_summary", return_value=summary):
                    with patch("finfolio.storage.save_report") as mock_save:
                        with patch("finfolio.storage.SUMMARIES_DIR", Path("/tmp/summaries")):
                            with patch("finfolio.storage.REPORTS_DIR", Path("/tmp/reports")):
                                mock_llm = MagicMock()
                                mock_response = MagicMock(
                                    content='{"verdict": "True", "note": "Test", "source_url": "https://example.com", "source_title": "Source", "source_date": "2026-09-25"}'
                                )
                                mock_llm.invoke.return_value = mock_response

                                with patch.object(checker, "llm", mock_llm):
                                    checker.run_fact_check_single_video("test_vid")

                                    # Verify only factual claim was processed
                                    saved_report = mock_save.call_args[0][1]
                                    assert saved_report["verdict_count"] == 1
                                    assert saved_report["verdicts"][0]["claim_id"] == "factual_001"

    def test_fact_check_handles_missing_summary(self, mock_config):
        """Test error handling when summary is missing."""
        video_id = "missing_vid"

        with patch.object(FactChecker, "_get_llm"):
            checker = FactChecker(mock_config)

            with patch("finfolio.storage.has_report", return_value=False):
                with patch("finfolio.storage.load_summary", return_value=None):
                    with pytest.raises(ValueError) as exc_info:
                        checker.run_fact_check_single_video(video_id)
                    assert "Summary not found" in str(exc_info.value)

    def test_fact_check_handles_invalid_claims(self, mock_config):
        """Test error handling when summary has invalid claims."""
        summary = {
            "video_id": "test_vid",
            "title": "Test",
            "channel_name": "Test",
            "channel_url": "https://example.com",
            "source_url": "https://youtube.com/watch?v=test",
            "transcript_source": "YouTube API",
            "claims": [
                {
                    # Missing required fields
                    "id": "bad_claim",
                    "type": "number",
                }
            ],
        }

        with patch.object(FactChecker, "_get_llm"):
            checker = FactChecker(mock_config)

            with patch("finfolio.storage.has_report", return_value=False):
                with patch("finfolio.storage.load_summary", return_value=summary):
                    with pytest.raises(ValueError) as exc_info:
                        checker.run_fact_check_single_video("test_vid")
                    assert "No valid claims" in str(exc_info.value)
