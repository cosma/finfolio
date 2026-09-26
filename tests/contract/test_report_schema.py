"""Contract tests for report schema validation (US1).

Ensures that generated reports conform to ReportModel schema
and meet all business requirements.
"""

import pytest

from finfolio.models import ReportModel


@pytest.mark.contract
class TestReportSchema:
    """Test report schema compliance."""

    def test_report_schema_validation(self):
        """Test that a complete report validates against schema."""
        report_data = {
            "video_id": "test_vid_001",
            "title": "Finance Discussion",
            "channel_name": "Finance Channel",
            "channel_url": "https://youtube.com/@FinanceChannel",
            "source_url": "https://youtube.com/watch?v=test_vid_001",
            "transcript_source": "YouTube API",
            "fact_checked_at": "2026-09-25T15:30:00Z",
            "fact_check_duration_seconds": 45.2,
            "search_provider": "Tavily",
            "llm_model": "claude-haiku-4-5-20251001",
            "cost": {"search_usd": 0.02, "llm_usd": 0.01, "total_usd": 0.03},
            "summary": {"video_id": "test_vid_001", "claims": []},
            "verdicts": [
                {
                    "claim_id": "claim_001",
                    "claim_text": "Test claim",
                    "verdict": "True",
                    "note": "Verified against sources",
                    "source_url": "https://example.com",
                    "source_title": "Example Source",
                    "source_date": "2026-09-25",
                    "search_query": "test query",
                    "fact_checked_at": "2026-09-25T15:30:05Z",
                    "llm_model": "claude-haiku-4-5-20251001",
                    "reasoning_cost": {"tokens_in": 100, "tokens_out": 50, "cost_usd": 0.0001},
                }
            ],
            "claim_count": 1,
            "verdict_count": 1,
            "verdict_breakdown": {
                "True": 1,
                "Partially supported/overstated": 0,
                "Unverified": 0,
                "False": 0,
            },
            "disclaimer": "FinFolio reports facts and their accuracy. This is not financial advice.",
        }

        # Should not raise
        report = ReportModel(**report_data)
        assert report.video_id == "test_vid_001"
        assert report.verdict_count == 1
        assert len(report.verdicts) == 1

    def test_report_disclaimer_present(self):
        """Test that disclaimer is exactly as specified."""
        report_data = {
            "video_id": "test_vid",
            "title": "Test",
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

        report = ReportModel(**report_data)
        expected = "FinFolio reports facts and their accuracy. This is not financial advice."
        assert report.disclaimer == expected

    def test_report_cost_fields_populated(self):
        """Test that cost fields are properly populated."""
        report_data = {
            "video_id": "test_vid",
            "title": "Test",
            "channel_name": "Test Channel",
            "channel_url": "https://example.com",
            "source_url": "https://youtube.com/watch?v=test",
            "transcript_source": "YouTube API",
            "fact_checked_at": "2026-09-25T15:30:00Z",
            "fact_check_duration_seconds": 10.0,
            "search_provider": "Tavily",
            "llm_model": "claude-haiku-4-5-20251001",
            "cost": {"search_usd": 0.02, "llm_usd": 0.01, "total_usd": 0.03},
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

        report = ReportModel(**report_data)
        assert report.cost["search_usd"] == 0.02
        assert report.cost["llm_usd"] == 0.01
        assert report.cost["total_usd"] == 0.03

    def test_report_verdict_breakdown_sums_correctly(self):
        """Test that verdict breakdown sums to verdict count."""
        verdicts_data = [
            {
                "claim_id": "claim_001",
                "claim_text": "True claim",
                "verdict": "True",
                "note": "Verified",
                "source_url": "https://example.com",
                "source_title": "Source",
                "source_date": "2026-09-25",
                "search_query": "query",
                "fact_checked_at": "2026-09-25T15:30:05Z",
                "llm_model": "claude-haiku-4-5-20251001",
                "reasoning_cost": {"tokens_in": 100, "tokens_out": 50, "cost_usd": 0.0001},
            },
            {
                "claim_id": "claim_002",
                "claim_text": "False claim",
                "verdict": "False",
                "note": "Not verified",
                "source_url": "https://example.com",
                "source_title": "Source",
                "source_date": "2026-09-25",
                "search_query": "query",
                "fact_checked_at": "2026-09-25T15:30:05Z",
                "llm_model": "claude-haiku-4-5-20251001",
                "reasoning_cost": {"tokens_in": 100, "tokens_out": 50, "cost_usd": 0.0001},
            },
            {
                "claim_id": "claim_003",
                "claim_text": "Unverified claim",
                "verdict": "Unverified",
                "note": "No sources",
                "source_url": None,
                "source_title": None,
                "source_date": None,
                "search_query": "query",
                "fact_checked_at": "2026-09-25T15:30:05Z",
                "llm_model": "claude-haiku-4-5-20251001",
                "reasoning_cost": {"tokens_in": 100, "tokens_out": 50, "cost_usd": 0.0001},
            },
        ]

        report_data = {
            "video_id": "test_vid",
            "title": "Test",
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
            "verdicts": verdicts_data,
            "claim_count": 3,
            "verdict_count": 3,
            "verdict_breakdown": {
                "True": 1,
                "Partially supported/overstated": 0,
                "Unverified": 1,
                "False": 1,
            },
            "disclaimer": "FinFolio reports facts and their accuracy. This is not financial advice.",
        }

        report = ReportModel(**report_data)
        total = sum(report.verdict_breakdown.values())
        assert total == report.verdict_count == 3

    def test_report_with_partial_verdict(self):
        """Test report with Partially supported/overstated verdict."""
        report_data = {
            "video_id": "test_vid",
            "title": "Test",
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
            "verdicts": [
                {
                    "claim_id": "claim_001",
                    "claim_text": "Partially correct claim",
                    "verdict": "Partially supported/overstated",
                    "note": "Partially accurate but overstated",
                    "source_url": "https://example.com",
                    "source_title": "Source",
                    "source_date": "2026-09-25",
                    "search_query": "query",
                    "fact_checked_at": "2026-09-25T15:30:05Z",
                    "llm_model": "claude-haiku-4-5-20251001",
                    "reasoning_cost": {"tokens_in": 100, "tokens_out": 50, "cost_usd": 0.0001},
                }
            ],
            "claim_count": 1,
            "verdict_count": 1,
            "verdict_breakdown": {
                "True": 0,
                "Partially supported/overstated": 1,
                "Unverified": 0,
                "False": 0,
            },
            "disclaimer": "FinFolio reports facts and their accuracy. This is not financial advice.",
        }

        report = ReportModel(**report_data)
        assert report.verdicts[0].verdict == "Partially supported/overstated"

    def test_report_empty_verdicts_valid(self):
        """Test that report with no verdicts is still valid."""
        report_data = {
            "video_id": "test_vid_no_claims",
            "title": "Test",
            "channel_name": "Test Channel",
            "channel_url": "https://example.com",
            "source_url": "https://youtube.com/watch?v=test",
            "transcript_source": "YouTube API",
            "fact_checked_at": "2026-09-25T15:30:00Z",
            "fact_check_duration_seconds": 0.5,
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

        report = ReportModel(**report_data)
        assert len(report.verdicts) == 0
        assert report.verdict_count == 0
