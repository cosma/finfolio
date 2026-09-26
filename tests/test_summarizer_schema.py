"""Unit tests for summarizer Pydantic schemas."""

from datetime import datetime

import pytest
from pydantic import ValidationError

from finfolio.summarizer_schema import Claim, ClaimType, SummaryMetadata, SummaryOutput


class TestClaimType:
    """Tests for ClaimType enum."""

    def test_all_claim_types_defined(self):
        """Test all required claim types are defined."""
        assert ClaimType.NUMBER.value == "number"
        assert ClaimType.DATE.value == "date"
        assert ClaimType.DEAL.value == "deal"
        assert ClaimType.COMPANY_FACT.value == "company-fact"
        assert ClaimType.PRODUCT_FACT.value == "product-fact"


class TestClaim:
    """Tests for Claim model."""

    def test_valid_claim(self):
        """Test creating a valid claim."""
        claim = Claim(
            type=ClaimType.NUMBER,
            claim="Apple stock closed at $200",
            quote="Apple stock closed at $200 on September 25, 2024",
            source_timestamp="12:34:00",
            confidence_score=0.95,
        )
        assert claim.type == ClaimType.NUMBER
        assert claim.confidence_score == 0.95

    def test_claim_without_optional_fields(self):
        """Test creating claim without optional timestamp and confidence."""
        claim = Claim(
            type=ClaimType.DATE,
            claim="iPhone 15 Pro released September 2023",
            quote="iPhone 15 Pro was released in September 2023",
        )
        assert claim.source_timestamp is None
        assert claim.confidence_score is None

    def test_claim_type_validation(self):
        """Test claim type must be valid enum."""
        with pytest.raises(ValidationError):
            Claim(
                type="invalid-type",
                claim="Test",
                quote="Test quote",
            )

    def test_claim_min_length(self):
        """Test claim must not be empty."""
        with pytest.raises(ValidationError):
            Claim(
                type=ClaimType.NUMBER,
                claim="",
                quote="Test quote",
            )

    def test_claim_max_length(self):
        """Test claim has reasonable max length."""
        with pytest.raises(ValidationError):
            Claim(
                type=ClaimType.NUMBER,
                claim="x" * 501,  # Exceeds max 500
                quote="Test quote",
            )

    def test_timestamp_format_validation(self):
        """Test timestamp format must match HH:MM:SS."""
        # Valid timestamps (HH:MM:SS format)
        Claim(
            type=ClaimType.NUMBER,
            claim="Test",
            quote="Test",
            source_timestamp="00:00:00",
        )
        Claim(
            type=ClaimType.NUMBER,
            claim="Test",
            quote="Test",
            source_timestamp="23:59:59",
        )
        Claim(
            type=ClaimType.NUMBER,
            claim="Test",
            quote="Test",
            source_timestamp="12:34:56",
        )

        # Invalid timestamps (wrong format)
        with pytest.raises(ValidationError):
            Claim(
                type=ClaimType.NUMBER,
                claim="Test",
                quote="Test",
                source_timestamp="invalid",
            )

        with pytest.raises(ValidationError):
            Claim(
                type=ClaimType.NUMBER,
                claim="Test",
                quote="Test",
                source_timestamp="12:60",  # Missing seconds
            )

        with pytest.raises(ValidationError):
            Claim(
                type=ClaimType.NUMBER,
                claim="Test",
                quote="Test",
                source_timestamp="1:2:3",  # Single digits, needs padding
            )

    def test_confidence_score_range(self):
        """Test confidence score must be 0.0-1.0."""
        # Valid scores
        Claim(
            type=ClaimType.NUMBER,
            claim="Test",
            quote="Test",
            confidence_score=0.0,
        )
        Claim(
            type=ClaimType.NUMBER,
            claim="Test",
            quote="Test",
            confidence_score=1.0,
        )
        Claim(
            type=ClaimType.NUMBER,
            claim="Test",
            quote="Test",
            confidence_score=0.5,
        )

        # Invalid scores
        with pytest.raises(ValidationError):
            Claim(
                type=ClaimType.NUMBER,
                claim="Test",
                quote="Test",
                confidence_score=1.5,
            )

        with pytest.raises(ValidationError):
            Claim(
                type=ClaimType.NUMBER,
                claim="Test",
                quote="Test",
                confidence_score=-0.1,
            )


