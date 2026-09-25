# Contract: Report JSON Schema

**Scope**: Structure and validation of fact-checking reports written to `storage/reports/videos/{video_id}.json`

---

## Schema (JSON Schema / Pydantic)

### Root: Report Object

```json
{
  "video_id": "dQw4w9WgXcQ",
  "title": "Apple Q3 Earnings Review",
  "channel_name": "FinancialAdvisor123",
  "channel_url": "https://youtube.com/@financialadvisor123",
  "source_url": "https://youtube.com/watch?v=dQw4w9WgXcQ",
  "transcript_source": "YouTube API",
  "fact_checked_at": "2026-09-25T15:30:46Z",
  "fact_check_duration_seconds": 45.2,
  "search_provider": "Tavily",
  "llm_model": "claude-haiku-4-5-20251001",
  "cost": {
    "search_usd": 0.02,
    "llm_usd": 0.01,
    "total_usd": 0.03
  },
  "summary": {
    "text": "...",
    "key_points": ["..."]
  },
  "verdicts": [...],
  "claim_count": 15,
  "verdict_count": 15,
  "verdict_breakdown": {
    "True": 8,
    "Partially supported/overstated": 4,
    "Unverified": 2,
    "False": 1
  },
  "disclaimer": "FinFolio reports facts and their accuracy. This is not financial advice.",
  "monetization_disclosure": null
}
```

---

## Field Definitions

### Metadata Fields

**`video_id`** (string, required)
- YouTube video ID (11 characters, alphanumeric)
- Pattern: `^[a-zA-Z0-9_-]{11}$`
- Example: `dQw4w9WgXcQ`

**`title`** (string, required)
- Video title from YouTube
- Min length: 1, Max length: 500
- UTF-8 encoded

**`channel_name`** (string, required)
- Channel name (not username)
- Min length: 1, Max length: 100

**`channel_url`** (string, required)
- Canonical channel URL
- Pattern: `https://youtube.com/@[a-zA-Z0-9_-]+`

**`source_url`** (string, required)
- Full YouTube video URL
- Pattern: `https://youtube.com/watch?v=[a-zA-Z0-9_-]{11}`

**`transcript_source`** (string, enum, required)
- How transcript was obtained
- Values: `"YouTube API"`, `"Manual"`
- Per Principle IV (Transparency)

---

### Fact-Checking Metadata

**`fact_checked_at`** (string, ISO 8601 timestamp, required)
- When fact-checking completed
- Format: `YYYY-MM-DDTHH:MM:SSZ` (UTC)
- Example: `2026-09-25T15:30:46Z`

**`fact_check_duration_seconds`** (number, required)
- Wall-clock time for fact-checking all claims
- Min: 0.1, Max: 3600 (1 hour)
- Includes I/O, search, and LLM reasoning

**`search_provider`** (string, enum, required)
- Search API provider
- Values: `"Tavily"` (only option in Phase 1)
- Extensible for future providers

**`llm_model`** (string, required)
- Model identifier used for verdict reasoning
- Example: `"claude-haiku-4-5-20251001"`
- Audit trail for model drift detection

---

### Cost Tracking

**`cost`** (object, required)

```json
{
  "search_usd": 0.02,
  "llm_usd": 0.01,
  "total_usd": 0.03
}
```

- **`search_usd`** (number, min: 0): Tavily search API costs
- **`llm_usd`** (number, min: 0): Claude API costs (sum of per-verdict reasoning costs)
- **`total_usd`** (number, min: 0): `search_usd + llm_usd`

**Validation**: `total_usd == search_usd + llm_usd` (must match exactly)

---

### Summary (Reference from Module 2)

**`summary`** (object, required)
- Denormalized copy of summary metadata from Module 2
- Contains `text` (full summary) and `key_points` (list of strings)
- Preserved for reporting context; not modified by fact-checking

---

### Verdicts

**`verdicts`** (array of Verdict objects, required)
- Empty array if no claims, otherwise one Verdict per claim
- Ordered as extracted from summary

#### Verdict Object

```json
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
```

**Field Definitions**:

- **`claim_id`** (string, required): Unique ID from summary (e.g., `claim_001`)
- **`claim_text`** (string, required): Full claim statement (denormalized for readability)
- **`verdict`** (string, enum, required):
  - `"True"`: Claim verified by sources
  - `"Partially supported/overstated"`: Core accurate but exaggerated
  - `"Unverified"`: No sources found or search timed out
  - `"False"`: Contradicted by sources
- **`note`** (string, required): 1-2 sentences explaining verdict (min: 1, max: 250 characters)
- **`source_url`** (string or null):
  - Required if verdict is `"True"` or `"False"`
  - Optional if verdict is `"Unverified"` or `"Partially supported"`
  - HTTP(S) URL format
- **`source_title`** (string or null): Publication/page title from source snippet
- **`source_date`** (string, ISO 8601 date, or null):
  - Format: `YYYY-MM-DD`
  - Publication date from source; null if unavailable
