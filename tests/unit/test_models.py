"""Unit tests for Pydantic models: ClaimModel, VerdictModel, ReportModel, CostModel."""

import pytest
from pydantic import ValidationError

from finfolio.models import ClaimModel, CostModel, ReportModel, VerdictModel


class TestClaimModel:
    """Test ClaimModel validation and schema."""

    def test_valid_claim_with_mm_ss_timestamp(self):
        """Test creating a valid claim with MM:SS timestamp."""
        claim = ClaimModel(
            id="claim_001",
            text="Apple stock closed at $195.42 on Sept 23",
            quote="the stock was trading at one ninety five forty two",
            type="number",
            confidence=0.92,
            timestamp="12:34",
            is_opinion=False,
            is_forecast=False,
        )
        assert claim.id == "claim_001"
        assert claim.text == "Apple stock closed at $195.42 on Sept 23"
        assert claim.confidence == 0.92
        assert claim.timestamp == "12:34"

    def test_valid_claim_with_hh_mm_ss_timestamp(self):
        """Test creating a valid claim with HH:MM:SS timestamp."""
        claim = ClaimModel(
            id="claim_002",
            text="Test claim",
            quote="test quote",
            type="date",
            confidence=0.85,
            timestamp="01:23:45",
            is_opinion=False,
            is_forecast=False,
        )
        assert claim.timestamp == "01:23:45"

    def test_claim_confidence_validation_min(self):
        """Test that confidence must be >= 0.0."""
        with pytest.raises(ValidationError) as exc_info:
            ClaimModel(
                id="claim_003",
                text="Test",
                quote="test",
                type="number",
                confidence=-0.1,
                timestamp="12:34",
            )
        assert "confidence" in str(exc_info.value).lower()

    def test_claim_confidence_validation_max(self):
        """Test that confidence must be <= 1.0."""
        with pytest.raises(ValidationError) as exc_info:
            ClaimModel(
                id="claim_004",
                text="Test",
                quote="test",
                type="number",
                confidence=1.1,
                timestamp="12:34",
            )
        assert "confidence" in str(exc_info.value).lower()

    def test_claim_type_enum_validation(self):
        """Test that type must be one of the allowed enum values."""
        with pytest.raises(ValidationError):
            ClaimModel(
                id="claim_005",
                text="Test",
                quote="test",
                type="invalid_type",
                confidence=0.9,
                timestamp="12:34",
            )

    def test_valid_claim_types(self):
        """Test all valid claim types."""
        valid_types = ["number", "date", "deal", "company-fact", "product-fact", "other"]
        for claim_type in valid_types:
            claim = ClaimModel(
                id=f"claim_{claim_type}",
                text="Test",
                quote="test",
                type=claim_type,
                confidence=0.9,
                timestamp="12:34",
            )
            assert claim.type == claim_type

    def test_claim_empty_text_fails_validation(self):
        """Test that empty text fails validation."""
        with pytest.raises(ValidationError):
            ClaimModel(
                id="claim_006",
                text="",
                quote="test",
                type="number",
                confidence=0.9,
                timestamp="12:34",
            )

    def test_claim_empty_quote_fails_validation(self):
        """Test that empty quote fails validation."""
        with pytest.raises(ValidationError):
            ClaimModel(
                id="claim_007",
                text="Test",
                quote="",
                type="number",
                confidence=0.9,
                timestamp="12:34",
            )

    def test_invalid_timestamp_format(self):
        """Test that invalid timestamp format fails validation."""
        with pytest.raises(ValidationError):
            ClaimModel(
                id="claim_008",
                text="Test",
                quote="test",
                type="number",
                confidence=0.9,
                timestamp="invalid",
            )

    def test_invalid_timestamp_values_mm_ss(self):
        """Test that invalid MM:SS values fail."""
        with pytest.raises(ValidationError):
            ClaimModel(
                id="claim_009",
                text="Test",
                quote="test",
                type="number",
                confidence=0.9,
                timestamp="60:90",  # Invalid minutes and seconds
            )

    def test_invalid_timestamp_values_hh_mm_ss(self):
        """Test that invalid HH:MM:SS values fail."""
        with pytest.raises(ValidationError):
            ClaimModel(
                id="claim_010",
                text="Test",
                quote="test",
                type="number",
                confidence=0.9,
                timestamp="25:61:62",  # Invalid hour, minute, second
            )

    def test_claim_opinion_flag(self):
        """Test is_opinion flag."""
        claim = ClaimModel(
            id="claim_011",
            text="Test opinion",
            quote="test",
            type="other",
            confidence=0.8,
            timestamp="12:34",
            is_opinion=True,
        )
        assert claim.is_opinion is True

    def test_claim_forecast_flag(self):
        """Test is_forecast flag."""
        claim = ClaimModel(
            id="claim_012",
            text="Test forecast",
            quote="test",
            type="other",
            confidence=0.8,
            timestamp="12:34",
            is_forecast=True,
        )
        assert claim.is_forecast is True


