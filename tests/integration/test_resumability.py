"""Integration tests for resumability and partial failure recovery (US2)."""

import json
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from finfolio.config import Config
from finfolio.fact_checker import FactChecker, extract_completed_claim_ids


@pytest.fixture(autouse=True)
def tavily_key(monkeypatch):
    """FactChecker builds a Tavily client at init. Give it a dummy key so the tests do not depend on .env."""
    monkeypatch.setenv("TAVILY_API_KEY", "test-dummy-key")


@pytest.mark.integration
class TestResumability:
    """Test resumability: partial failure recovery."""

    @pytest.fixture
    def fixture_summary(self):
        """Create fixture summary with 4 claims."""
        return {
            "video_id": "test_vid_resumable",
            "title": "Test Video",
            "channel_name": "Test Channel",
            "channel_url": "https://youtube.com/@TestChannel",
            "source_url": "https://youtube.com/watch?v=test_vid",
            "transcript_source": "YouTube API",
            "claims": [
                {
                    "id": "claim_001",
                    "text": "Claim 1",
                    "quote": "claim",
                    "type": "number",
                    "confidence": 0.9,
                    "timestamp": "12:34",
                    "is_opinion": False,
                    "is_forecast": False,
                },
                {
                    "id": "claim_002",
                    "text": "Claim 2",
                    "quote": "claim",
                    "type": "number",
                    "confidence": 0.9,
                    "timestamp": "05:20",
                    "is_opinion": False,
                    "is_forecast": False,
                },
                {
                    "id": "claim_003",
                    "text": "Claim 3",
                    "quote": "claim",
                    "type": "number",
                    "confidence": 0.9,
                    "timestamp": "08:15",
                    "is_opinion": False,
                    "is_forecast": False,
                },
                {
                    "id": "claim_004",
                    "text": "Claim 4",
                    "quote": "claim",
                    "type": "number",
                    "confidence": 0.9,
                    "timestamp": "15:45",
                    "is_opinion": False,
                    "is_forecast": False,
                },
            ],
        }

    def test_extract_completed_claim_ids_empty(self):
        """Test extract_completed_claim_ids with no report."""
        result = extract_completed_claim_ids(None)
        assert result == set()

    def test_extract_completed_claim_ids_with_verdicts(self):
        """Test extract_completed_claim_ids extracts IDs correctly."""
        report = {
            "verdicts": [
                {"claim_id": "claim_001", "verdict": "True"},
                {"claim_id": "claim_002", "verdict": "False"},
            ]
        }
        result = extract_completed_claim_ids(report)
        assert result == {"claim_001", "claim_002"}

    def test_partial_failure_then_resume(self):
        """Test resumability: partial failure leaves claims 1-2, retry gets 3-4."""
        video_id = "test_vid_resumable"

        with tempfile.TemporaryDirectory() as tmpdir:
            storage_path = Path(tmpdir)
            summaries_dir = storage_path / "summaries"
            reports_dir = storage_path / "reports" / "videos"
            summaries_dir.mkdir(parents=True)
            reports_dir.mkdir(parents=True)

            summary = self._create_fixture_summary()
            summary_path = summaries_dir / f"{video_id}.json"
            summary_path.write_text(json.dumps(summary))

            mock_config = MagicMock(spec=Config)
            mock_config.llm_model = "claude-haiku-4-5-20251001"

            with patch.object(FactChecker, "_get_llm"):
                checker = FactChecker(mock_config)

                # FIRST RUN: Process claims 1-2, fail on claim 3
                with patch("finfolio.storage.SUMMARIES_DIR", summaries_dir):
                    with patch("finfolio.storage.REPORTS_DIR", reports_dir):
                        mock_llm = MagicMock()
                        # First 2 verdicts succeed
                        success_responses = [
                            MagicMock(
                                content='{"verdict": "True", "note": "Verified", "source_url": "https://example.com", "source_title": "Source", "source_date": "2026-09-25"}'
                            ),
                            MagicMock(
                                content='{"verdict": "False", "note": "Not verified", "source_url": "https://example.com", "source_title": "Source", "source_date": "2026-09-25"}'
                            ),
                        ]
                        # Third fails with timeout
                        mock_llm.invoke.side_effect = [
                            success_responses[0],
                            success_responses[1],
                            Exception("Search timeout"),
                        ]

                        with patch.object(checker, "llm", mock_llm):
                            # First run: should handle the exception and save partial report
                            try:
                                checker.run_fact_check_single_video(video_id)
                            except Exception:
                                pass  # Expected to fail

                            # Verify partial report was saved
                            report_path = reports_dir / f"{video_id}.json"
                            assert report_path.exists()
                            partial_report = json.loads(report_path.read_text())
                            assert len(partial_report["verdicts"]) == 2

                # SECOND RUN: Resume from claim 3
                with patch("finfolio.storage.SUMMARIES_DIR", summaries_dir):
                    with patch("finfolio.storage.REPORTS_DIR", reports_dir):
                        mock_llm = MagicMock()
                        # Now claims 3-4 succeed
                        mock_llm.invoke.side_effect = [
                            MagicMock(
                                content='{"verdict": "Unverified", "note": "No sources", "source_url": null, "source_title": null, "source_date": null}'
                            ),
                            MagicMock(
                                content='{"verdict": "True", "note": "Verified", "source_url": "https://example.com", "source_title": "Source", "source_date": "2026-09-25"}'
                            ),
                        ]

                        with patch.object(checker, "llm", mock_llm):
                            # Second run: should skip claims 1-2, process 3-4
                            checker.run_fact_check_single_video(video_id)

                            # Verify final report has all 4 verdicts
                            report_path = reports_dir / f"{video_id}.json"
                            final_report = json.loads(report_path.read_text())
                            assert final_report["verdict_count"] == 4
                            verdict_ids = {v["claim_id"] for v in final_report["verdicts"]}
                            assert verdict_ids == {
                                "claim_001",
                                "claim_002",
                                "claim_003",
                                "claim_004",
                            }

    def test_resumability_skips_already_verified(self):
        """Test that resumability correctly skips already-verified claims."""
        video_id = "test_skip_verified"

        with tempfile.TemporaryDirectory() as tmpdir:
            storage_path = Path(tmpdir)
            summaries_dir = storage_path / "summaries"
            reports_dir = storage_path / "reports" / "videos"
            summaries_dir.mkdir(parents=True)
            reports_dir.mkdir(parents=True)

            summary = self._create_fixture_summary()
            summary["video_id"] = video_id
            summary_path = summaries_dir / f"{video_id}.json"
            summary_path.write_text(json.dumps(summary))

            # Create partial report with first 2 claims already verified
            partial_report = {
                "video_id": video_id,
                "title": "Test",
                "channel_name": "Test",
                "channel_url": "https://example.com",
                "source_url": "https://youtube.com/watch?v=test",
                "transcript_source": "YouTube API",
                "fact_checked_at": "2026-09-25T10:00:00Z",
                "fact_check_duration_seconds": 10.0,
                "search_provider": "Tavily",
                "llm_model": "claude-haiku-4-5-20251001",
                "cost": {"search_usd": 0.0, "llm_usd": 0.0, "total_usd": 0.0},
                "summary": summary,
                "verdicts": [
                    {
                        "claim_id": "claim_001",
                        "claim_text": "Claim 1",
                        "verdict": "True",
                        "note": "Already verified",
                        "source_url": "https://example.com",
                        "source_title": "Source",
                        "source_date": "2026-09-25",
                        "search_query": "query",
                        "fact_checked_at": "2026-09-25T10:00:00Z",
                        "llm_model": "claude-haiku-4-5-20251001",
                        "reasoning_cost": {"tokens_in": 100, "tokens_out": 50, "cost_usd": 0.0001},
                    },
                    {
                        "claim_id": "claim_002",
                        "claim_text": "Claim 2",
                        "verdict": "False",
                        "note": "Already verified",
                        "source_url": "https://example.com",
                        "source_title": "Source",
                        "source_date": "2026-09-25",
                        "search_query": "query",
                        "fact_checked_at": "2026-09-25T10:00:00Z",
                        "llm_model": "claude-haiku-4-5-20251001",
                        "reasoning_cost": {"tokens_in": 100, "tokens_out": 50, "cost_usd": 0.0001},
                    },
                ],
                "claim_count": 4,
                "verdict_count": 2,
                "verdict_breakdown": {
                    "True": 1,
                    "Partially supported": 0,
                    "Unverified": 0,
                    "False": 1,
                },
                "disclaimer": "FinFolio reports facts and their accuracy. This is not financial advice.",
            }

            report_path = reports_dir / f"{video_id}.json"
            report_path.write_text(json.dumps(partial_report))

            mock_config = MagicMock(spec=Config)
            mock_config.llm_model = "claude-haiku-4-5-20251001"

            with patch.object(FactChecker, "_get_llm"):
                checker = FactChecker(mock_config)

                with patch("finfolio.storage.SUMMARIES_DIR", summaries_dir):
                    with patch("finfolio.storage.REPORTS_DIR", reports_dir):
                        mock_llm = MagicMock()
                        # Should only be called twice (for claims 3-4, not 1-2)
                        mock_llm.invoke.side_effect = [
                            MagicMock(
                                content='{"verdict": "True", "note": "Verified", "source_url": "https://example.com", "source_title": "Source", "source_date": "2026-09-25"}'
                            ),
                            MagicMock(
                                content='{"verdict": "True", "note": "Verified", "source_url": "https://example.com", "source_title": "Source", "source_date": "2026-09-25"}'
                            ),
                        ]

                        with patch.object(checker, "llm", mock_llm):
                            checker.run_fact_check_single_video(video_id)

                            # LLM should have been called exactly 2 times (not 4)
                            assert mock_llm.invoke.call_count == 2

    def _create_fixture_summary(self):
        """Helper to create fixture summary."""
        return {
            "video_id": "test_vid",
            "title": "Test Video",
            "channel_name": "Test Channel",
            "channel_url": "https://youtube.com/@Test",
            "source_url": "https://youtube.com/watch?v=test",
            "transcript_source": "YouTube API",
            "claims": [
                {
                    "id": "claim_001",
                    "text": "Claim 1",
                    "quote": "claim",
                    "type": "number",
                    "confidence": 0.9,
                    "timestamp": "12:34",
                    "is_opinion": False,
                    "is_forecast": False,
                },
                {
                    "id": "claim_002",
                    "text": "Claim 2",
                    "quote": "claim",
                    "type": "number",
                    "confidence": 0.9,
                    "timestamp": "05:20",
                    "is_opinion": False,
                    "is_forecast": False,
                },
                {
                    "id": "claim_003",
                    "text": "Claim 3",
                    "quote": "claim",
                    "type": "number",
                    "confidence": 0.9,
                    "timestamp": "08:15",
                    "is_opinion": False,
                    "is_forecast": False,
                },
                {
                    "id": "claim_004",
                    "text": "Claim 4",
                    "quote": "claim",
                    "type": "number",
                    "confidence": 0.9,
                    "timestamp": "15:45",
                    "is_opinion": False,
                    "is_forecast": False,
                },
            ],
        }
