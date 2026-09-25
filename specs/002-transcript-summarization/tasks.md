# Tasks: Transcript Summarization Module

**Input**: Design documents from `/specs/002-transcript-summarization/`

**Prerequisites**: plan.md ✓, spec.md ✓, research.md ✓, data-model.md ✓, contracts/ ✓, quickstart.md ✓

**Organization**: Tasks grouped by user story to enable independent implementation and testing.

## Format: `[ID] [P?] [Story?] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story (US1, US2, US3, US4)
- All paths relative to repository root

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and dependencies

- [ ] T001 Add LangChain dependencies to pyproject.toml (langchain>=0.1.0, langchain-anthropic>=0.1.0, pydantic>=2.0, tiktoken)
- [ ] T002 [P] Create finfolio/summarizer_schema.py with Pydantic models: Claim, SummaryOutput (per data-model.md)
- [ ] T003 [P] Create finfolio/summarizer.py skeleton with imports and docstrings (LangChain integration to follow)
- [ ] T004 [P] Create tests/test_summarizer.py skeleton with test fixtures
- [ ] T005 [P] Create tests/test_summary_storage.py skeleton
- [ ] T006 [P] Create tests/test_summarizer_cli.py skeleton
- [ ] T007 Update .env.example with FINFOLIO_LLM_MODEL=claude-haiku-4-5-20251001 and ANTHROPIC_API_KEY=your-key
- [ ] T008 Verify pyproject.toml has [project.scripts] finfolio = "finfolio.cli:main" (already configured)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core storage and schema infrastructure

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [ ] T009 Extend finfolio/storage.py: add SUMMARIES_DIR constant = STORAGE_DIR / "summaries"
- [ ] T010 [P] Extend finfolio/storage.py: implement ensure_summaries_dir() function
- [ ] T011 [P] Extend finfolio/storage.py: implement has_summary(video_id: str) → bool
- [ ] T012 [P] Extend finfolio/storage.py: implement save_summary(video_id: str, summary: SummaryOutput) → None (atomic .tmp pattern)
- [ ] T013 [P] Extend finfolio/storage.py: implement get_summaries_dir() → Path
- [ ] T014 [P] Implement Pydantic models in finfolio/summarizer_schema.py:
  - [ ] Claim model with type (Enum), claim, quote, source_timestamp (optional), confidence_score (optional)
  - [ ] SummaryOutput model with summary, claims[], metadata dict
  - [ ] Add validation rules per data-model.md (length constraints, enum validation, timestamp format)
- [ ] T015 [P] Write integration tests for storage functions in tests/test_summary_storage.py:
  - [ ] Test save_summary() with atomic write (creates .tmp then renames)
  - [ ] Test has_summary() returns True/False correctly
  - [ ] Test ensure_summaries_dir() creates directory if missing
  - [ ] Test idempotency: saving same summary twice leaves identical file
- [ ] T016 [P] Write unit tests for Pydantic schemas in tests/test_summarizer_schema.py:
  - [ ] Test Claim validation passes with valid data
  - [ ] Test Claim validation fails with invalid type enum
  - [ ] Test SummaryOutput validation passes with valid structure
  - [ ] Test SummaryOutput validation fails with empty claims array
  - [ ] Test timestamp format validation (ISO8601)
- [ ] T017 Run pytest on Phase 2 tests: `uv run pytest tests/test_summary_storage.py tests/test_summarizer_schema.py -v`
- [ ] T018 Ensure all Phase 2 code passes type checking: `uv run mypy finfolio/summarizer_schema.py finfolio/storage.py`

**Checkpoint**: Storage layer ready, schema models validated, all tests passing

---

## Phase 3: User Story 1 - Summarize New Transcripts (Priority: P1) 🎯 MVP

**Goal**: Core functionality — read transcripts, call LLM, store summaries; idempotent processing

**Independent Test**: `uv run pytest tests/test_summarizer.py -v -k "test_summarize_new_transcript" && uv run finfolio summarize --help`

### Tests for User Story 1 ⚠️

- [ ] T019 [P] [US1] Write test_summarize_new_transcript() in tests/test_summarizer.py:
  - Verify summarization chain produces valid SummaryOutput
  - Verify output has non-empty summary and claims list
  - Verify output.metadata includes transcript_tokens, model, temperature, timestamp
