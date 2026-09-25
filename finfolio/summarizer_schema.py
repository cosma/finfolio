"""Pydantic models for transcript summarization output."""

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class ClaimType(StrEnum):
    """Enumeration of factual claim types."""

    NUMBER = "number"
    DATE = "date"
    DEAL = "deal"
    COMPANY_FACT = "company-fact"
    PRODUCT_FACT = "product-fact"


class Claim(BaseModel):
    """A discrete, verifiable factual claim extracted from a transcript."""

    type: ClaimType = Field(..., description="Category of factual claim")
    claim: str = Field(
        ..., min_length=1, max_length=500, description="The factual statement (1-2 sentences)"
    )
    quote: str = Field(
        ..., min_length=1, description="Exact source text from transcript (evidence)"
    )
    source_timestamp: str | None = Field(
        None,
        pattern=r"^\d{1,2}:\d{2}:\d{2}$",
        description="Video timestamp HH:MM:SS where claim was spoken",
    )
    confidence_score: float | None = Field(
        None, ge=0.0, le=1.0, description="LLM confidence that this is factual (0.0-1.0)"
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "type": "number",
                "claim": "Apple released the iPhone 15 Pro in September 2023",
                "quote": "Apple released the iPhone 15 Pro in September 2023",
                "source_timestamp": "12:34:00",
                "confidence_score": 0.98,
            }
        }
    )


class SummaryMetadata(BaseModel):
    """Metadata about the summarization process."""

    transcript_tokens: int = Field(..., ge=0, description="Estimated token count of input")
    model: str = Field(..., description="LLM model used")
    temperature: float = Field(..., ge=0.0, le=2.0, description="Temperature parameter used")
    timestamp: datetime = Field(..., description="UTC timestamp when summary was generated")
    cost_usd: float | None = Field(
        None, ge=0.0, description="Estimated cost of this LLM call in USD"
    )
    input_tokens: int | None = Field(None, ge=0, description="LLM input token count")
    output_tokens: int | None = Field(None, ge=0, description="LLM output token count")
    transcript_truncated: bool | None = Field(
        None, description="True if input was truncated due to context length"
    )


class SummaryOutput(BaseModel):
    """Output of transcript summarization: summary + claims + metadata."""

    summary: str = Field(
        ...,
        min_length=150,
        max_length=10000,
        description="Plain-language summary of key insights (150-400 words typical)",
    )
    claims: list[Claim] = Field(
        ...,
        min_length=1,
        description="List of discrete, verifiable factual claims (separated from opinions)",
    )
    metadata: SummaryMetadata = Field(..., description="Processing metadata")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "summary": "The advisor discussed AI chip manufacturers and energy stocks...",
                "claims": [
                    {
                        "type": "number",
                        "claim": "Tech sector P/E ratio at 22x",
                        "quote": "Tech sector is at 22 times earnings",
                        "confidence_score": 0.95,
                    }
                ],
                "metadata": {
                    "transcript_tokens": 8500,
                    "model": "claude-haiku-4-5-20251001",
                    "temperature": 0.3,
                    "timestamp": "2026-09-25T14:30:00Z",
                    "cost_usd": 0.034,
                },
            }
        }
    )
