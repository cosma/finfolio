# Implementation Plan: Search Fallback and Claim Re-check

**Branch**: `fix/search-fallback-and-claim-cleanup` | **Date**: 2026-10-14 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/006-search-fallback/spec.md`

## Summary

Claims are verified with a free search source (DuckDuckGo, via the `ddgs` library) first. A verdict is accepted only when it is not Unverified and its confidence meets a configurable threshold (default 0.8). Otherwise the claim falls back to the paid source (Tavily). Any paid-search failure stops the fact-check run with exit code 2 and keeps the partial verdicts. Verdicts record `verified_by` and `confidence`. Verdicts without `verified_by` are re-checked. Storage cleanup removes empty-search Unverified verdicts. Most of this is already built; the plan records the design and adds the threshold setting (FR-012) and the removal of the report-level `search_provider` field (FR-014).

## Technical Context

**Language/Version**: Python 3.11+ (project `requires-python >=3.11`).

**Primary Dependencies**: `ddgs` 9.16.0 (new, free search), `langchain-community` Tavily tool (existing, paid search), `langchain-anthropic` (existing, verdict reasoning), Pydantic v2 (existing).

**Storage**: Per-video reports in `storage/reports/videos/{video_id}.json` (gitignored). Monthly digests in `storage/reports/monthly/`. No new storage.

**Testing**: pytest with `unittest.mock`. The shared `tests/conftest.py` blocks `.env` loading and stubs the DuckDuckGo search for every test (FR-011).

**Target Platform**: Single user, macOS, local CLI.

**Project Type**: CLI pipeline (`finfolio factcheck`, `finfolio report`) plus a one-time cleanup script.

**Performance Goals**: Not a stated goal (spec has none). Each claim costs one free search, plus one paid search only when the free source is not confident.

**Constraints**: Paid search credits are limited (1,000 free per month; pay as you go at $0.008 per credit). Free search has no key and no fixed quota, but it is an unofficial interface and can rate-limit. The LLM is called once per claim, plus once more when the free-source verdict is not accepted.

**Scale/Scope**: About 30 claims per video, 30–40 videos per month, so roughly 900–1,200 claims per month.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Note |
|---|---|---|
| I. Accuracy Over Speed | Pass | Claims with no source stay Unverified (FR-013). A search failure never becomes a verdict (FR-004). |
| II. No Financial Advice | Pass | Disclaimer unchanged. |
| III. Facts vs. Forecasts | Pass | Opinion and forecast claims are not searched (spec Assumptions). |
| IV. Transparency | Pass with note | Each verdict records its source (`verified_by`). The top-level provider field is removed, so the per-claim record is now the only one. |
| V. Monetization | Pass | Unchanged. |
| VI. Official YouTube API only | Pass | This feature does not touch YouTube data. The free search is a web source, not YouTube, so Principle VI does not apply. Note that `ddgs` uses unofficial endpoints; this is accepted for web search, not for YouTube. |
| VII. Resource & Cost Discipline | Gate: attention | Every claim not confirmed by the free source costs a second LLM call. Cost must stay observable (Principle VII says every LLM call is logged). Task to verify the cost tracker covers the verify path. |
| Dev workflow: TDD for fact-checking logic | Deviation | The verify and re-check logic was written before its tests, and the tests were added after. Recorded in Complexity Tracking. |
| Dev workflow: types & lint | Pass | mypy and ruff clean on the changed modules. |

**Gate result**: PASS with two items recorded: the cost-tracking check (Principle VII) and the TDD deviation.

## Project Structure

### Documentation (this feature)

```text
specs/006-search-fallback/
├── spec.md
├── plan.md                  # this file
├── research.md              # Phase 0 decisions
├── data-model.md            # Phase 1 entities
├── quickstart.md            # Phase 1 validation guide
├── contracts/
│   ├── cli-factcheck.md     # exit codes and messages
│   ├── search-chain.md      # internal search interface
│   └── verdict-record.md    # stored verdict fields
├── checklists/requirements.md
└── tasks.md                 # created later by /speckit-tasks
```

### Source Code (repository root)

```text
src/finfolio/
├── config.py                # + search_min_confidence (FINFOLIO_SEARCH_MIN_CONFIDENCE, default 0.8)
├── fact_checker.py          # verify_claim (chain), fact_check_claim (provider, confidence), loop, completed IDs
├── models.py                # VerdictModel + verified_by, confidence; verdict_needs_recheck; ReportModel without search_provider
├── storage.py               # list_pending_videos (re-check and missing-claim rules)
├── cli.py                   # factcheck: catches SearchError -> exit 2
├── llm/prompts.py           # verdict prompt asks for confidence
└── search/
    ├── errors.py            # SearchError, SearchQuotaError
    ├── ddg_client.py        # DuckDuckGoSearchClient (free, first in chain)
    └── tavily_client.py     # TavilySearchClient (paid, fallback; non-quota failures raise)

scripts/cleanup_claim_verdicts.py   # one-time cleanup, dry-run by default

tests/
├── conftest.py              # autouse: no .env, DuckDuckGo stubbed
├── unit/test_search_chain.py
├── unit/test_recheck.py
├── unit/test_search_quota.py
└── unit/test_cleanup_verdicts.py
```

**Structure Decision**: Search clients stay in `search/`, one per provider, behind the same result shape (`title`, `url`, `content`). The chain itself lives in `FactChecker.verify_claim`, so there is one place that decides the order and the acceptance rule.

## Design Decisions

1. **Free source first**: `ddgs` (`DDGS().text`), chosen because it needs no key and returns the same fields the prompt uses. Rejected: scraping HTML (not an official interface, and brittle).
2. **Acceptance rule**: accept a DuckDuckGo verdict only if it is not Unverified and its confidence is at or above the threshold. The confidence comes from the LLM, as a field in the verdict prompt.
3. **Threshold setting**: `FINFOLIO_SEARCH_MIN_CONFIDENCE`, default 0.8, validated to lie between 0 and 1. Read in `Config`, which already reads `FINFOLIO_*` values.
4. **Failure policy**: `SearchError` is the base; `SearchQuotaError` is a subclass for exhausted credits. Any paid-search failure stops the run. Free-search failures fall back to the paid source instead.
5. **Re-check marker**: a verdict with no `verified_by` is re-checked. This covers old Unverified verdicts and verdicts from failed or invalid LLM output. A verdict with `verified_by` is final.
6. **Invalid model output**: True or False without `source_url` is downgraded to Unverified with no `verified_by`, so it is re-checked and does not stop the run.
7. **Provider field**: `search_provider` is removed from `ReportModel` and from new reports (FR-014). The cleanup script also removes it from existing reports, so stored data matches the schema.
8. **Test isolation**: the shared fixture stops `.env` loading and stubs DuckDuckGo. Tests that exercise Tavily stub its search at the test level.

## Phase 0: Research

See [research.md](research.md).

## Phase 1: Design & Contracts

See [data-model.md](data-model.md), [contracts/](contracts/), and [quickstart.md](quickstart.md).

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|---|---|---|
| TDD not followed for the verify and re-check logic (Constitution Development Workflow) | The logic was built while the search and cost behavior were being investigated, and tests were written once the behavior was confirmed. | Rewriting the code test-first now would repeat work already verified against the live data. The tests now cover every rule in the spec. |
