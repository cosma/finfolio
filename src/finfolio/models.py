"""Pydantic models for fact-checking domain entities."""

import re
from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator

# Fixed disclaimer carried by every report and digest (Constitution Principle II).
DISCLAIMER = "FinFolio reports facts and their accuracy. This is not financial advice."


class ClaimModel(BaseModel):
    """Represents a factual claim extracted from a video transcript."""

    id: str = Field(..., description="Unique identifier for the claim")
    text: str = Field(..., min_length=1, description="Full claim statement")
    quote: str = Field(..., min_length=1, description="Exact transcript excerpt")
    type: Literal["number", "date", "deal", "company-fact", "product-fact", "other"] = Field(
        ..., description="Category of the claim"
    )
    confidence: float = Field(
        ..., ge=0.0, le=1.0, description="Summarization confidence [0.0, 1.0]"
    )
    timestamp: str = Field(..., description="Source timestamp in MM:SS or HH:MM:SS format")
    is_opinion: bool = Field(
        default=False, description="True if marked as opinion/forecast (skip fact-check)"
    )
    is_forecast: bool = Field(default=False, description="True if marked as prediction")

    @field_validator("timestamp")
    @classmethod
    def validate_timestamp(cls, v: str) -> str:
        """Validate timestamp format (MM:SS or HH:MM:SS)."""
        # MM:SS format
        mm_ss_pattern = r"^([0-5]?\d):([0-5]?\d)$"
        # HH:MM:SS format
        hh_mm_ss_pattern = r"^([01]?\d|2[0-3]):([0-5]?\d):([0-5]?\d)$"

        if not (re.match(mm_ss_pattern, v) or re.match(hh_mm_ss_pattern, v)):
            raise ValueError(f"Timestamp must be in MM:SS or HH:MM:SS format, got: {v}")
        return v

    model_config = {"str_strip_whitespace": True}


class CostModel(BaseModel):
    """Represents cost breakdown for fact-checking operations."""

    search_usd: float = Field(..., ge=0.0, description="Cost of web search operations")
    llm_usd: float = Field(..., ge=0.0, description="Cost of LLM operations")
    total_usd: float = Field(..., ge=0.0, description="Total cost")

    @field_validator("total_usd")
    @classmethod
    def validate_total(cls, v: float, info) -> float:
        """Validate that total equals search_usd + llm_usd."""
        if "search_usd" in info.data and "llm_usd" in info.data:
            expected_total = info.data["search_usd"] + info.data["llm_usd"]
            # Allow small floating point rounding errors
            if abs(v - expected_total) > 1e-10:
                raise ValueError(
                    f"total_usd ({v}) must equal search_usd + llm_usd ({expected_total})"
                )
        return v


class VerdictModel(BaseModel):
    """Represents the fact-checking result for a single claim."""

    claim_id: str = Field(..., description="Reference to Claim.id")
    claim_text: str = Field(..., description="Denormalized claim text for readability")
    verdict: Literal["True", "Partially supported", "Unverified", "False"] = Field(
        ..., description="Verdict category"
    )
    note: str = Field(
        ..., min_length=1, max_length=250, description="1-2 sentences explaining verdict"
    )
    source_url: str | None = Field(default=None, description="Primary source URL from search")
    source_title: str | None = Field(default=None, description="Source page title / publication")
    source_date: str | None = Field(default=None, description="Publication date (ISO 8601)")
    search_query: str = Field(..., min_length=1, description="Query sent to Tavily search")
    fact_checked_at: str = Field(..., description="ISO 8601 timestamp when fact-checking occurred")
    llm_model: str = Field(..., min_length=1, description="Model used for verdict reasoning")
    reasoning_cost: dict = Field(
        ..., description="Cost breakdown: {tokens_in, tokens_out, cost_usd}"
    )
    verified_by: str | None = Field(
        default=None,
        description="Search provider that produced this verdict: duckduckgo or tavily. Missing on verdicts that must be re-checked.",
    )
    confidence: float | None = Field(
        default=None, ge=0.0, le=1.0, description="LLM confidence in the verdict, 0.0 to 1.0"
    )

    @model_validator(mode="after")
    def validate_source_url_for_verdict(self) -> "VerdictModel":
        """Validate that True/False verdicts have source_url."""
        if self.verdict in ("True", "False") and self.source_url is None:
            raise ValueError(f'Verdict "{self.verdict}" requires source_url to be provided')
        return self

    model_config = {"str_strip_whitespace": True}