class TestVerdictModel:
    """Test VerdictModel validation and schema."""

    def test_valid_verdict_true(self):
        """Test creating a valid True verdict."""
        verdict = VerdictModel(
            claim_id="claim_001",
            claim_text="Apple stock closed at $195.42 on Sept 23",
            verdict="True",
            note="Verified against Yahoo Finance data for Sept 23, 2026.",
            source_url="https://finance.yahoo.com/quote/AAPL/history",
            source_title="Yahoo Finance - Apple Historical Data",
            source_date="2026-09-23",
            search_query="Apple AAPL stock price Sept 23 2026",
            fact_checked_at="2026-09-25T15:30:05Z",
            llm_model="claude-haiku-4-5-20251001",
            reasoning_cost={"tokens_in": 450, "tokens_out": 85, "cost_usd": 0.0001},
        )
        assert verdict.verdict == "True"
        assert verdict.source_url is not None

    def test_valid_verdict_false(self):
        """Test creating a valid False verdict."""
        verdict = VerdictModel(
            claim_id="claim_002",
            claim_text="Test false claim",
            verdict="False",
            note="Contradicts published sources.",
            source_url="https://example.com/fact",
            source_title="Example Source",
            source_date="2026-09-25",
            search_query="test query",
            fact_checked_at="2026-09-25T15:30:05Z",
            llm_model="claude-haiku-4-5-20251001",
            reasoning_cost={"tokens_in": 400, "tokens_out": 80, "cost_usd": 0.00009},
        )
        assert verdict.verdict == "False"

    def test_valid_verdict_partially_supported(self):
        """Test creating a Partially supported verdict."""
        verdict = VerdictModel(
            claim_id="claim_003",
            claim_text="Test partial claim",
            verdict="Partially supported/overstated",
            note="Partially accurate but overstated.",
            source_url="https://example.com/partial",
            source_title="Example Partial",
            source_date="2026-09-25",
            search_query="test query",
            fact_checked_at="2026-09-25T15:30:05Z",
            llm_model="claude-haiku-4-5-20251001",
            reasoning_cost={"tokens_in": 420, "tokens_out": 75, "cost_usd": 0.00008},
        )
        assert verdict.verdict == "Partially supported/overstated"

    def test_valid_verdict_unverified(self):
        """Test creating an Unverified verdict."""
        verdict = VerdictModel(
            claim_id="claim_004",
            claim_text="Test unverified claim",
            verdict="Unverified",
            note="No sources found to verify or contradict this claim.",
            source_url=None,
            source_title=None,
            source_date=None,
            search_query="test query unverified",
            fact_checked_at="2026-09-25T15:30:05Z",
            llm_model="claude-haiku-4-5-20251001",
            reasoning_cost={"tokens_in": 300, "tokens_out": 60, "cost_usd": 0.00006},
        )
        assert verdict.verdict == "Unverified"
        assert verdict.source_url is None

    def test_verdict_invalid_enum(self):
        """Test that invalid verdict enum fails."""
        with pytest.raises(ValidationError):
            VerdictModel(
                claim_id="claim_005",
                claim_text="Test",
                verdict="Maybe",  # Invalid enum value
                note="Test note",
                search_query="test",
                fact_checked_at="2026-09-25T15:30:05Z",
                llm_model="claude-haiku-4-5-20251001",
                reasoning_cost={"tokens_in": 100, "tokens_out": 50, "cost_usd": 0.00005},
            )

    def test_verdict_empty_note_fails(self):
        """Test that empty note fails validation."""
        with pytest.raises(ValidationError):
            VerdictModel(
                claim_id="claim_006",
                claim_text="Test",
                verdict="True",
                note="",  # Empty note
                source_url="https://example.com",
                search_query="test",
                fact_checked_at="2026-09-25T15:30:05Z",
                llm_model="claude-haiku-4-5-20251001",
                reasoning_cost={"tokens_in": 100, "tokens_out": 50, "cost_usd": 0.00005},
            )

    def test_verdict_note_too_long_fails(self):
        """Test that note > 250 characters fails."""
        long_note = "x" * 251
        with pytest.raises(ValidationError):
            VerdictModel(
                claim_id="claim_007",
                claim_text="Test",
                verdict="True",
                note=long_note,
                source_url="https://example.com",
                search_query="test",
                fact_checked_at="2026-09-25T15:30:05Z",
                llm_model="claude-haiku-4-5-20251001",
                reasoning_cost={"tokens_in": 100, "tokens_out": 50, "cost_usd": 0.00005},
            )

    def test_verdict_true_without_source_url_fails(self):
        """Test that True verdict without source_url fails."""
        with pytest.raises(ValidationError):
            VerdictModel(
                claim_id="claim_008",
                claim_text="Test",
                verdict="True",
                note="Verified",
                source_url=None,  # Missing for True verdict
                search_query="test",
                fact_checked_at="2026-09-25T15:30:05Z",
                llm_model="claude-haiku-4-5-20251001",
                reasoning_cost={"tokens_in": 100, "tokens_out": 50, "cost_usd": 0.00005},
            )

    def test_verdict_false_without_source_url_fails(self):
        """Test that False verdict without source_url fails."""
        with pytest.raises(ValidationError):
            VerdictModel(
                claim_id="claim_009",
                claim_text="Test",
                verdict="False",
                note="Not verified",
                source_url=None,  # Missing for False verdict
                search_query="test",
                fact_checked_at="2026-09-25T15:30:05Z",
                llm_model="claude-haiku-4-5-20251001",
                reasoning_cost={"tokens_in": 100, "tokens_out": 50, "cost_usd": 0.00005},
            )

    def test_verdict_empty_search_query_fails(self):
        """Test that empty search_query fails."""
        with pytest.raises(ValidationError):
            VerdictModel(
                claim_id="claim_010",
                claim_text="Test",
                verdict="True",
                note="Test",
                source_url="https://example.com",
                search_query="",  # Empty
                fact_checked_at="2026-09-25T15:30:05Z",
                llm_model="claude-haiku-4-5-20251001",
                reasoning_cost={"tokens_in": 100, "tokens_out": 50, "cost_usd": 0.00005},
            )


