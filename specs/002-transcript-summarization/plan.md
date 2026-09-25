# Implementation Plan: Transcript Summarization Module

**Branch**: `002-transcript-summarization` | **Date**: 2026-09-25 | **Spec**: `specs/002-transcript-summarization/spec.md`

**Input**: Feature specification from `/specs/002-transcript-summarization/spec.md`

## Summary

Build a LangChain-based summarization pipeline that reads unsummarized transcripts from `storage/transcripts/`, extracts plain-language summaries and discrete factual claims (separated from opinions/forecasts), and writes structured JSON to `storage/summaries/{video_id}.json`. Expose this via a CLI command `finfolio summarize`. Implement resilience (exponential backoff, retry on API failure), cost monitoring (log tokens and cost per call), and idempotent processing (skip existing summaries).

## Technical Context

**Language/Version**: Python 3.11+

**Primary Dependencies**: 
- LangChain & langchain-anthropic (LLM abstraction + Claude integration)
- pydantic (output schema validation)
- existing: click, pyyaml, python-dotenv

**Storage**: Filesystem (`storage/transcripts/` → `storage/summaries/`); JSON format per spec (summary, claims, metadata)

**Testing**: pytest + pytest-cov (existing test suite pattern)

**Target Platform**: Linux/macOS CLI (runs locally or in Docker)

**Project Type**: CLI tool / Python library

**Performance Goals**: 
- Process 50-minute transcript in under 1 minute (including LLM API call, parsing, JSON write)
- Cost per transcript: $0.01-0.05 USD with Haiku model

**Constraints**:
- Memory: 8 GB RAM host, 2 GB Docker VM — keep LangChain chain lightweight
- API quota: 10,000 units/day for YouTube (not applicable to this module; follows from Constitution Principle VII)
- LLM context window: Haiku ~100k tokens; truncate transcripts intelligently if needed
- Immutable summaries: once created, never updated (idempotent only)

**Scale/Scope**: ~20-30 videos/week; batch processing via CLI

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

✅ **Principle I (Accuracy Over Speed)**: Factual claims are extracted but NOT fact-checked here (fact-checking is module 3). This module separates claims from opinions per contract; downstream module owns verification.

✅ **Principle II (No Financial Advice)**: This module produces structured data only (summary + claims). Presentation/disclaimers are UI concerns, not this module.

✅ **Principle III (Facts vs. Forecasts Separation)**: **CORE REQUIREMENT** — LangChain chain explicitly separates factual claims from opinions/forecasts. Output schema enforces this via structured `claims[]` list (facts only).

✅ **Principle IV (Transparency About Method)**: Metadata in JSON includes `transcript_tokens`, `model`, `temperature`, `timestamp`. No fabrication.

✅ **Principle V (Monetization Awareness)**: Spec FR-008 requires filtering sponsored content. LLM prompt instructs exclusion of "brought you by" / "sponsored by" sections.

✅ **Principle VI (Reliability Over Cleverness)**: No custom web scraping; transcripts come from module 1 (youtube-transcript-api). No HTML parsing.

✅ **Principle VII (Resource & Cost Discipline)**: 
- ✅ **LangChain abstraction**: All LLM calls go through LangChain (no direct Claude API).
- ✅ **Model via config**: Model ID read from env var (`FINFOLIO_LLM_MODEL`, default `claude-haiku-4-5-20251001`), never hardcoded.
- ✅ **Cost monitoring**: Every LLM call logs tokens, model, estimated cost to stdout.
- ✅ **Temperature discipline**: Summarization uses `temperature = 0.3` per constitution (slight variation, deterministic).
- ✅ **Memory efficiency**: Single-pass chain, no caching of full transcripts in memory, use iterator/streaming if needed.

**GATE RESULT**: ✅ **PASS** — All principles satisfied by design. Principle III explicitly enforced by output schema. LangChain abstraction and cost monitoring baked into plan.

## Project Structure

### Documentation (this feature)