class TestSummaryMetadata:
    """Tests for SummaryMetadata model."""

    def test_valid_metadata(self):
        """Test creating valid metadata."""
        metadata = SummaryMetadata(
            transcript_tokens=8500,
            model="claude-haiku-4-5-20251001",
            temperature=0.3,
            timestamp=datetime.fromisoformat("2026-09-25T14:30:00+00:00"),
            cost_usd=0.034,
            input_tokens=8500,
            output_tokens=612,
        )
        assert metadata.transcript_tokens == 8500
        assert metadata.temperature == 0.3

    def test_metadata_with_optional_fields(self):
        """Test metadata with optional fields omitted."""
        metadata = SummaryMetadata(
            transcript_tokens=1000,
            model="claude-haiku-4-5-20251001",
            temperature=0.3,
            timestamp=datetime.now(),
        )
        assert metadata.cost_usd is None
        assert metadata.input_tokens is None


class TestSummaryOutput:
    """Tests for SummaryOutput model."""

    def test_valid_summary_output(self):
        """Test creating valid summary output."""
        summary_text = (
            "The advisor discussed three key investment themes: semiconductor supply constraints, "
            "energy stocks in ESG portfolios, and fintech M&A activity. Recommended focusing on "
            "chip manufacturers with strong runways while cautioning against overpaying for SaaS deals. "
            "Overall bullish on AI-related infrastructure plays with measured risk management."
        )
        summary = SummaryOutput(
            summary=summary_text,
            claims=[
                Claim(
                    type=ClaimType.NUMBER,
                    claim="S&P 500 at 5432",
                    quote="S&P 500 is at 5432",
                )
            ],
            metadata=SummaryMetadata(
                transcript_tokens=1000,
                model="claude-haiku-4-5-20251001",
                temperature=0.3,
                timestamp=datetime.now(),
            ),
        )
        assert len(summary.claims) == 1
        assert "semiconductor" in summary.summary

    def test_summary_min_length(self):
        """Test summary must be at least 150 characters."""
        with pytest.raises(ValidationError):
            SummaryOutput(
                summary="Short",
                claims=[
                    Claim(
                        type=ClaimType.NUMBER,
                        claim="Test",
                        quote="Test",
                    )
                ],
                metadata=SummaryMetadata(
                    transcript_tokens=100,
                    model="claude-haiku-4-5-20251001",
                    temperature=0.3,
                    timestamp=datetime.now(),
                ),
            )

    def test_claims_min_items(self):
        """Test claims list must not be empty."""
        with pytest.raises(ValidationError):
            SummaryOutput(
                summary="x" * 200,
                claims=[],
                metadata=SummaryMetadata(
                    transcript_tokens=100,
                    model="claude-haiku-4-5-20251001",
                    temperature=0.3,
                    timestamp=datetime.now(),
                ),
            )

    def test_invalid_claims_in_list(self):
        """Test all claims in list must be valid."""
        with pytest.raises(ValidationError):
            SummaryOutput(
                summary="x" * 200,
                claims=[
                    Claim(
                        type=ClaimType.NUMBER,
                        claim="Valid claim",
                        quote="Valid quote",
                    ),
                    {
                        "type": "invalid-type",
                        "claim": "Invalid",
                        "quote": "Invalid",
                    },
                ],
                metadata=SummaryMetadata(
                    transcript_tokens=100,
                    model="claude-haiku-4-5-20251001",
                    temperature=0.3,
                    timestamp=datetime.now(),
                ),
            )
