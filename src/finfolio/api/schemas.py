"""Response models for the read API. They drive the OpenAPI schema shown in Swagger UI."""

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class DigestSummary(BaseModel):
    """One row in the digest list."""

    month: str = Field(description="Month identifier, YYYY-MM", examples=["2026-08"])
    generated_at: str
    report_count: int
    verdict_breakdown: dict[str, int]


class DigestList(BaseModel):
    items: list[DigestSummary]


class DigestDetail(BaseModel):
    """A full monthly digest, returned as stored. Stored fields pass through unchanged."""

    model_config = ConfigDict(extra="allow")

    month: str
    generated_at: str | None = None
    report_count: int | None = None
    verdict_breakdown: dict[str, int] | None = None
    per_channel_breakdown: list[dict[str, Any]] = Field(default_factory=list)
    monetization_summary: list[dict[str, Any]] = Field(default_factory=list)
    disclaimer: str | None = None


class ReportSummary(BaseModel):
    """One row in the per-video report list."""

    video_id: str
    title: str
    channel_name: str
    channel_url: str
    fact_checked_at: str
    claim_count: int
    verdict_breakdown: dict[str, int]


class ReportPage(BaseModel):
    items: list[ReportSummary]
    total: int = Field(description="Number of reports matching the filters, across all pages")
    page: int
    page_size: int


class ReportDetail(BaseModel):
    """A full per-video report, returned as stored. Stored fields pass through unchanged."""

    model_config = ConfigDict(extra="allow")

    video_id: str
    title: str | None = None
    channel_name: str | None = None
    channel_url: str | None = None
    source_url: str | None = None
    transcript_source: str | None = None
    fact_checked_at: str | None = None
    claim_count: int | None = None
    verdict_count: int | None = None
    verdict_breakdown: dict[str, int] | None = None
    verdicts: list[dict[str, Any]] = Field(default_factory=list)
    summary: dict[str, Any] | None = None
    cost: dict[str, Any] | None = None
    disclaimer: str | None = None


class SkippedItem(BaseModel):
    item: str = Field(description="Path of the stored file that was skipped")
    reason: str


class RefreshResult(BaseModel):
    indexed: dict[str, int] = Field(description="Counts of indexed reports and digests")
    skipped: list[SkippedItem] = Field(description="Files that could not be indexed")
