# Contract: Stored verdict record

```json
{
  "claim_id": "c_001",
  "claim_text": "…",
  "verdict": "True",
  "note": "…",
  "source_url": "https://…",
  "source_title": "…",
  "source_date": "2026-09-01",
  "search_query": "…",
  "fact_checked_at": "2026-10-14T18:00:00Z",
  "llm_model": "claude-haiku-4-5-20251001",
  "reasoning_cost": {"tokens_in": 0, "tokens_out": 0, "cost_usd": 0.0},
  "verified_by": "duckduckgo",
  "confidence": 0.92
}
```

- `verified_by` absent → must be re-checked.
- `confidence` may be null.
- Readers (API, digests, review) must accept reports without `verified_by` and `confidence` (older data).