- [ ] T020 [P] [US1] Write test_transcript_truncation() in tests/test_summarizer.py:
  - Create transcript exceeding 85k token threshold
  - Verify truncation happens and warning is logged
  - Verify summary still generated from truncated input
  - Verify metadata.transcript_truncated = True
- [ ] T021 [P] [US1] Write test_empty_transcript_rejected() in tests/test_summarizer.py:
  - Verify empty/whitespace-only transcript raises TranscriptTooShortError
  - Verify error is caught and logged, not crashes
- [ ] T022 [US1] Write test_idempotent_processing() in tests/test_summarizer_cli.py:
  - Create test transcript and run summarization once
  - Re-run summarization and verify no new files created
  - Verify file not modified (same timestamp, hash)

### Implementation for User Story 1

- [ ] T023 [US1] Implement core LangChain chain in finfolio/summarizer.py:
  - Function: summarize_transcript(transcript_text: str, video_id: str) → SummaryOutput
  - Implement RunnableSequence with PromptTemplate + ChatAnthropic + JsonOutputParser
  - Configure temperature=0.3 for summarization (per constitution)
  - Prompt instructs: extract summary (150-400 words) + claims (type, text, quote, timestamp, confidence)
  - Prompt instructs: exclude opinions/forecasts/advice, exclude sponsored content
  - Use model from env var FINFOLIO_LLM_MODEL (default: claude-haiku-4-5-20251001)
  - Parse LLM response as JSON, validate against SummaryOutput schema
  - Raise InvalidOutputError if validation fails
  - Type hints: transcript_text: str, video_id: str, return: SummaryOutput

- [ ] T024 [P] [US1] Implement token estimation in finfolio/summarizer.py:
  - Function: estimate_tokens(text: str) → int
  - Use tiktoken with Haiku tokenizer to estimate token count
  - Return conservative estimate (round up)

- [ ] T025 [P] [US1] Implement transcript validation in finfolio/summarizer.py:
  - Function: validate_transcript(transcript_text: str) → bool (or raise error)
  - Check: non-empty, min 50 characters (basic sanity)
  - Check: valid UTF-8 encoding
  - Raise TranscriptTooShortError if invalid

- [ ] T026 [US1] Implement transcript truncation in finfolio/summarizer.py:
  - Function: truncate_if_needed(transcript_text: str) → tuple[str, bool]
  - Estimate tokens; if > 85k, truncate to first 75% and return (truncated_text, True)
  - If ≤ 85k, return (text, False) unchanged
  - Log warning when truncation occurs: "transcript_truncated" event with original/truncated token counts

- [ ] T027 [US1] Implement cost logging in finfolio/summarizer.py:
  - Extract token counts from ChatAnthropic response.usage_metadata (input_tokens, output_tokens)
  - Calculate cost using Haiku rates: (input_tokens * 0.80 + output_tokens * 2.40) / 1_000_000 USD
  - Add cost_usd, input_tokens, output_tokens to SummaryOutput.metadata
  - Log structured JSON: {"event": "llm_call_complete", "video_id": "...", "cost_usd": 0.034, ...}

- [ ] T028 [US1] Implement retry with exponential backoff in finfolio/summarizer.py:
  - Wrap LLM call with retry logic: max 3 attempts
  - Backoff: 1s, 2s, 4s between retries
  - Catch TransientError (API timeouts, rate limits initially)
  - On rate limit (429): backoff but don't increment retry counter if within quota
  - Raise LLMAPIError after 3 failed attempts with error message
  - Log each retry: {"event": "lllm_retry", "attempt": N, "error": "..."}

- [ ] T029 [US1] Implement idempotency check in finfolio/summarizer.py:
  - Function: process_transcript_safe(video_id: str, transcript_text: str) → Optional[SummaryOutput]
  - Call has_summary(video_id); if True, return None (skip)
  - Otherwise: validate, truncate if needed, call summarize_transcript()
  - On success: call save_summary(video_id, output)
  - Return output
  - Handles atomic write via storage.save_summary()

- [ ] T030 [P] [US1] Write unit tests in tests/test_summarizer.py for all functions:
  - Test estimate_tokens() matches tiktoken
  - Test validate_transcript() accepts/rejects edge cases
  - Test truncate_if_needed() at various sizes
  - Test retry backoff timing
  - All tests should be deterministic and fast (< 5s total)

