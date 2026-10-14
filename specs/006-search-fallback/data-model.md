# Data Model: Search Fallback and Claim Re-check

## Verdict (stored in report `verdicts` list)

| Field | Type | Notes |
|---|---|---|
| `claim_id` | string | Reference to the claim in the video summary. |
| `claim_text` | string | Denormalized claim text. |
| `verdict` | True / Partially supported / Unverified / False | Canonical names only (FR-016 of spec 005). |
| `note` | string, max 250 chars | Explanation. |
| `source_url`, `source_title`, `source_date` | string or null | Required for True and False. |
| `search_query` | string | The claim text used for the search. |
| `fact_checked_at` | ISO 8601 UTC | When the verdict was produced. |
| `llm_model` | string | Model that produced the verdict. |
| `reasoning_cost` | object | `{tokens_in, tokens_out, cost_usd}`. |
| `verified_by` | `duckduckgo` / `tavily` / absent | **New.** Absent means the verdict must be re-checked (FR-006, FR-007). |
| `confidence` | number 0–1 or null | **New.** The model's confidence, clamped to [0, 1] (spec Edge Cases). |

**Validation rules**
- True or False requires `source_url` (existing rule; enforced in `VerdictModel`).
- `verified_by` is set only when the model reply was valid. A parse failure or a True/False without source leaves it absent.
- `confidence` is null when the model did not give a number.

## Report (stored in `storage/reports/videos/{video_id}.json`)

- `verdicts`: list of Verdict.
- `verdict_count`: `len(verdicts)`.
- `verdict_breakdown`: counts for the four canonical names.
- `search_provider`: **removed** from new reports (FR-014). Existing reports keep it until the cleanup script runs.

## Pending video (derived, not stored)

A video is pending when either:
1. it has a summary and no report, or
2. its report has a verdict with no `verified_by` and `verdict` Unverified, or
3. its report lacks a verdict for a checkable claim (not opinion or forecast) that exists in its summary.

## State transitions for a claim

```text
no verdict ──(verify)──> verdict with verified_by        (final)
no verdict ──(verify fails: paid search error)──> no verdict, run stops
Unverified, no verified_by ──(re-check)──> verdict with verified_by (replaces old)
verdict with verified_by, Unverified after both sources empty ──> final (FR-013)
```
