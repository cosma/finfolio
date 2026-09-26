# Contract: Monthly Digest JSON Schema

**Scope**: Structure and validation of digest files written to `storage/reports/monthly/{year}-{month}.json`

**Version**: 1.1 | **Status**: Final (Updated per /speckit-clarify Clarification Q3)

---

## Schema (JSON Schema / Pydantic)

### Root: Digest Object (Clarification Q3)

```json
{
  "month": "2026-09",
  "generated_at": "2026-09-27T14:30:00Z",
  "report_count": 3,
  "verdict_breakdown": {
    "True": 5,
    "Partially supported": 2,
    "Unverified": 1,
    "False": 1
  },
  "per_channel_breakdown": [
    {
      "channel_name": "Financial Wisdom Daily",
      "channel_url": "https://youtube.com/@financialwisdom",
      "video_count": 2,
      "verdict_breakdown": {
        "True": 3,
        "Partially supported": 1,
        "Unverified": 0,
        "False": 0
      }
    },
    {
      "channel_name": "Stock Talk Pro",
      "channel_url": "https://youtube.com/@stocktalkpro",
      "video_count": 1,
      "verdict_breakdown": {
        "True": 2,
        "Partially supported": 1,
        "Unverified": 1,
        "False": 1
      }
    }
  ],
  "monetization_summary": [
    {
      "channel_name": "Financial Wisdom Daily",
      "disclosure": "This video is sponsored by InvestXYZ trading course ($199)"
    }
  ]
}
```

---

## Field Definitions

### Digest Metadata

**`month`** (string, required)
- Month in YYYY-MM format (ISO 8601 partial date)
- Pattern: `^\d{4}-\d{2}$`
- Example: `"2026-09"`
- Validation: Must be a valid calendar month (01-12 for MM)

**`generated_at`** (string, ISO 8601 UTC timestamp, required)
- When digest was generated
- Format: `YYYY-MM-DDTHH:MM:SSZ` (UTC)
- Example: `"2026-09-27T14:30:00Z"`
- Validation: Must be valid ISO 8601 UTC timestamp

**`report_count`** (integer, required)
- Number of video reports aggregated into this digest
- Min: 0 (digest can be empty for months with no reports)
- Example: `3`
- Validation: `report_count` >= 0 and equals sum of all `video_count` in `per_channel_breakdown`

---

### Verdict Breakdown (Reusable Object)

**`verdict_breakdown`** (object, required at top level and per-channel)

Verdict counts for the specified scope (overall or per-channel):

```json
{
  "True": 5,
  "Partially supported": 2,
  "Unverified": 1,
  "False": 1
}
```

**Field Definitions** (all integers, ≥ 0):
- **`True`**: Count of claims verified as True
- **`Partially supported`**: Count of claims verified as Partially supported (canonical term, replaces "overstated")
- **`Unverified`**: Count of claims that could not be verified
- **`False`**: Count of claims verified as False

**Validation**:
- All counts >= 0
- Sum of all counts equals total claims in the relevant scope (overall or per-channel)

---

### Per-Channel Breakdown (ChannelDigest)

**`per_channel_breakdown`** (array of ChannelDigest, required - Clarification Q3)

List of statistics by channel (sorted by channel_name). May be empty if report_count is 0.

#### ChannelDigest Object

```json
{
  "channel_name": "Financial Wisdom Daily",
  "channel_url": "https://youtube.com/@financialwisdom",
  "video_count": 2,
  "verdict_breakdown": {
    "True": 3,
    "Partially supported": 1,
    "Unverified": 0,
    "False": 0
  }
}
```

**Field Definitions**:

- **`channel_name`** (string, required):
  - Channel name from report metadata
  - Min length: 1, Max length: 100
  - UTF-8 encoded

- **`channel_url`** (string, required):
  - Canonical channel URL starting with https://
  - Must be a valid URL

- **`video_count`** (integer, required):
  - Number of videos from this channel published in the month
  - Min: 1 (only include channels with at least one video)
  - Validation: Sum of all video_count values must equal report_count

- **`verdict_breakdown`** (object, required):
  - Same VerdictBreakdown structure as root level
  - Counts for this channel's videos only
  - All counts >= 0

---

### Monetization Summary (MonetizationEntry Array)

**`monetization_summary`** (array of MonetizationEntry, required - Clarification Q3)

List of unique monetization disclosures found in the month (sorted by channel_name, then disclosure text). Omits entries for channels with no disclosures.

```json
[
  {
    "channel_name": "Financial Wisdom Daily",
    "disclosure": "This video is sponsored by InvestXYZ trading course ($199)"
  }
]
```

#### MonetizationEntry Object

- **`channel_name`** (string, required):
  - Name of the channel that had this disclosure
  - Min length: 1

- **`disclosure`** (string, required):
  - The monetization disclosure statement text
  - Min length: 1
  - Non-empty (null values excluded from summary)
  - Unique per (channel_name, disclosure) pair

---

## Validation Rules

### Schema-Level (Pydantic v2)

