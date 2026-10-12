# Data Model: Monthly Digest Module

**Date**: 2026-09-27 | **Version**: 1.1 (Updated per /speckit-clarify Session 2026-09-27)

## Overview

The Monthly Digest module aggregates fact-checking reports from a given month into a summary document. This data model defines the entities involved in digest generation and storage, aligned with Clarifications Q3 (JSON schema).

---

## Core Entities

### 1. Digest (MonthlyDigest)

**Represents**: Aggregated fact-checking statistics for a single calendar month.

**Fields** (matches spec Digest Output Format):

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `month` | string (YYYY-MM) | Yes | ISO 8601 month in format YYYY-MM (e.g., "2026-09") |
| `generated_at` | ISO 8601 timestamp | Yes | UTC timestamp when digest was generated (UTC) |
| `report_count` | integer | Yes | Total number of reports (videos) included in digest (≥ 0) |
| `verdict_breakdown` | VerdictBreakdown | Yes | Aggregated counts across all videos in month |
| `per_channel_breakdown` | array[ChannelDigest] | Yes | Per-channel verdict statistics |
| `monetization_summary` | array[MonetizationEntry] | Yes | Unique monetization disclosures found in month |

**Validation Rules** (per Clarification Q3):
- `month` must match pattern `^\d{4}-\d{2}$` (YYYY-MM)
- `month` must be valid calendar month (01-12)
- `generated_at` must be ISO 8601 UTC timestamp
- `report_count` ≥ 0 and equals sum of all `video_count` in per_channel_breakdown
- Sum of verdict_breakdown counts equals total claims across all reports
- `per_channel_breakdown` must not have duplicate channel names
- `monetization_summary` must not have duplicate (channel_name, disclosure) pairs

**Constraints**:
- Digest file is immutable once written; regenerating a month overwrites the file (idempotent via atomic .tmp pattern)
- Digest represents a point-in-time snapshot of all reports for that month
- Empty months still generate a digest file with report_count=0 and empty arrays

---

### 2. VerdictBreakdown

**Represents**: Count of each verdict type (four canonical verdict categories).

**Fields**:

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `True` | integer | Yes | Count of verdicts marked "True" (≥ 0) |
| `Partially supported` | integer | Yes | Count of "Partially supported" verdicts (≥ 0) |
| `Unverified` | integer | Yes | Count of "Unverified" verdicts (≥ 0) |
| `False` | integer | Yes | Count of verdicts marked "False" (≥ 0) |

**Validation Rules**:
- All counts must be ≥ 0
- Sum of all counts equals the total verdict count in the digest
- Field names are canonical and consistent across all modules (Clarification Q3)

**Example**:
```json
{
  "True": 8,
  "Partially supported": 4,
  "Unverified": 2,
  "False": 1
}
```

---

### 3. ChannelDigest

**Represents**: Aggregated verdict statistics for a single channel within a digest.

**Fields** (per Clarification Q3):

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `channel_name` | string | Yes | Channel name (from report metadata) |
| `channel_url` | string | Yes | Channel URL (from report metadata, must be https://) |
| `video_count` | integer | Yes | Number of videos from this channel published in the month (≥ 1) |
| `verdict_breakdown` | VerdictBreakdown | Yes | Verdict counts specific to this channel's videos |

**Validation Rules**:
- `channel_name` must not be empty (1-100 chars)
- `channel_url` must start with https://
- `video_count` ≥ 1 (only include channels with at least one report)
- Sum of channel verdict_breakdown counts must equal total claims in that channel's videos

**Relationships**:
- Part of Digest.per_channel_breakdown array (one entry per channel with reports in month)
- Each channel appears exactly once in the array
- Aggregated from multiple Report entities with matching channel_name
- Ordered by channel_name for determinism

**Example**:
```json
{
  "channel_name": "FinancialAdvisor123",
  "channel_url": "https://youtube.com/@financialadvisor123",
  "video_count": 3,
  "verdict_breakdown": {
    "True": 5,
    "Partially supported": 2,
    "Unverified": 1,
    "False": 0
  }
}
```

---

### 4. MonetizationEntry

**Represents**: A unique monetization disclosure found in the month, associated with a channel.

**Fields** (per Clarification Q3):

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `channel_name` | string | Yes | Channel name that had this disclosure |
| `disclosure` | string | Yes | Text of the monetization disclosure from the video (non-empty) |

**Validation Rules**:
- `channel_name` must not be empty
- `disclosure` must not be empty or null
- Only included if channel has at least one report with non-null monetization_disclosure field
- Disclosures are deduplicated per (channel_name, disclosure_text) pair
- Array ordered deterministically (by channel_name, then disclosure_text)

**Example**:
```json
[
  {
    "channel_name": "FinancialAdvisor123",
    "disclosure": "Paid sponsorship from Fidelity"
  },
  {
    "channel_name": "MarketMaker456",
    "disclosure": "This video promotes CoinMarketCap Pro affiliate link."
  }
]
```

---

## Relationships

```
Digest
  ├─ verdict_breakdown: VerdictBreakdown (overall, all videos in month)
  ├─ per_channel_breakdown: ChannelDigest[] (one per unique channel)
  │   └─ verdict_breakdown: VerdictBreakdown (per-channel only)
  └─ monetization_summary: MonetizationEntry[] (unique channel-disclosure pairs)

Report (from Module 3 - input source, read-only)
  ├─ summary.metadata.publication_date (ISO 8601, determines month assignment)
  ├─ summary.metadata.channel_name (grouped by this)
  ├─ summary.metadata.channel_url (preserved in ChannelDigest)
  ├─ verdict_breakdown (summed into Digest verdicts)
  └─ monetization_disclosure (nullable, collected into monetization_summary)
```

---

## Data Flow: Report → Digest

**Input**: All files in `storage/reports/videos/*.json` with publication_date in target month

**Processing**:
1. Scan reports directory for JSON files
2. Load each report and extract:
   - `channel_name`, `channel_url`
   - `verdict_breakdown` counts
   - `monetization_disclosure` (if not null)
   - Publication date from embedded summary metadata
3. Filter reports to only those published in target month
4. Group by channel
5. Aggregate verdict counts (sum across all videos)
6. Collect and deduplicate monetization disclosures
7. Build ChannelStats for each channel
8. Build MonetizationSummary from collected disclosures
9. Construct MonthlyDigest and write to `storage/reports/monthly/{year}-{month}.json`

**Output**: Single digest file per month

---

## Storage Schema

**Location**: `storage/reports/monthly/{year}-{month}.json`

**Format**: Single JSON object per month (from Clarification Q3)

**Example (September 2026 with 2 channels, mixed verdicts, 3 reports)**:

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

## Backward Compatibility

**Version 1.0**: Initial release

Future extensions (e.g., monthly trends, year-over-year comparison) will add optional fields to MonthlyDigest. Consumers must ignore unknown fields (schema evolution).

---

**Document Version**: 1.0 | **Status**: Final