```text
specs/002-transcript-summarization/
├── spec.md              # Feature specification ✓
├── plan.md              # This file (architecture + design)
├── research.md          # Phase 0: LangChain patterns, output validation (generated below)
├── data-model.md        # Phase 1: Entity definitions, state machine (generated below)
├── contracts/
│   └── summary-output.schema.json  # Phase 1: JSON schema for storage/summaries/{video_id}.json
└── quickstart.md        # Phase 1: Validation scenarios, test commands (generated below)
└── tasks.md             # Phase 2: Implementation tasks (/speckit-tasks command)
```

### Source Code (repository root)

```text
finfolio/
├── __init__.py
├── cli.py                          # Extend: add `summarize` command
├── storage.py                      # Extend: add save_summary(), has_summary(), ensure_summaries_dir()
├── transcript_fetcher.py           # Existing (no changes)
├── youtube_client.py               # Existing (no changes)
├── config.py                       # Existing (no changes needed; env var lookup in main code)
├── summarizer.py                   # NEW: LangChain summarization pipeline
└── summarizer_schema.py            # NEW: Pydantic models for output validation

tests/
├── test_summarizer.py              # NEW: unit tests for extraction chain
├── test_summary_storage.py         # NEW: storage integration tests
└── test_summarizer_cli.py          # NEW: CLI command integration tests

storage/
├── transcripts/                    # Existing (input)
└── summaries/                      # NEW: output directory for {video_id}.json files
```

**Structure Decision**: Single-project Python package with minimal new modules. Summarizer logic isolated in `summarizer.py` with Pydantic schemas in `summarizer_schema.py` for clean separation of concerns. CLI extended in `cli.py` with new `summarize` subcommand. Storage layer extended with summary-specific methods following existing patterns.

## Complexity Tracking

No Constitution violations. No architectural complexity beyond the feature scope.

---

## Phase 0: Research & Decision Log

**Status**: ✅ Complete

**Research Output**: `research.md`

**Key Findings**:

1. **LangChain Architecture**: Use `LangChain RunnableSequence` with `JsonOutputParser` + Pydantic validation
2. **Cost Monitoring**: Leverage `ChatAnthropic` response metadata for token/cost logging; no external API calls needed
3. **Truncation Strategy**: Use `tiktoken` to estimate tokens; truncate at 85% of limit (safety margin); proceed with truncated input
4. **Sponsored Content**: Instruct LLM in prompt to exclude ads; no regex patterns needed
5. **Immutability**: Check-exists pattern for idempotency; user must manually delete to regenerate
6. **Configuration**: Model via env var `FINFOLIO_LLM_MODEL`, cost logging always-on
7. **Validation**: Pydantic models for runtime schema validation before storage

All research questions resolved. No blockers for Phase 1.

---

## Phase 1: Design & Contracts

**Status**: ✅ Complete

**Generated Artifacts**:

1. **`data-model.md`** — Entity definitions:
   - `Claim`: discrete factual statement (type, claim, quote, source_timestamp, confidence_score)
   - `Summary`: plain summary + claims[] + metadata (tokens, model, cost, timestamp)
   - Storage layout: `storage/transcripts/` → `storage/summaries/{video_id}.json`
   - State machine: per-transcript processing with retry/backoff logic
   - Concurrent access: idempotent via file-exists check + atomic rename

2. **`contracts/summary-output.schema.json`** — JSON Schema:
   - Validates structure and types for all Summary fields
   - Enforces: summary length, claims array size, metadata required fields
   - Integrates with Pydantic models for runtime validation

3. **`quickstart.md`** — Validation scenarios:
   - Scenario 1: Happy path (summarize new transcript)
   - Scenario 2: Idempotency (re-run skips existing)
   - Scenario 3: Error handling (invalid transcripts skipped)
   - Scenario 4: Cost monitoring & logging
   - Scenario 5: Large transcript truncation
   - Scenario 6: Facts vs. opinions separation
   - Scenario 7: CLI integration
   - Batch test: end-to-end run with multiple transcripts

**Constitution Re-check**: ✅ **PASS**

- ✅ Principle I: Claims extracted, not fact-checked here (module 3 owns verification)
- ✅ Principle III: Factual claims explicitly separated from opinions/forecasts in schema
- ✅ Principle VII: LangChain abstraction enforced, model via config, cost logging built-in
- All other principles satisfied by design

**Next Step**: `/speckit-tasks` to generate implementation task list (Phase 2)