- [ ] T031 [US1] Run all User Story 1 tests: `uv run pytest tests/test_summarizer.py -v` (all should pass)
- [ ] T032 [US1] Type check User Story 1 code: `uv run mypy finfolio/summarizer.py`
- [ ] T033 [US1] Lint User Story 1 code: `uv run ruff check finfolio/summarizer.py`

**Checkpoint**: US1 core functionality complete; summarize_transcript() works end-to-end for single transcripts; idempotency verified

---

## Phase 4: User Story 2 - Separate Facts from Opinions (Priority: P1)

**Goal**: LLM extracts only verifiable factual claims; opinions/forecasts excluded from claims list

**Independent Test**: Test with mixed fact/opinion transcript; verify claims list contains only facts

### Tests for User Story 2 ⚠️

- [ ] T034 [P] [US2] Write test_facts_vs_opinions_separation() in tests/test_summarizer.py:
  - Transcript input: "Apple stock closed at $200. I think Apple will go to $400." (fact + opinion)
  - Verify claims[] includes "Apple stock closed at $200"
  - Verify claims[] does NOT include "I think Apple will go to $400"
  - Verify summary mentions both but claims are fact-only

- [ ] T035 [P] [US2] Write test_opinion_detection_phrases() in tests/test_summarizer.py:
  - Test phrases: "I believe", "I think", "in my opinion", "forecast", "bullish", "bearish"
  - Verify each is excluded from claims[] but included in summary

- [ ] T036 [P] [US2] Write test_claim_types_classification() in tests/test_summarizer.py:
  - Test LLM classifies claims correctly: number, date, deal, company-fact, product-fact
  - Verify each type has correct enum value

### Implementation for User Story 2

- [ ] T037 [US2] Refine LLM prompt in finfolio/summarizer.py for fact/opinion separation:
  - Update prompt template to include explicit instruction:
    ```
    "Extract ONLY verifiable factual statements into the claims list.
     Exclude opinions, forecasts, predictions, 'I believe', 'I think', 'my view is'.
     Each claim must be factually verifiable, not a statement of opinion or belief."
    ```
  - Add instruction for claim type classification: "Classify each claim as one of: number, date, deal, company-fact, product-fact"
  - Test with mock LLM response to verify prompt works

- [ ] T038 [US2] Add claim type validation in finfolio/summarizer_schema.py:
  - ClaimType enum: number, date, deal, company-fact, product-fact
  - Claim.type field uses this enum
  - Pydantic will validate at runtime

- [ ] T039 [P] [US2] Add source quote verification in finfolio/summarizer.py:
  - After LLM returns claims, verify each quote is substring of original transcript
  - If quote not found: log warning but keep claim (LLM may have paraphrased)
  - Add to metadata: quote_verification_errors (count)

- [ ] T040 [US2] Run User Story 2 tests: `uv run pytest tests/test_summarizer.py -v -k "opinion"` (all should pass)
- [ ] T041 [US2] Type check and lint: `uv run mypy finfolio/summarizer.py && uv run ruff check finfolio/summarizer.py`

**Checkpoint**: Facts/opinions correctly separated; claims list contains only verifiable statements; claim types classified

---

## Phase 5: User Story 3 - Invoke Summarization via CLI (Priority: P1)

**Goal**: CLI command `finfolio summarize` processes all pending transcripts with progress reporting

**Independent Test**: `uv run finfolio summarize` on test transcript directory; verify exit code 0, output shows processed count

### Tests for User Story 3 ⚠️

- [ ] T042 [P] [US3] Write test_cli_summarize_command() in tests/test_summarizer_cli.py:
  - Verify `finfolio summarize --help` displays usage
  - Verify command can be invoked without errors

- [ ] T043 [P] [US3] Write test_cli_batch_processing() in tests/test_summarizer_cli.py:
  - Create 2-3 test transcripts in storage/transcripts/
  - Run `finfolio summarize`
  - Verify all transcripts are processed (files created in storage/summaries/)
  - Verify exit code 0
  - Verify stdout contains JSON log entries with counts

- [ ] T044 [P] [US3] Write test_cli_error_handling() in tests/test_summarizer_cli.py:
  - Create empty transcript (invalid)
  - Run `finfolio summarize`
  - Verify error is logged but processing continues with next transcript
  - Verify exit code 0 (batch completed, some transcripts errored)
  - Verify error count reported in final summary