class ReportModel(BaseModel):
    """Represents per-video fact-checking result."""

    # Metadata
    video_id: str = Field(..., description="YouTube video ID")
    title: str = Field(..., min_length=1, description="Video title")
    channel_name: str = Field(..., min_length=1, description="YouTube channel name")
    channel_url: str = Field(..., min_length=1, description="Channel URL")
    source_url: str = Field(..., min_length=1, description="YouTube video URL")
    transcript_source: str = Field(
        ..., min_length=1, description="Source of transcript (YouTube API or Manual)"
    )

    # Fact-checking metadata
    fact_checked_at: str = Field(..., description="ISO 8601 timestamp")
    fact_check_duration_seconds: float = Field(
        ..., gt=0, description="Wall-clock time for fact-checking"
    )
    search_provider: Literal["Tavily"] = Field(default="Tavily", description="Web search provider")
    llm_model: str = Field(..., min_length=1, description="LLM model used for verdicts")

    # Cost tracking
    cost: dict = Field(..., description="Cost breakdown {search_usd, llm_usd, total_usd}")

    # Summary and verdicts
    summary: dict = Field(default_factory=dict, description="Reference to Module 2 summary")
    verdicts: list = Field(default_factory=list, description="List of VerdictModel objects")

    # Counts
    claim_count: int = Field(..., ge=0, description="Total claims processed")
    verdict_count: int = Field(..., ge=0, description="Verdicts assigned")
    verdict_breakdown: dict = Field(
        ...,
        description="Breakdown by verdict type: {True, Partially supported, Unverified, False}",
    )

    # Report footer
    disclaimer: str = Field(..., description="Static disclaimer text (immutable per Principle II)")
    monetization_disclosure: str | None = Field(
        default=None, description="Optional monetization disclosure"
    )

    @field_validator("disclaimer")
    @classmethod
    def validate_disclaimer(cls, v: str) -> str:
        """Validate that disclaimer is the exact fixed text."""
        if v != DISCLAIMER:
            raise ValueError(f'Disclaimer must be exactly: "{DISCLAIMER}". Got: "{v}"')
        return v

    @field_validator("verdict_count")
    @classmethod
    def validate_verdict_count(cls, v: int, info) -> int:
        """Validate that verdict_count matches len(verdicts)."""
        if "verdicts" in info.data:
            if v != len(info.data["verdicts"]):
                raise ValueError(
                    f"verdict_count ({v}) must equal len(verdicts) ({len(info.data['verdicts'])})"
                )
        return v

    @field_validator("verdict_breakdown")
    @classmethod
    def validate_verdict_breakdown(cls, v: dict, info) -> dict:
        """Validate that verdict_breakdown sums to verdict_count."""
        if "verdict_count" in info.data:
            expected_keys = {"True", "Partially supported", "Unverified", "False"}
            actual_keys = set(v.keys())
            if actual_keys != expected_keys:
                raise ValueError(
                    f"verdict_breakdown must have keys {expected_keys}, got {actual_keys}"
                )

            total = sum(v.values())
            if total != info.data["verdict_count"]:
                raise ValueError(
                    f"verdict_breakdown sum ({total}) must equal verdict_count ({info.data['verdict_count']})"
                )
        return v

    model_config = {"str_strip_whitespace": True}


def verdict_needs_recheck(verdict: dict) -> bool:
    """True if a stored verdict must be checked again.

    Verdicts written before verified_by existed, and verdicts from a failed LLM parse, have no
    verified_by. An Unverified verdict without one may be a search failure, not a real finding.
    """
    return verdict.get("verdict") == "Unverified" and not verdict.get("verified_by")
