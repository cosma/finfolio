# Phase 1 Design: Data Model & Entities

**Date**: 2026-09-25 | **Status**: Complete

## Entity Definitions

### Claim

**Purpose**: Discrete, verifiable factual statement extracted from transcript, separated from opinions.

**Fields**:
| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `type` | Enum | Yes | `number`, `date`, `deal`, `company-fact`, `product-fact` |
| `claim` | string | Yes | The factual statement itself (1-2 sentences) |
| `quote` | string | Yes | Exact source text from transcript (the evidence) |
| `source_timestamp` | string | No | Video timestamp HH:MM:SS where claim was spoken |
| `confidence_score` | float | No | 0.0-1.0; LLM confidence that this is factual (not opinion) |

**Validation Rules**:
- `type` must be one of the five enum values (case-insensitive)
- `claim` must be non-empty and under 500 characters
- `quote` must be a substring of the original transcript
- `source_timestamp` if present must match regex `^\d{1,2}:\d{2}:\d{2}$`
- `confidence_score` if present must be 0.0 ≤ x ≤ 1.0

**Example**:
```json
{
  "type": "number",
  "claim": "Apple released the iPhone 15 Pro in September 2023",
  "quote": "Apple released the iPhone 15 Pro in September 2023",
  "source_timestamp": "12:34:00",
  "confidence_score": 0.98
}
```

---

### Summary

**Purpose**: Plain-language summary + structured claims extracted from a video transcript.

**Fields**:
| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `summary` | string | Yes | 150-400 word plain-language summary of key insights |
| `claims` | array[Claim] | Yes | List of discrete factual claims (3-15 typical) |
| `metadata` | object | Yes | Processing metadata (see below) |

**Metadata Fields**:
| Field | Type | Notes |
|-------|------|-------|
| `transcript_tokens` | int | Estimated token count of input transcript |
| `model` | string | LLM model used (e.g., `claude-haiku-4-5-20251001`) |
| `temperature` | float | Temperature parameter used (e.g., 0.3) |
| `timestamp` | ISO8601 | UTC timestamp when summary was generated |
| `cost_usd` | float | Estimated cost of this LLM call in USD |
| `input_tokens` | int | LLM input token count |
| `output_tokens` | int | LLM output token count |
| `transcript_truncated` | bool | True if input was truncated due to context length |

**Validation Rules**:
- `summary` must be 150-400 words (count words naively; 3000-6000 characters typical)
- `claims` must not be empty (at least 1 claim)
- All Claim objects in claims array must pass Claim validation
- `metadata.timestamp` must be valid ISO8601 with timezone
- `metadata.cost_usd` must be ≥ 0

**Example**:
```json
{
  "summary": "The guest discussed three key investment themes: AI chip manufacturers' supply constraints, the emerging role of energy stocks in ESG-compliant portfolios, and recent M&A activity in fintech. They recommended focusing on semiconductor companies with 5-year runways, while cautioning against overpaying for software-as-a-service deals.",
  "claims": [
    {
      "type": "date",
      "claim": "AMD announced new 7nm chip process in Q3 2025",
      "quote": "AMD announced new 7nm chip process in Q3 2025",
      "source_timestamp": "05:20:00",
      "confidence_score": 0.95
    },
    {
      "type": "number",
      "claim": "Tech sector P/E ratio reached 22x in 2025",
      "quote": "Tech sector P/E is running at 22 times earnings",
      "source_timestamp": "08:15:00",
      "confidence_score": 0.87
    }
  ],
  "metadata": {
    "transcript_tokens": 8524,
    "model": "claude-haiku-4-5-20251001",
    "temperature": 0.3,
    "timestamp": "2026-09-25T14:30:00Z",
    "cost_usd": 0.034,
    "input_tokens": 8500,
    "output_tokens": 612,
    "transcript_truncated": false
  }
}
```

---

## Storage & State

### File Layout

```
storage/
├── transcripts/
│   ├── dQw4w9WgXcQ.txt      # Input: raw transcript text
│   ├── jNQXAC9IVRw.txt
│   └── ...
├── summaries/
│   ├── dQw4w9WgXcQ.json     # Output: Summary object (see above)
│   ├── jNQXAC9IVRw.json
│   └── ...
└── .finfolio-state.json     # Existing: channel fetch state (unchanged)
```