```python
from pydantic import BaseModel, Field, field_validator
from datetime import datetime
from typing import List

class VerdictBreakdown(BaseModel):
    True: int = Field(ge=0)
    Partially_supported: int = Field(ge=0, alias="Partially supported")
    Unverified: int = Field(ge=0)
    False: int = Field(ge=0)
    
    model_config = {"populate_by_name": True}

class ChannelDigest(BaseModel):
    channel_name: str = Field(min_length=1, max_length=100)
    channel_url: str = Field(pattern="^https://")
    video_count: int = Field(ge=1)
    verdict_breakdown: VerdictBreakdown

class MonetizationEntry(BaseModel):
    channel_name: str = Field(min_length=1)
    disclosure: str = Field(min_length=1)

class Digest(BaseModel):
    month: str = Field(pattern=r"^\d{4}-\d{2}$")
    generated_at: str  # Validate ISO 8601 format
    report_count: int = Field(ge=0)
    verdict_breakdown: VerdictBreakdown
    per_channel_breakdown: List[ChannelDigest] = Field(default_factory=list)
    monetization_summary: List[MonetizationEntry] = Field(default_factory=list)
    
    @field_validator("month")
    @classmethod
    def validate_month(cls, v):
        year, month = v.split("-")
        if not (1 <= int(month) <= 12):
            raise ValueError(f"Month must be 01-12, got {month}")
        return v
    
    @field_validator("report_count")
    @classmethod
    def validate_report_count(cls, v, info):
        per_channel = info.data.get("per_channel_breakdown", [])
        total_videos = sum(c.video_count for c in per_channel)
        if v != total_videos:
            raise ValueError(f"report_count ({v}) must equal sum of video_count ({total_videos})")
        return v
```

### Semantic Validation

1. **Month Validity**: Must be YYYY-MM with valid month (01-12)
2. **Report Count**: Must equal sum of all video_count in per_channel_breakdown
3. **Verdict Consistency**: All verdict counts >= 0
4. **Channel Uniqueness**: No duplicate channel_name in per_channel_breakdown array
5. **Monetization Uniqueness**: No duplicate (channel_name, disclosure) pairs in monetization_summary
6. **Monetization Deduplication**: Disclosures sorted by (channel_name, disclosure_text) for determinism
7. **Timestamp Format**: generated_at must be valid ISO 8601 UTC timestamp
8. **Ordering**: per_channel_breakdown sorted by channel_name; monetization_summary sorted by channel_name, then disclosure

---

## Examples

### Full Digest (2 Channels, Multiple Verdicts, Monetization - Clarification Q3)

```json
{
  "month": "2026-09",
  "generated_at": "2026-09-27T14:30:00Z",
  "report_count": 3,
  "verdict_breakdown": {
    "True": 5,
    "Partially supported": 2,
    "Unverified": 1,
    "False": 1
  },
  "per_channel_breakdown": [
    {
      "channel_name": "Financial Wisdom Daily",
      "channel_url": "https://youtube.com/@financialwisdom",
      "video_count": 2,
      "verdict_breakdown": {
        "True": 3,
        "Partially supported": 1,
        "Unverified": 0,
        "False": 0
      }
    },
    {
      "channel_name": "Stock Talk Pro",
      "channel_url": "https://youtube.com/@stocktalkpro",
      "video_count": 1,
      "verdict_breakdown": {
        "True": 2,
        "Partially supported": 1,
        "Unverified": 1,
        "False": 1
      }
    }
  ],
  "monetization_summary": [
    {
      "channel_name": "Financial Wisdom Daily",
      "disclosure": "This video is sponsored by InvestXYZ trading course ($199)"
    }
  ]
}
```

### Empty Digest (No Reports for Month)

```json
{
  "month": "2026-08",
  "generated_at": "2026-09-27T14:30:00Z",
  "report_count": 0,
  "verdict_breakdown": {
    "True": 0,
    "Partially supported": 0,
    "Unverified": 0,
    "False": 0
  },
  "per_channel_breakdown": [],
  "monetization_summary": []
}
```

### Single Channel Digest (No Monetization)

```json
{
  "month": "2026-09",
  "generated_at": "2026-09-27T14:30:00Z",
  "report_count": 2,
  "verdict_breakdown": {
    "True": 4,
    "Partially supported": 1,
    "Unverified": 1,
    "False": 0
  },
  "per_channel_breakdown": [
    {
      "channel_name": "SingleChannel",
      "channel_url": "https://youtube.com/@singlechannel",
      "video_count": 2,
      "verdict_breakdown": {
        "True": 4,
        "Partially supported": 1,
        "Unverified": 1,
        "False": 0
      }
    }
  ],
  "monetization_summary": []
}
```

---

## Backward Compatibility

**Version 1.1**: Updated per Clarification Q3 (June 2026)
- Changed `overall_verdict_breakdown` → `verdict_breakdown`
- Removed `verdict_count` (derive from verdict_breakdown if needed)
- Changed per-channel structure (removed `monetization_disclosures`, moved to root array)
- Changed monetization_summary from complex object to simple array
- Verdict field naming: "Partially supported/overstated" → "Partially supported"

**Version 1.x**: Consumers must ignore unknown fields (schema evolution strategy)

---

**Contract Version**: 1.1 | **Status**: Final (Updated 2026-09-27 per /speckit-clarify Q3)