- **`search_query`** (string, required): Query sent to Tavily (denormalized for debugging)
- **`fact_checked_at`** (string, ISO 8601 timestamp, required): When this verdict was assigned
- **`llm_model`** (string, required): Model used for verdict (audit trail)
- **`reasoning_cost`** (object, required):
  - **`tokens_in`** (integer, min: 0): Input tokens (search results + prompt)
  - **`tokens_out`** (integer, min: 0): Output tokens (verdict + reasoning)
  - **`cost_usd`** (number, min: 0): Cost for this verdict in USD

---

### Counts & Breakdown

**`claim_count`** (integer, required)
- Total claims from summary
- Min: 0
- Example: `15`

**`verdict_count`** (integer, required)
- Verdicts assigned (may be < claim_count if some claims are opinions)
- Min: 0, Max: claim_count
- Example: `15`

**`verdict_breakdown`** (object, required)
```json
{
  "True": 8,
  "Partially supported/overstated": 4,
  "Unverified": 2,
  "False": 1
}
```

**Validation**: 
- Each key must be one of the four verdict types
- Sum must equal `verdict_count`
- All values >= 0

---

### Disclaimer & Disclosure

**`disclaimer`** (string, fixed, required)
- Per Principle II (No Financial Advice)
- **Fixed text** (must not vary): `"FinFolio reports facts and their accuracy. This is not financial advice."`
- Always present in report; never modified

**`monetization_disclosure`** (string or null, optional)
- Per Principle V (Monetization Awareness)
- If present, states fact of promotion without judgment
- Example: `"This video promotes an affiliate link to CoinMarketCap Pro."`
- Null if no monetization detected

---

## Validation Rules

### Schema-Level

```python
class ReportModel(BaseModel):
    video_id: str = Field(..., pattern=r"^[a-zA-Z0-9_-]{11}$")
    title: str = Field(..., min_length=1, max_length=500)
    channel_name: str = Field(..., min_length=1, max_length=100)
    channel_url: str = Field(..., pattern=r"^https://youtube\.com/@[a-zA-Z0-9_-]+$")
    source_url: str = Field(..., regex=r"^https://youtube\.com/watch\?v=[a-zA-Z0-9_-]{11}$")
    transcript_source: Literal["YouTube API", "Manual"]
    fact_checked_at: str  # Validate ISO 8601
    fact_check_duration_seconds: float = Field(..., gt=0, le=3600)
    search_provider: Literal["Tavily"]
    llm_model: str = Field(..., min_length=1)
    cost: CostModel
    summary: dict  # Flexible; denormalized from Module 2
    verdicts: list[VerdictModel]
    claim_count: int = Field(..., ge=0)
    verdict_count: int = Field(..., ge=0, le=100)  # Conservative max
    verdict_breakdown: dict  # Keys: verdict types; values: counts
    disclaimer: str  # Must equal exact fixed text
    monetization_disclosure: str | None = None
    
    @validator("verdict_count")
    def verdict_count_le_claim_count(cls, v, values):
        if v > values.get("claim_count", 0):
            raise ValueError("verdict_count cannot exceed claim_count")
        return v
    
    @validator("disclaimer")
    def disclaimer_fixed_text(cls, v):
        expected = "FinFolio reports facts and their accuracy. This is not financial advice."
        if v != expected:
            raise ValueError(f"disclaimer must be: {expected}")
        return v
    
    @validator("cost")
    def cost_total_matches(cls, v):
        if abs(v.total_usd - (v.search_usd + v.llm_usd)) > 1e-6:
            raise ValueError("cost.total_usd must equal search_usd + llm_usd")
        return v
```

### Semantic

1. **Verdict Consistency**: Verdicts with `verdict="True"` or `verdict="False"` must have `source_url` set
2. **Verdict Breakdown**: Counts must sum to `verdict_count`
3. **Cost Monotonicity**: `search_usd >= 0` and `llm_usd >= 0`
4. **Timestamp Order**: `fact_checked_at` should be recent (within last 24 hours recommended for freshness)

---

## Examples

### Full Report (3 Claims, Mixed Verdicts)

See `data-model.md` "Storage Schema" section for a complete example.

### Minimal Report (0 Claims)

```json
{
  "video_id": "abc123XYZ",
  "title": "Empty Video",
  "channel_name": "Test",
  "channel_url": "https://youtube.com/@test",
  "source_url": "https://youtube.com/watch?v=abc123XYZ",
  "transcript_source": "YouTube API",
  "fact_checked_at": "2026-09-25T15:30:00Z",
  "fact_check_duration_seconds": 0.5,
  "search_provider": "Tavily",
  "llm_model": "claude-haiku-4-5-20251001",
  "cost": {"search_usd": 0.0, "llm_usd": 0.0, "total_usd": 0.0},
  "summary": {"text": "", "key_points": []},
  "verdicts": [],
  "claim_count": 0,
  "verdict_count": 0,
  "verdict_breakdown": {"True": 0, "Partially supported/overstated": 0, "Unverified": 0, "False": 0},
  "disclaimer": "FinFolio reports facts and their accuracy. This is not financial advice.",
  "monetization_disclosure": null
}
```

---

## Backward Compatibility

**Version 1.0** (Phase 1 design):
- No prior versions; first release
- Future extensions (e.g., multi-source verdicts) will bump to 1.1 with new optional fields
- Consumers must ignore unknown fields (schema evolution)

---

**Contract Version**: 1.0 | **Status**: Final
