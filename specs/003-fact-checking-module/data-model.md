# Phase 1: Data Model & Entities

**Date**: 2026-09-25 | **Branch**: `003-fact-checking-module`

## Entity Overview

The fact-checking module defines entities for claims, verdicts, and reports. Entities inherit from or reference summarization module (Module 2) for claim data; fact-checking adds verdict fields and report persistence.

---

## Entity: Claim

**Source**: Extracted from summary by Module 2 and loaded from `storage/summaries/{video_id}.json`

**Fields**:
```python
@dataclass
class Claim:
    id: str                      # unique identifier (e.g., "claim_001")
    text: str                    # full claim statement
    quote: str                   # exact transcript excerpt
    type: Literal[
        "number",                # quantitative fact (stock price, percentage)
        "date",                  # temporal fact (deal announcement date)
        "deal",                  # acquisition, merger, partnership
        "company-fact",          # company-specific fact
        "product-fact",          # product feature or release
        "other"                  # uncategorized factual claim
    ]
    confidence: float            # summarization confidence [0.0, 1.0]
    timestamp: str               # source timestamp (MM:SS format)
    is_opinion: bool             # True if marked as opinion/forecast (skip fact-check)
    is_forecast: bool            # True if marked as prediction/forecast
```

**Validation Rules**:
- `text` and `quote` must be non-empty
- `type` must be one of the enumerated values
- `confidence` must be in [0.0, 1.0]
- `timestamp` must be valid MM:SS or HH:MM:SS format
- `is_opinion` = True → skip fact-checking (no verdict assigned)

**Relationships**:
- Belongs to: Video (parent)
- Referenced by: Verdict (1:1 mapping during fact-checking)

---

## Entity: Verdict

**Purpose**: Stores the fact-checking result for a single claim

**Fields**:
```python
@dataclass
class Verdict:
    claim_id: str                           # reference to Claim.id
    claim_text: str                         # denormalized for readability
    verdict: Literal[
        "True",
        "Partially supported/overstated",
        "Unverified",
        "False"
    ]
    note: str                               # 1-2 sentences explaining verdict
    source_url: str | None                  # primary source URL from search
    source_title: str | None                # source page title / publication
    source_date: str | None                 # publication date (ISO 8601)
    search_query: str                       # query sent to Tavily
    fact_checked_at: str                    # ISO 8601 timestamp
    llm_model: str                          # model used (for audit trail)
    reasoning_cost: dict                    # {"tokens_in": N, "tokens_out": M, "cost_usd": X}
```

**Validation Rules**:
- `claim_id` must reference an existing claim in parent Video
- `verdict` must be one of the four enumerated values
- `note` must be non-empty and <= 250 characters
- `source_url` required if verdict is "True" or "False", optional for "Unverified"
- `search_query` must be non-empty (denormalized for debugging)
- `fact_checked_at` must be valid ISO 8601
- `llm_model` must be non-empty (for audit trail; prevents model drift)

**State Transitions**:
- Initial: Claim exists, no Verdict
- Searched: Verdict assigned based on LLM reasoning
- Saved: Verdict persisted to report

**Error States**:
- If search times out: verdict = "Unverified", note = "Search timed out"
- If API quota exceeded: verdict = "Unverified", note = "Quota exhausted, retry later"
- If claim is malformed: skip (no verdict), log error

---

## Entity: Report

**Purpose**: Per-video fact-checking result; written to `storage/reports/videos/{video_id}.json`

**Fields**:
```python
@dataclass
class Report:
    # Metadata (from summary or video)
    video_id: str
    title: str
    channel_name: str
    source_url: str                         # YouTube video URL
    transcript_source: str                  # "YouTube API" or "Manual"
    
    # Fact-checking metadata
    fact_checked_at: str                    # ISO 8601
    fact_check_duration_seconds: float      # wall-clock time
    search_provider: Literal["Tavily"]
    llm_model: str                          # model used for verdicts
    
    # Cost tracking
    cost: dict                              # {"search_usd": X, "llm_usd": Y, "total_usd": Z}
    
    # Summary data (from Module 2)
    summary: dict                           # reference to summary metadata
    
    # Verdicts
    verdicts: list[Verdict]
    
    # Counts
    claim_count: int                        # total claims processed
    verdict_count: int                      # verdicts assigned
    verdict_breakdown: dict                 # {"True": N, "Partially supported": M, "Unverified": K, "False": L}
    
    # Report footer
    disclaimer: str                         # static: "FinFolio reports facts and their accuracy. This is not financial advice."
    monetization_disclosure: str | None     # e.g., "This video promotes [product/course]" if applicable
```

**Validation Rules**:
- All required fields must be non-empty
- `fact_checked_at` must be valid ISO 8601
- `fact_check_duration_seconds` must be > 0
- `cost` total must match sum of search_usd + llm_usd
- `verdict_count` must equal len(verdicts)
- `verdict_breakdown` must sum to `verdict_count`
- `disclaimer` must be present and unchanged (immutable text per Principle II)