### Concurrent Access

**Race Condition Handling**:
1. Check if `storage/summaries/{video_id}.json` exists at start of summarization
2. If it exists: skip this transcript (idempotent, no race condition)
3. If two processes check simultaneously: both see file missing, both attempt to write
   - **Mitigation**: Use atomic rename pattern (write to `.tmp`, then `rename()`)
   - Winner's file persists; loser's `.tmp` is left behind (cleanup on next run)
4. **Caller's Responsibility**: External orchestration (cron, systemd) should not schedule concurrent `finfolio summarize` runs on the same transcript

**Idempotency Contract**:
- Running `finfolio summarize` twice with same input → identical output files
- No duplicates created
- No existing files modified (immutability)

---

## Operational State Machine

**Per-Transcript Processing**:

```
START
  ↓
CHECK_EXISTS: Does storage/summaries/{video_id}.json exist?
  ├─ YES → SKIP (idempotent)
  └─ NO → READ_TRANSCRIPT
           ↓
           VALIDATE_TRANSCRIPT: Non-empty, reasonable size?
             ├─ INVALID → FAIL_LOG (error), NEXT_TRANSCRIPT
             └─ VALID → ESTIMATE_TOKENS
                         ↓
                         TRUNCATE_CHECK: Token count > 85k?
                           ├─ YES → TRUNCATE (log warning)
                           └─ NO → USE_FULL_TRANSCRIPT
                                   ↓
                                   CALL_LLM (with exponential backoff, 3 retries)
                                     ├─ SUCCESS → PARSE_OUTPUT
                                     │             ↓
                                     │             VALIDATE_OUTPUT
                                     │               ├─ VALID → WRITE_JSON (atomic), LOG_COST, SUCCESS_LOG
                                     │               └─ INVALID → FAIL_LOG (malformed output)
                                     ├─ RATE_LIMITED → BACKOFF_AND_RETRY (exponential)
                                     │                  └─ (after 3 retries) → FAIL_LOG (rate limit)
                                     └─ ERROR → BACKOFF_AND_RETRY (exponential)
                                                  └─ (after 3 retries) → FAIL_LOG (API error)
                           ↓
                           NEXT_TRANSCRIPT
```

**Batch Run State**:

```
START_BATCH
  ↓
FIND_UNSUMMARIZED: Scan storage/transcripts/, skip if storage/summaries/{id}.json exists
  ↓
PROCESS_EACH (for each unsummarized transcript)
  └─ (see per-transcript state machine above)
     ├─ SUCCESS → COUNT++, LOG_PROGRESS, LOG_COST
     └─ FAILURE → ERROR_COUNT++, LOG_ERROR, CONTINUE
  ↓
REPORT_BATCH: stdout {transcripts_processed, errors, total_cost_usd}
  ↓
END_BATCH
```

---

## API Boundary

**Input Contract** (to `summarizer.py`):
- `transcript_id` (str): video_id or identifier
- `transcript_text` (str): full transcript text

**Output Contract** (from `summarizer.py`):
- Returns: `Summary` object (Pydantic model)
- Raises: `TranscriptTooLongError`, `LLMAPIError`, `InvalidOutputError`

**Storage API** (new methods in `finfolio/storage.py`):

```python
def save_summary(video_id: str, summary: Summary) -> None:
    """Save Summary object to storage/summaries/{video_id}.json atomically."""

def has_summary(video_id: str) -> bool:
    """Check if storage/summaries/{video_id}.json exists."""

def ensure_summaries_dir() -> None:
    """Create storage/summaries/ if missing."""

def get_summaries_dir() -> Path:
    """Return Path to storage/summaries/ directory."""
```

---

## Dependencies

**Production**:
- `langchain>=0.1.0` (LLM abstraction)
- `langchain-anthropic>=0.1.0` (Claude integration)
- `pydantic>=2.0` (schema validation)
- `tiktoken` (token estimation for truncation detection)

**Development/Testing**:
- `pytest>=7.4.0` (existing)
- `pytest-cov>=4.1.0` (existing)
- `mypy>=1.5.0` (existing; will type-check new modules)