class TestCostModel:
    """Test CostModel validation."""

    def test_valid_cost_model(self):
        """Test creating a valid cost model."""
        cost = CostModel(search_usd=0.02, llm_usd=0.01, total_usd=0.03)
        assert cost.search_usd == 0.02
        assert cost.llm_usd == 0.01
        assert cost.total_usd == 0.03

    def test_cost_total_validation(self):
        """Test that total_usd must equal search_usd + llm_usd."""
        with pytest.raises(ValidationError):
            CostModel(search_usd=0.02, llm_usd=0.01, total_usd=0.04)  # Incorrect total

    def test_cost_zero_values(self):
        """Test that zero costs are allowed."""
        cost = CostModel(search_usd=0.0, llm_usd=0.0, total_usd=0.0)
        assert cost.total_usd == 0.0


class TestReportModel:
    """Test ReportModel validation and schema."""

    def test_valid_report(self):
        """Test creating a valid report model."""
        report = ReportModel(
            video_id="dQw4w9WgXcQ",
            title="Apple Q3 Earnings Review",
            channel_name="FinancialAdvisor123",
            channel_url="https://youtube.com/@FinancialAdvisor123",
            source_url="https://youtube.com/watch?v=dQw4w9WgXcQ",
            transcript_source="YouTube API",
            fact_checked_at="2026-09-25T15:30:00Z",
            fact_check_duration_seconds=45.2,
            search_provider="Tavily",
            llm_model="claude-haiku-4-5-20251001",
            cost={"search_usd": 0.02, "llm_usd": 0.01, "total_usd": 0.03},
            summary={"claims": []},
            verdicts=[],
            claim_count=1,
            verdict_count=0,
            verdict_breakdown={
                "True": 0,
                "Partially supported/overstated": 0,
                "Unverified": 0,
                "False": 0,
            },
            disclaimer="FinFolio reports facts and their accuracy. This is not financial advice.",
        )
        assert report.video_id == "dQw4w9WgXcQ"
        assert (
            report.disclaimer
            == "FinFolio reports facts and their accuracy. This is not financial advice."
        )

    def test_report_disclaimer_validation(self):
        """Test that disclaimer must be the exact fixed text."""
        with pytest.raises(ValidationError):
            ReportModel(
                video_id="test_id",
                title="Test",
                channel_name="Test Channel",
                channel_url="https://example.com",
                source_url="https://example.com/video",
                transcript_source="YouTube API",
                fact_checked_at="2026-09-25T15:30:00Z",
                fact_check_duration_seconds=10.0,
                search_provider="Tavily",
                llm_model="claude-haiku-4-5-20251001",
                cost={"search_usd": 0.0, "llm_usd": 0.0, "total_usd": 0.0},
                summary={},
                verdicts=[],
                claim_count=0,
                verdict_count=0,
                verdict_breakdown={
                    "True": 0,
                    "Partially supported/overstated": 0,
                    "Unverified": 0,
                    "False": 0,
                },
                disclaimer="Wrong disclaimer text",
            )

    def test_report_duration_must_be_positive(self):
        """Test that fact_check_duration_seconds must be > 0."""
        with pytest.raises(ValidationError):
            ReportModel(
                video_id="test_id",
                title="Test",
                channel_name="Test Channel",
                channel_url="https://example.com",
                source_url="https://example.com/video",
                transcript_source="YouTube API",
                fact_checked_at="2026-09-25T15:30:00Z",
                fact_check_duration_seconds=0,  # Invalid
                search_provider="Tavily",
                llm_model="claude-haiku-4-5-20251001",
                cost={"search_usd": 0.0, "llm_usd": 0.0, "total_usd": 0.0},
                summary={},
                verdicts=[],
                claim_count=0,
                verdict_count=0,
                verdict_breakdown={
                    "True": 0,
                    "Partially supported/overstated": 0,
                    "Unverified": 0,
                    "False": 0,
                },
                disclaimer="FinFolio reports facts and their accuracy. This is not financial advice.",
            )

    def test_report_verdict_count_matches_verdicts_list(self):
        """Test that verdict_count must equal len(verdicts)."""
        with pytest.raises(ValidationError):
            ReportModel(
                video_id="test_id",
                title="Test",
                channel_name="Test Channel",
                channel_url="https://example.com",
                source_url="https://example.com/video",
                transcript_source="YouTube API",
                fact_checked_at="2026-09-25T15:30:00Z",
                fact_check_duration_seconds=10.0,
                search_provider="Tavily",
                llm_model="claude-haiku-4-5-20251001",
                cost={"search_usd": 0.0, "llm_usd": 0.0, "total_usd": 0.0},
                summary={},
                verdicts=[],
                claim_count=0,
                verdict_count=5,  # Mismatch: should be 0
                verdict_breakdown={
                    "True": 0,
                    "Partially supported/overstated": 0,
                    "Unverified": 0,
                    "False": 0,
                },
                disclaimer="FinFolio reports facts and their accuracy. This is not financial advice.",
            )

    def test_report_verdict_breakdown_sums_correctly(self):
        """Test that verdict_breakdown sums to verdict_count."""
        with pytest.raises(ValidationError):
            ReportModel(
                video_id="test_id",
                title="Test",
                channel_name="Test Channel",
                channel_url="https://example.com",
                source_url="https://example.com/video",
                transcript_source="YouTube API",
                fact_checked_at="2026-09-25T15:30:00Z",
                fact_check_duration_seconds=10.0,
                search_provider="Tavily",
                llm_model="claude-haiku-4-5-20251001",
                cost={"search_usd": 0.0, "llm_usd": 0.0, "total_usd": 0.0},
                summary={},
                verdicts=[],
                claim_count=0,
                verdict_count=1,
                verdict_breakdown={
                    "True": 0,
                    "Partially supported/overstated": 0,
                    "Unverified": 0,
                    "False": 0,
                },  # Sums to 0, not 1
                disclaimer="FinFolio reports facts and their accuracy. This is not financial advice.",
            )