**Relationships**:
- Parent: Video (1:1)
- Contains: list of Verdicts (1:many)
- References: Summary (includes denormalized copy from Module 2)

---

## Entity: Video

**Purpose**: Logical grouping for summary → report processing

**Fields** (logical; not persisted separately):
```python
@dataclass
class Video:
    video_id: str
    title: str
    channel_name: str
    source_url: str                         # YouTube URL
    has_summary: bool                       # exists in storage/summaries/
    has_report: bool                        # exists in storage/reports/videos/
```

**State Transitions**:
- Initial: `has_summary=False, has_report=False` (before Module 2)
- After Summarization: `has_summary=True, has_report=False`
- After Fact-Checking: `has_summary=True, has_report=True`
- Idempotent: If `has_report=True`, skip in `finfolio factcheck`

---

## Storage Schema

### Summary Input (from Module 2)
**Location**: `storage/summaries/{video_id}.json`
```json
{
  "video_id": "dQw4w9WgXcQ",
  "title": "Apple Q3 Earnings Review",
  "channel_name": "FinancialAdvisor123",
  "source_url": "https://youtube.com/watch?v=...",
  "transcript_source": "YouTube API",
  "summary": "...",
  "claims": [
    {
      "id": "claim_001",
      "text": "Apple stock closed at $195.42 on Sept 23",
      "quote": "the stock was trading at one ninety five forty two",
      "type": "number",
      "confidence": 0.92,
      "timestamp": "12:34",
      "is_opinion": false,
      "is_forecast": false
    }
  ]
}
```

### Report Output (Phase 1 design)
**Location**: `storage/reports/videos/{video_id}.json`
```json
{
  "video_id": "dQw4w9WgXcQ",
  "title": "Apple Q3 Earnings Review",
  "channel_name": "FinancialAdvisor123",
  "source_url": "https://youtube.com/watch?v=...",
  "transcript_source": "YouTube API",
  "fact_checked_at": "2026-09-25T15:30:00Z",
  "fact_check_duration_seconds": 45.2,
  "search_provider": "Tavily",
  "llm_model": "claude-haiku-4-5-20251001",
  "cost": {
    "search_usd": 0.02,
    "llm_usd": 0.01,
    "total_usd": 0.03
  },
  "summary": { ... },
  "verdicts": [
    {
      "claim_id": "claim_001",
      "claim_text": "Apple stock closed at $195.42 on Sept 23",
      "verdict": "True",
      "note": "Verified against Yahoo Finance data for Sept 23, 2026.",
      "source_url": "https://finance.yahoo.com/quote/AAPL/history",
      "source_title": "Yahoo Finance - Apple Historical Data",
      "source_date": "2026-09-23",
      "search_query": "Apple AAPL stock price Sept 23 2026",
      "fact_checked_at": "2026-09-25T15:30:05Z",
      "llm_model": "claude-haiku-4-5-20251001",
      "reasoning_cost": {
        "tokens_in": 450,
        "tokens_out": 85,
        "cost_usd": 0.0001
      }
    }
  ],
  "claim_count": 1,
  "verdict_count": 1,
  "verdict_breakdown": {
    "True": 1,
    "Partially supported/overstated": 0,
    "Unverified": 0,
    "False": 0
  },
  "disclaimer": "FinFolio reports facts and their accuracy. This is not financial advice.",
  "monetization_disclosure": null
}
```

---

## Key Invariants

1. **Claim Completeness**: Every claim in summary must be represented in verdicts (or marked as skipped/opinion)
2. **Verdict Consistency**: Same claim input always produces same verdict (temperature=0)
3. **Source Attribution**: True/False verdicts must have source URL; Unverified verdicts must have rationale in note
4. **Cost Tracking**: Sum of reasoning_cost.cost_usd per verdict equals report.cost.llm_usd
5. **Idempotency**: Running `finfolio factcheck` twice produces identical reports on second run
6. **Partial Persistence**: Report file is valid JSON at all intermediate states (even if not all claims verified)

---

## Type Safety (Python 3.10+)

All entities use dataclasses with type hints and pydantic for validation:

```python
from dataclasses import dataclass
from pydantic import BaseModel, validator, Field
from typing import Literal, Optional

class ClaimModel(BaseModel):
    id: str
    text: str
    quote: str
    type: Literal["number", "date", "deal", "company-fact", "product-fact", "other"]
    confidence: float = Field(ge=0.0, le=1.0)
    timestamp: str
    is_opinion: bool = False
    is_forecast: bool = False
    
    @validator("timestamp")
    def validate_timestamp(cls, v):
        # Ensure MM:SS or HH:MM:SS format
        ...

class VerdictModel(BaseModel):
    claim_id: str
    claim_text: str
    verdict: Literal["True", "Partially supported/overstated", "Unverified", "False"]
    note: str = Field(min_length=1, max_length=250)
    # ... other fields
```

---

**Phase 1 Data Model Complete**: Ready for contract definitions and quickstart validation.