- [ ] T045 [US3] Write test_cli_exit_codes() in tests/test_summarizer_cli.py:
  - Exit code 0: success (at least some transcripts processed)
  - Exit code 1: critical error (config missing, no transcripts, API auth failed)
  - Verify codes returned correctly in each scenario

### Implementation for User Story 3

- [ ] T046 [US3] Extend finfolio/cli.py: add `summarize` command:
  - Function: @main.command("summarize")
  - Click options: `--config` (default: channels.yaml, optional), `--batch-size` (default: 100, limit files per run)
  - Load FINFOLIO_LLM_MODEL env var; default to claude-haiku-4-5-20251001
  - Load ANTHROPIC_API_KEY env var; raise error if missing
  - Call get_summaries_dir() to create storage/summaries/ if missing
  - Scan storage/transcripts/ for .txt files
  - For each transcript: call process_transcript_safe() (idempotency + summarization)
  - Track: processed_count, error_count, total_cost_usd, skipped_count
  - Log each event as structured JSON to stdout

- [ ] T047 [P] [US3] Implement batch loop in finfolio/cli.py:
  - For each transcript in transcripts_dir:
    - Load video_id from filename
    - Check has_summary(video_id); if True, increment skipped_count and continue
    - Load transcript text from file
    - Call process_transcript_safe(); if returns SummaryOutput, increment processed_count and add cost
    - On error: log error, increment error_count, continue (don't halt)
  - After loop: log final summary event with totals

- [ ] T048 [P] [US3] Implement progress logging in finfolio/cli.py:
  - Log at start: {"event": "summarization_start", "status": "success"}
  - Log per transcript: {"event": "transcript_processed", "video_id": "...", "claims_count": N, "cost_usd": X}
  - Log errors: {"event": "transcript_error", "video_id": "...", "error": "..."}
  - Log at end: {"event": "summarization_complete", "status": "success", "processed": N, "errors": N, "skipped": N, "total_cost_usd": X}
  - All logs to stdout as JSON (one per line)

- [ ] T049 [P] [US3] Implement exit code logic in finfolio/cli.py:
  - Exit 0: if processed_count > 0 or skipped_count > 0 (batch ran)
  - Exit 1: if error_count > 0 AND processed_count == 0 (all failed)
  - Exit 1: if config/API key missing, transcript dir missing, other critical errors
  - Use sys.exit(code) at end of command

- [ ] T050 [US3] Run User Story 3 CLI tests: `uv run pytest tests/test_summarizer_cli.py -v` (all should pass)
- [ ] T051 [US3] Manual CLI test:
  - Create test transcript in storage/transcripts/test-video.txt
  - Run `uv run finfolio summarize`
  - Verify output JSON, exit code, file created in storage/summaries/test-video.json
  - Run again; verify skipped (idempotent)
  - Delete summary file; run again; verify regenerated
- [ ] T052 [US3] Type check and lint CLI code: `uv run mypy finfolio/cli.py && uv run ruff check finfolio/cli.py`

**Checkpoint**: CLI command fully functional; batch processing works end-to-end; all 3 P1 user stories complete

---

## Phase 6: User Story 4 - Cost-Aware Summarization (Priority: P2)

**Goal**: Log cost of each LLM call; track spending across batch runs

**Independent Test**: Run summarization and verify cost metadata logged and accurate

### Tests for User Story 4 ⚠️

- [ ] T053 [P] [US4] Write test_cost_logging() in tests/test_summarizer.py:
  - Verify SummaryOutput.metadata includes cost_usd > 0
  - Verify cost_usd calculated from input/output tokens at correct rates
  - Test with known token counts and verify cost matches

- [ ] T054 [P] [US4] Write test_cost_reporting_in_cli() in tests/test_summarizer_cli.py:
  - Run summarization via CLI on test transcript
  - Verify JSON log includes "cost_usd" in transcript_processed event
  - Verify final summary log includes "total_cost_usd" (sum of all transcripts)

- [ ] T055 [P] [US4] Write test_cost_accuracy() in tests/test_summarizer.py:
  - Mock ChatAnthropic response with known token counts (e.g., 5000 input, 500 output)
  - Verify calculated cost = (5000 * 0.80 + 500 * 2.40) / 1_000_000
  - Within ±0.0001 USD (small margin for rounding)

### Implementation for User Story 4

- [ ] T056 [US4] Refine cost calculation in finfolio/summarizer.py:
  - After LLM call completes, extract response.usage_metadata (ChatAnthropic provides this)
  - Get: usage_metadata.input_tokens, output_tokens
  - Calculate: cost_usd = (input_tokens * 0.80 + output_tokens * 2.40) / 1_000_000
  - Add to SummaryOutput.metadata: input_tokens, output_tokens, cost_usd
  - Document rates: Haiku input $0.80/1M, output $2.40/1M (current as of 2024-Q3)

- [ ] T057 [US4] Add cost aggregation to CLI in finfolio/cli.py:
  - After processing each transcript: add cost_usd to total_cost_usd accumulator
  - Log cost per transcript in transcript_processed event
  - Report total_cost_usd in final summarization_complete event

- [ ] T058 [P] [US4] Add cost tracking to metadata in finfolio/summarizer.py:
  - Ensure all SummaryOutput.metadata includes: input_tokens, output_tokens, cost_usd, model, temperature, timestamp
  - Validate schema matches contracts/summary-output.schema.json

- [ ] T059 [US4] Run User Story 4 tests: `uv run pytest tests/test_summarizer.py -v -k "cost"` (all should pass)
- [ ] T060 [US4] Manual cost tracking test:
  - Run `uv run finfolio summarize` on test transcripts
  - Capture stdout logs; parse JSON
  - Sum all cost_usd values; verify matches final total_cost_usd
  - Verify costs are reasonable ($0.01-0.05 per transcript)

**Checkpoint**: Cost logging complete; accurate cost tracking per transcript and batch run

---

## Phase 7: Error Handling & Resilience (Cross-Cutting)

**Purpose**: Robust handling of edge cases and failures

- [ ] T061 [P] Implement LLM API error handling in finfolio/summarizer.py:
  - Catch anthropic.APIConnectionError: retry with backoff
  - Catch anthropic.RateLimitError (429): exponential backoff, don't count against retry limit if transient
  - Catch anthropic.APIStatusError: log error, mark transcript as failed
  - Catch json.JSONDecodeError (LLM output malformed): log error, mark as failed
  - Catch pydantic.ValidationError (output schema violation): log error, mark as failed
  - All errors logged with full context: {"event": "lllm_error", "video_id": "...", "error": "...", "attempt": N}

- [ ] T062 [P] Implement transcript validation in finfolio/summarizer.py:
  - Empty transcript check: skip with error log
  - Encoding check: decode UTF-8, handle UnicodeDecodeError
  - Size check: reject if > 1MB (text too large)
  - All validation errors logged with {"event": "transcript_validation_failed", "video_id": "...", "reason": "..."}

- [ ] T063 [P] Implement concurrent access safety in finfolio/storage.py:
  - Verify save_summary() uses atomic .tmp → rename pattern (already implemented in Phase 2)
  - Verify has_summary() is simple file existence check (no race conditions)
  - Document: Caller responsible for external coordination; this module handles file-level atomicity

- [ ] T064 [P] Write comprehensive error handling tests in tests/test_summarizer.py:
  - Test malformed LLM response (invalid JSON)
  - Test LLM response missing required fields
  - Test empty transcript
  - Test very large transcript (>1MB)
  - Test API connection error (mock and verify retry)
  - Test rate limit error (mock and verify backoff)
  - All tests should verify error is logged and gracefully handled

- [ ] T065 Run error handling tests: `uv run pytest tests/test_summarizer.py -v -k "error"` (all should pass)

---

## Phase 8: Polish & Cross-Cutting Concerns

**Purpose**: Final validation and quality assurance

- [ ] T066 [P] Run full test suite: `uv run pytest tests/ -v --cov=finfolio --cov-report=term-missing` (target: >80% coverage)
- [ ] T067 [P] Run type checking on entire codebase: `uv run mypy finfolio/ tests/`
- [ ] T068 [P] Run linting on entire codebase: `uv run ruff check finfolio/ tests/`
- [ ] T069 [P] Format code: `uv run ruff format finfolio/ tests/`

- [ ] T070 [P] Validate output schema compliance:
  - Run `uv run python3 -c "import json, jsonschema; schema = json.load(open('specs/002-transcript-summarization/contracts/summary-output.schema.json')); ..."` (verify schema valid)
  - Generate a summary; validate against schema using jsonschema library

- [ ] T071 Run quickstart.md validation scenarios:
  - Execute Scenario 1: Summarize New Transcript
  - Execute Scenario 2: Idempotency (Re-run)
  - Execute Scenario 3: Error Handling
  - Execute Scenario 4: Cost Monitoring
  - Verify all acceptance criteria pass

- [ ] T072 [P] Update documentation:
  - Update README.md if needed (add summarization section describing finfolio summarize command)
  - Add docstrings to all public functions in finfolio/summarizer.py
  - Add docstrings to all new CLI commands in finfolio/cli.py
  - Ensure all docstrings follow existing finfolio style (Google-style)

- [ ] T073 Final pre-commit validation:
  - Create git commit with all changes: `git add -A && git commit -m "feat: implement transcript summarization module"`
  - Run pre-commit hooks (if configured)
  - Verify all tests pass: `uv run pytest tests/ -v`
  - Verify types check: `uv run mypy finfolio/`
  - Verify linting passes: `uv run ruff check finfolio/`

- [ ] T074 Manual end-to-end validation:
  - Fresh clone/environment setup: `uv sync && source .env`
  - Run full summarization workflow: `uv run finfolio summarize`
  - Inspect output in storage/summaries/
  - Verify JSON files are valid and complete
  - Verify cost estimates are accurate
  - Test idempotency: run again, verify no new processing

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies → start immediately
- **Foundational (Phase 2)**: Depends on Setup → BLOCKS all user stories
- **User Stories (Phase 3-6)**: All depend on Foundational completion
  - US1, US2, US3 (all P1) can run in parallel after Foundational
  - US4 (P2) can start after Foundational but is lower priority
- **Polish (Phase 8)**: Depends on all user stories complete

### User Story Execution

1. **Complete Foundational (Phase 2)** — CRITICAL
2. **US1 + US2 + US3 can run in parallel** (all P1; no inter-dependencies)
3. **US4 sequential** (P2; can start after any P1 complete, but wait for Foundational)
4. **Polish once all stories complete**

### Within User Story (Example: US1)

1. Write tests first (T019-T022)
2. Run tests; verify FAIL (TDD)
3. Implement core function (T023)
4. Implement helpers (T024-T028)
5. Implement idempotency (T029)
6. Implement detailed tests (T030)
7. Run tests; verify PASS
8. Type check, lint, format

---

## Parallel Execution Examples

### Setup Phase (T001-T008)

```bash
# All marked [P] can run in parallel in parallel (different files):
- T002: Create finfolio/summarizer_schema.py
- T003: Create finfolio/summarizer.py skeleton
- T004: Create tests/test_summarizer.py skeleton
- T005: Create tests/test_summary_storage.py skeleton
- T006: Create tests/test_summarizer_cli.py skeleton

# Sequential: T001 (dependencies), then T002-T006 parallel, then T007-T008 (config)
```

### Foundational Phase (T009-T018)

```bash
# T009 is sequential (must add SUMMARIES_DIR const first)
# Then T010-T013 parallel (extend storage.py with different functions)
# Then T014 parallel (add validation to schema)
# Then T015-T016 parallel (write storage tests, write schema tests)
# Then T017-T018 sequential (run tests, verify)
```

### User Story 1 Phase (T019-T033)

```bash
# Tests (T019-T022): All [P] can run in parallel
# Implementation (T023): Sequential (core chain)
# Helpers (T024-T028): All [P] can run in parallel after T023
# Unit tests (T030): Sequential (depends on implementation)
# Validate (T031-T033): Sequential
```

### All User Stories in Parallel (after Foundational)

```bash
# After Phase 2 complete:
- Developer A: Phase 3 (US1) — T019-T033
- Developer B: Phase 4 (US2) — T034-T041
- Developer C: Phase 5 (US3) — T042-T052
- (Sequential): Phase 6 (US4) — T053-T060 (lower priority)
# All stories meet up in Phase 8 (Polish)
```

---

## Implementation Strategy

### MVP First (Recommended - Stops after Phase 5)

1. ✅ Complete Phase 1: Setup
2. ✅ Complete Phase 2: Foundational (CRITICAL)
3. ✅ Complete Phase 3: US1 (Summarize New Transcripts)
4. ✅ Complete Phase 4: US2 (Separate Facts from Opinions)
5. ✅ Complete Phase 5: US3 (Invoke Summarization via CLI)
6. **STOP and VALIDATE**: Run quickstart.md scenarios 1-3
7. ✅ **(OPTIONAL) Complete Phase 6: US4 (Cost-Aware Summarization)**
8. ✅ **(OPTIONAL) Complete Phase 8: Polish**

**MVP Scope**: Core summarization pipeline with idempotent CLI command and facts/opinions separation (P1 stories only)

### Incremental Delivery

- **Release 1** (MVP): Phase 1 + 2 + 3 + 5 → `finfolio summarize` works
  - Users can run batch summarization; transcripts processed in order; output stored
  - Still uses LLM but no cost tracking yet

- **Release 2** (Hardened): Add Phase 4 → Facts vs opinions separation verified
  - Same CLI command; output now has validated fact/opinion separation
  - Meets Constitution Principle III requirement

- **Release 3** (Observable): Add Phase 6 → Cost tracking enabled
  - Same CLI command; users can see cost of each transcript and total batch cost
  - Meets Constitution Principle VII requirement

- **Release 4** (Polish): Phase 8 → Documentation, edge cases, optimization
  - Same CLI command; higher test coverage, better error messages, etc.

---

## Checkpoint Validation

After each phase, verify:

- ✅ All tasks in phase checked off
- ✅ `uv run pytest tests/ -v` → all tests pass
- ✅ `uv run mypy finfolio/` → no type errors
- ✅ `uv run ruff check finfolio/` → no linting errors
- ✅ Manual test (e.g., `uv run finfolio summarize`) → works end-to-end

---

## Summary

**Total Tasks**: 74

**By Phase**:
- Phase 1 (Setup): 8 tasks
- Phase 2 (Foundational): 10 tasks
- Phase 3 (US1): 15 tasks
- Phase 4 (US2): 5 tasks
- Phase 5 (US3): 7 tasks
- Phase 6 (US4): 5 tasks
- Phase 7 (Error Handling): 5 tasks
- Phase 8 (Polish): 9 tasks

**By Story**:
- US1 (Summarize New Transcripts): 15 tasks
- US2 (Separate Facts from Opinions): 5 tasks
- US3 (Invoke Summarization via CLI): 7 tasks
- US4 (Cost-Aware Summarization): 5 tasks

**MVP Scope** (Phases 1-5, stopping before Phase 6): **52 tasks** → Core pipeline, idempotent, facts/opinions separation, CLI command

**Full Scope** (Phases 1-8): **74 tasks** → All above + cost tracking + error handling polish

**Suggested Start**: Phase 1 (Setup) + Phase 2 (Foundational) sequentially, then Phase 3-5 in parallel if team allows.

---

## Phase 9: Convergence (Gap Closure)

**Purpose**: Address remaining unimplemented phases and polish items identified by `/speckit-converge`

**Status**: MVP (Phases 1-3, 5) complete; Secondary phases (4, 6, 7, 8) require completion

- [ ] T075 [US2] Implement test_facts_vs_opinions_separation() in tests/test_summarizer.py per Phase 4 (US2/AC1) — verify LLM correctly separates factual claims from opinions
- [ ] T076 [P] [US2] Implement test_opinion_detection_phrases() in tests/test_summarizer.py per Phase 4 (US2/AC2) — verify phrases like "I think", "bullish", "forecast" excluded from claims
- [ ] T077 [P] [US2] Implement test_claim_types_classification() in tests/test_summarizer.py per Phase 4 (US2/AC3) — verify claim type enumeration (number, date, deal, company-fact, product-fact)
- [ ] T078 [US4] Implement cost aggregation in finfolio/cli.py per Phase 6 (US4/AC1) — track total_cost_usd across batch run and report in final summary
- [ ] T079 [US4] Add cost tracking to metadata per Phase 6 (US4/AC2) — ensure all SummaryOutput.metadata includes input_tokens, output_tokens, cost_usd
- [ ] T080 Implement comprehensive error handling tests in tests/test_summarizer.py per Phase 7 (E1-E5) — test malformed LLM response, connection errors, rate limits, validation failures, UTF-8 encoding errors
- [ ] T081 [P] Add transcript size validation edge case test per Phase 7 — test rejection of transcripts > 1MB
- [ ] T082 [P] Add concurrent access safety test in tests/test_summary_storage.py per Phase 7 — verify atomic .tmp pattern prevents race conditions
- [ ] T083 Run quickstart.md validation scenarios (T071) — execute all 7 scenarios manually against implementation to verify end-to-end correctness
- [ ] T084 Update README.md with summarization module documentation per Phase 8 (T072) — add section describing `finfolio summarize` command, usage, and examples
- [ ] T085 Final code cleanup per Phase 8 (T073) — ensure all mypy, ruff format, ruff check pass; all tests passing; >80% coverage on new modules
- [ ] T086 Manual end-to-end validation per Phase 8 (T074) — run full `uv run finfolio summarize` on real transcripts, verify JSON output, cost accuracy, idempotency

**Completion Status**: Append these 12 tasks to complete Phases 4, 6, 7, 8 and close MVP→Full scope gap

---

## Phase 10: Convergence (Dependency & Validation Closure)

**Purpose**: Resolve critical blockers (dependencies, spec compliance verification) and finalize implementation validation

**Status**: Implementation code exists but blockers prevent testing; spec compliance needs verification

### Critical Path (Blocking All Tests)

- [x] T087 Install LangChain dependencies to enable testing per F1 (missing) — run `uv sync` or `pip install langchain>=0.1.0 langchain-anthropic>=0.1.0 tiktoken>=0.5.0 anthropic` to resolve ModuleNotFoundError and enable test execution

- [x] T088 Audit and verify LLM prompt in finfolio/summarizer.py per F2 (partial) — ensure prompt template explicitly instructs: (a) exclude sponsored/promotional content ("brought you by", "sponsored by" sections), (b) separate factual claims from opinions/forecasts/predictions, (c) classify claims as number/date/deal/company-fact/product-fact per spec FR-007 & US2/AC1-AC2

- [x] T089 Update README.md with summarization module documentation per F5 (partial) — add section describing `finfolio summarize` command usage, options (--batch-size), output format (JSON), examples, and exit codes; reference quickstart.md for validation scenarios

- [x] T090 Execute end-to-end manual validation per F6 (partial) — run `finfolio summarize` on real test transcripts; verify (a) summary files created in storage/summaries/, (b) JSON output matches contracts/summary-output.schema.json, (c) metadata includes all required fields, (d) idempotency (re-run skips existing files), (e) cost calculations accurate

### Secondary (Spec Compliance Verification)

- [x] T091 [P] Verify facts vs opinions separation implementation per F3 (partial) — confirm finfolio/summarizer_schema.py has Claim.type enum with values (number, date, deal, company-fact, product-fact); test quote verification logic in summarizer.py matches T039 spec (verify claim quotes are substrings of original transcript)

- [x] T092 [P] Verify cost tracking metadata completeness per F4 (partial) — audit SummaryOutput.metadata in finfolio/summarizer.py; confirm all instances include: input_tokens, output_tokens, cost_usd (calculated at Haiku rates: $0.80/1M input, $2.40/1M output), model, temperature, timestamp per T056 spec

- [x] T093 [P] Implement comprehensive error handling edge case tests per F7 (partial) — add to tests/test_summarizer.py: (a) malformed JSON from LLM response, (b) rate limit retry logic (mock 429, verify backoff), (c) UTF-8 encoding errors, (d) transcript > 1MB rejection, (e) API connection timeouts per Phase 7 spec

- [x] T094 [P] Update task completion status in tasks.md per F8 (unrequested) — audit actual implementation against Phase 1-8 task descriptions; mark completed tasks with [x] to provide accurate tracking of work done (e.g., if T023-T030 summarizer functions implemented, mark [x])

### Validation & Handoff

- [x] T095 Run full test suite post-dependency-install per T087 — execute `pytest tests/ -v --cov=finfolio --cov-report=term-missing`; target >80% coverage on finfolio/summarizer.py and finfolio/cli.py

- [x] T096 Run type checking and linting per Phase 8 — execute `mypy finfolio/ tests/` and `ruff check finfolio/ tests/`; fix any errors or style violations

- [x] T097 Final convergence validation — verify all Phase 9-10 convergence tasks complete; all tests passing; all spec requirements (US1-US4, FR-001-FR-008, SC-001-SC-005) demonstrably met by code; constitution principles (I, III, VII) compliant

**Completion Status**: 11 tasks to resolve critical blockers (T087), verify spec compliance (T088-T094), and validate implementation (T095-T097)

