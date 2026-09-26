# Tasks: Fact-Checking Module (003)

**Input**: Design documents from `/specs/003-fact-checking-module/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/, quickstart.md

**Organization**: Tasks grouped by user story (US1, US2, US3) to enable independent implementation and testing.

**Testing**: Test-first approach per Constitution (write tests before implementation). Tests are mandatory for fact-checking logic per Principle I.

---

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies on incomplete work)
- **[Story]**: User story this belongs to (US1, US2, US3) — omitted for Setup/Foundational/Polish phases
- All paths are absolute or project-relative from repository root

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and dependency management

- [ ] T001 Create directory structure: `src/finfolio/llm/`, `src/finfolio/search/`, `tests/unit/`, `tests/integration/`
- [ ] T002 Update `pyproject.toml` to add LangChain, Tavily, Pydantic dependencies (keep CPU-only, avoid heavy ML libs per CLAUDE.md)
- [ ] T003 [P] Create `src/finfolio/__init__.py` with version and module exports
- [ ] T004 [P] Create empty module files: `src/finfolio/models.py`, `src/finfolio/fact_checker.py`, `src/finfolio/cli.py`, `src/finfolio/search/tavily_client.py`

**Checkpoint**: Dependencies installable, module structure ready for Phase 2

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure and models that all user stories depend on

**⚠️ CRITICAL**: No user story work can begin until Phase 2 is complete. This phase establishes:
- Data model schemas (Claim, Verdict, Report)
- Storage API extensions (save_report, has_report)
- LangChain integration foundation
- Cost monitoring setup

### Data Models (Pydantic Schemas)

- [ ] T005 [P] Create `ClaimModel` Pydantic class in `src/finfolio/models.py` with fields: id, text, quote, type, confidence, timestamp, is_opinion, is_forecast; add validation for timestamp format (MM:SS / HH:MM:SS)
- [ ] T006 [P] Create `VerdictModel` Pydantic class in `src/finfolio/models.py` with fields: claim_id, claim_text, verdict (enum), note, source_url, source_title, source_date, search_query, fact_checked_at, llm_model, reasoning_cost
- [ ] T007 [P] Create `ReportModel` Pydantic class in `src/finfolio/models.py` with fields: video_id, title, channel_name, channel_url, source_url, transcript_source, fact_checked_at, fact_check_duration_seconds, search_provider, llm_model, cost, summary, verdicts, claim_count, verdict_count, verdict_breakdown, disclaimer, monetization_disclosure; add validator to ensure disclaimer is exact fixed text per Principle II
- [ ] T008 [P] Create `CostModel` nested Pydantic class with fields: search_usd, llm_usd, total_usd; add validator that `total_usd == search_usd + llm_usd`
- [ ] T009 Create unit tests for Pydantic models in `tests/unit/test_models.py`: test schema validation, test field constraints, test enum validation

### Storage API Extensions

- [ ] T010 [P] Extend `src/finfolio/storage.py` with `save_report(video_id: str, report_data: dict) -> None` function: write via atomic .tmp pattern, validate report_data against ReportModel before write, create `storage/reports/videos/` directory if missing
- [ ] T011 [P] Extend `src/finfolio/storage.py` with `has_report(video_id: str) -> bool` function: check if report exists at `storage/reports/videos/{video_id}.json`, return False if dir missing (log warning)
- [ ] T012 [P] Extend `src/finfolio/storage.py` with `load_summary(video_id: str) -> dict | None` function: load from `storage/summaries/{video_id}.json`, return None if missing, raise ValueError if JSON invalid
- [ ] T013 [P] Extend `src/finfolio/storage.py` with `list_pending_videos() -> list[str]` function: scan `storage/summaries/`, return video_ids without corresponding reports in `storage/reports/videos/`
- [ ] T014 Create unit tests for storage functions in `tests/unit/test_storage.py`: test has_report (missing/exists), test save_report (atomic write), test load_summary (missing/exists/invalid), test list_pending_videos

### LangChain Integration Foundation

- [ ] T015 Create `src/finfolio/llm/__init__.py` with LangChain imports and cost tracking setup
- [ ] T016 Create `src/finfolio/llm/cost_tracking.py`: implement LangChain callback handler to track tokens (input, output) and costs per LLM call; log to structured JSON (timestamp, model, tokens_in, tokens_out, cost_usd)
- [ ] T017 Create `src/finfolio/llm/prompts.py`: define prompt templates for verdict reasoning (input: claim, search results; output: verdict, note, reasoning); use Jinja2 or f-string templates
- [ ] T018 Create `src/finfolio/search/__init__.py` with Tavily initialization
- [ ] T019 Create `src/finfolio/search/tavily_client.py`: implement wrapper for TavilySearchResults tool; handle API key from env var; include error handling for timeouts, quota exhausted, no results

### Configuration & Logging

- [ ] T020 [P] Create `src/finfolio/config.py`: define Config dataclass with fields: storage_dir, llm_model (default: claude-haiku-4-5-20251001), tavily_api_key, anthropic_api_key, search_timeout_seconds (default: 10), log_level (default: INFO); read from env vars
- [ ] T021 [P] Create `src/finfolio/logging_utils.py`: setup structured JSON logging (timestamp, level, message, event_data); export configure_logging(level: str) function
- [ ] T022 Create integration test `tests/integration/test_foundation.py`: verify Config loads correctly, verify LangChain callbacks initialize, verify Tavily client can be instantiated

**Checkpoint**: Foundation ready. All models, storage functions, LangChain hooks, and config in place. No API calls yet. Ready for user story implementation.

---

## Phase 3: User Story 1 - Fact-Check Extracted Claims (Priority: P1) 🎯

**Goal**: Implement core fact-checking pipeline: load claims from summary, search for each claim, assign verdicts, generate report.

**Independent Test**: Single video can be fact-checked end-to-end; report is created with verdicts for all claims.

**Acceptance Criteria**:
- Given a video has extracted claims in `storage/summaries/{video_id}.json`
- When `finfolio factcheck --video-id {video_id}` runs
- Then a report is created at `storage/reports/videos/{video_id}.json` with verdicts for each claim

### Tests for User Story 1 (Test-First)

> Write these tests FIRST; they MUST FAIL before implementation

- [ ] T023 [P] [US1] Create unit test `tests/unit/test_fact_checker_verdict.py`: test verdict assignment logic with mocked search results (True verdict, False verdict, Partially supported verdict, Unverified verdict); verify verdict output matches expected type; verify note is non-empty
- [ ] T024 [P] [US1] Create unit test `tests/unit/test_fact_checker_claim_skip.py`: test that opinion claims are skipped (is_opinion=True); test that forecast claims are marked but not fact-checked; verify no verdict created for skipped claims
- [ ] T025 [P] [US1] Create integration test `tests/integration/test_fact_check_single_video.py`: load fixture summary with 3 claims (1 True, 1 False, 1 Unverified); mock Tavily search results; run fact_check(video_id); verify report created; verify 3 verdicts; verify verdict_breakdown correct
- [ ] T026 [P] [US1] Create contract test `tests/contract/test_report_schema.py`: generate sample report; validate against ReportModel schema; verify disclaimer present; verify cost fields populated; verify verdict breakdown sums correctly

### Implementation for User Story 1

- [ ] T027 Create `src/finfolio/fact_checker.py`: main FactChecker class with:
  - `__init__(config: Config)`: initialize LangChain LLM (Claude Haiku via ChatAnthropic, temperature=0), Tavily tool, cost tracker
  - `fact_check_claim(claim: ClaimModel, search_results: list) -> VerdictModel`: use LLM + prompt to synthesize verdict from claim and search results; return VerdictModel with all fields populated
  - `build_llm_agent()`: create LangChain tool-calling agent with Tavily search tool and verdict reasoning capability
  - Proper error handling: log exceptions, don't crash on single claim failure

- [ ] T028 [P] [US1] Create `src/finfolio/fact_checker.py` helper: `extract_claims_from_summary(summary: dict) -> list[ClaimModel]`: parse summary JSON, extract claims list, validate each claim against ClaimModel schema, return list or raise ValueError

- [ ] T029 [P] [US1] Create `src/finfolio/fact_checker.py` helper: `build_report(video_id, summary, verdicts) -> dict`: construct report dictionary from video metadata, summary, and verdicts; populate all ReportModel fields; calculate cost totals; include disclaimer and monetization_disclosure (if applicable); return report dict ready for ReportModel validation

- [ ] T030 [US1] Implement verdict assignment logic in `src/finfolio/fact_checker.py`:
  - For each claim: call Tavily search with claim text (query generation)
  - Pass search results + claim to LLM prompt
  - Parse LLM output: extract verdict, note, source_url, source_date
  - Create VerdictModel with all fields
  - Handle edge cases: no search results → "Unverified", search timeout → "Unverified", API error → log and continue

- [ ] T031 [US1] Create `src/finfolio/fact_checker.py` main entry: `run_fact_check_single_video(video_id: str, config: Config) -> None`:
  1. Check if report exists (idempotent check)
  2. Load summary from storage
  3. Extract claims from summary
  4. For each claim: search + assign verdict
  5. Build report
  6. Validate report against ReportModel
  7. Save report via storage.save_report()
  8. Log results (video_id, claim_count, verdict_count, cost_usd, duration)

- [ ] T032 [US1] Add logging to fact-checking operations in `src/finfolio/fact_checker.py`: log claim ID + text before search, log verdict + source after verdict, log errors with claim context

**Checkpoint**: User Story 1 complete. Single videos can be fact-checked end-to-end. Report schema validated. Cost tracked. Tests pass. Idempotency enforced.

---

## Phase 4: User Story 2 - Handle Partial Failures Gracefully (Priority: P1)

**Goal**: Implement resumability: if fact-checking fails partway through a video's claims, next run continues from unchecked claims without re-processing verified ones.

**Independent Test**: Partial failure (e.g., claim #6 times out) leaves claims 1-5 in report; retry processes only claims 6+; final report has all verdicts.

**Acceptance Criteria**:
- Given fact-checking has verified 5 claims and the 6th search times out
- When the next run executes
- Then only claims 6+ are fact-checked (claims 1-5 are skipped)

### Tests for User Story 2 (Test-First)

- [ ] T033 [P] [US2] Create integration test `tests/integration/test_resumability_partial_failure.py`: 
  - Setup summary with 4 claims
  - Mock Tavily to fail (timeout) on claim #2
  - Run fact_check(video_id) → expects partial report with claims 1 and 3 verdicts
  - Verify report file exists with 2 verdicts
  - Unmock Tavily
  - Run fact_check(video_id) again → expects full report with 4 verdicts
  - Verify claims 1 and 3 unchanged, claims 2 and 4 now added

- [ ] T034 [P] [US2] Create unit test `tests/unit/test_fact_checker_resumability.py`: test `extract_completed_claim_ids(report: dict) -> set[str]` function; test that already-verified claims are identified; test edge case: empty report

### Implementation for User Story 2

- [ ] T035 [P] [US2] Create `src/finfolio/fact_checker.py` helper: `extract_completed_claim_ids(report: dict | None) -> set[str]`:
  - If report is None → return empty set
  - If report exists → extract claim_ids from verdicts list
  - Return set of completed claim IDs for fast O(1) lookup

- [ ] T036 [US2] Extend `src/finfolio/fact_checker.py` function `run_fact_check_single_video()` to support resumability:
  1. Load existing report (if any) via storage
  2. Call extract_completed_claim_ids(existing_report) → completed_ids
  3. For each claim in summary:
     - If claim_id in completed_ids → skip (already verified)
     - Else: search + assign verdict + append to existing verdicts
  4. Save updated report (incremental save after each verdict)
  5. On error (search timeout, API error): catch, log, save partial report, continue to next claim

- [ ] T037 [US2] Implement incremental report save in `src/finfolio/fact_checker.py`:
  - After assigning verdict to claim: immediately save report to storage (via storage.save_report())
  - Ensures partial progress is not lost on failure
  - Uses atomic .tmp writes → safe even with concurrent runs
  - Update report metadata (fact_check_duration, cost) as claims are added

- [ ] T038 [US2] Add error recovery to fact_check_claim() and search operations:
  - Wrap Tavily search in try-except: catch TimeoutError, APIError, etc.
  - On timeout: return VerdictModel with verdict="Unverified", note="Search timed out"
  - On API quota exhausted: return VerdictModel with verdict="Unverified", note="Quota exhausted, retry later"
  - On other API error: log error, return verdict="Unverified", note="Search error, retrying next run"
  - Allow partial reports: remaining claims should not be processed if quota exhausted or critical error

- [ ] T039 [US2] Create `src/finfolio/fact_checker.py` logging for resumability:
  - Log when resume detected: "Resuming video_id; {N} claims already verified, {M} remaining"
  - Log skipped claims: "Skipping claim_id (already verified)"
  - Log recoverable errors: "Search timeout on claim_id; marked Unverified, continuing"

**Checkpoint**: User Story 2 complete. Partial failures are handled gracefully. Resumability works. Reports saved incrementally. Failed runs can be retried without re-processing. Tests pass.

---

## Phase 5: User Story 3 - Expose Fact-Checking via CLI (Priority: P1)

**Goal**: Implement CLI command `finfolio factcheck` for batch processing with progress reporting and error handling.

**Independent Test**: CLI processes all pending videos; reports progress to stdout; exits with correct code; handles errors gracefully.

**Acceptance Criteria**:
- Given the CLI is invoked with `finfolio factcheck`
- When execution completes
- Then stdout reports number of videos processed, number of claims verified, and number of errors

### Tests for User Story 3 (Test-First)

- [ ] T040 [P] [US3] Create unit test `tests/unit/test_cli_parsing.py`: test CLI argument parsing (--help, --limit, --video-id, --verbose); verify argparse configuration

- [ ] T041 [P] [US3] Create integration test `tests/integration/test_cli_batch_mode.py`:
  - Create 3 fixture summaries (test_001, test_002, test_003)
  - Create report for test_001 (to test idempotency)
  - Run CLI: `finfolio factcheck`
  - Verify stdout contains: "Processing X videos", "test_002: Y claims → Y verdicts", "test_003: Z claims → Z verdicts"
  - Verify test_001 skipped (idempotent)
  - Verify exit code 0

- [ ] T042 [P] [US3] Create integration test `tests/integration/test_cli_single_video.py`:
  - Run CLI: `finfolio factcheck --video-id test_video_001`
  - Verify report created for that video
  - Verify exit code 0

- [ ] T043 [P] [US3] Create integration test `tests/integration/test_cli_error_handling.py`:
  - Mock missing API key
  - Run CLI
  - Verify stderr contains error message: "ANTHROPIC_API_KEY not set"
  - Verify exit code 1

### Implementation for User Story 3

- [ ] T044 Create `src/finfolio/cli.py`:
  - Import argparse, logging, sys
  - Define `def main()` as entry point
  - Setup argument parser with:
    - Optional `--limit N` (process max N videos)
    - Optional `--video-id ID` (process single video)
    - Optional `--verbose` (enable DEBUG logging)
    - Optional `--help` (print usage)
  - Implement logic:
    1. Parse arguments
    2. Configure logging (INFO by default, DEBUG if --verbose)
    3. Load Config from environment variables
    4. If --video-id: call run_fact_check_single_video(video_id) and exit
    5. Else: call run_fact_check_batch(limit)

- [ ] T045 [US3] Create `src/finfolio/cli.py` batch function: `run_fact_check_batch(limit: int | None) -> int`:
  1. Call storage.list_pending_videos() → pending list
  2. If limit: pending = pending[:limit]
  3. If no pending: print "No pending videos to process", return 0
  4. Print "Processing X pending summaries..."
  5. Initialize counters: videos_processed, claims_verified, errors_total, cost_total, start_time
  6. For each video in pending (with index):
     - Try: call run_fact_check_single_video(video_id)
     - Catch exception: log error, increment errors_total, continue
     - Update counters: increment videos_processed, add claim count, add cost
  7. Compute duration: time.time() - start_time
  8. Print summary: "Total: X videos, Y claims verified, Z errors, $W cost, D seconds"
  9. Return 0 on success, 1 on fatal error (missing API key)

- [ ] T046 [US3] Create `src/finfolio/cli.py` progress reporting:
  - Print per-video progress: "[N/Total] video_id: X claims → X verdicts (Y errors) [cost: $Z] [duration: D s]"
  - Print at end: "Summary: Videos processed: X, Claims verified: Y, Errors: Z, Cost: $W, Duration: D s"

- [ ] T047 [US3] Create `src/finfolio/cli.py` error handling:
  - Catch missing API keys: check ANTHROPIC_API_KEY and TAVILY_API_KEY; print error to stderr and exit with code 1
  - Catch storage errors: log error, continue to next video (non-fatal)
  - Catch LLM/search errors: catch in run_fact_check_single_video (from US2), return partial report
  - Catch general exceptions: log stack trace, return 1

- [ ] T048 [US3] Create CLI entry point in `src/finfolio/cli.py`:
  - Add `if __name__ == "__main__": sys.exit(main())`
  - OR: configure setuptools entry point in pyproject.toml: `[project.scripts] finfolio = "finfolio.cli:main"`

- [ ] T049 [US3] Create integration test `tests/integration/test_cli_cost_reporting.py`:
  - Run CLI on 1 video
  - Parse stdout
  - Verify cost displayed: "cost: $X.XX"
  - Verify cost > 0 and < $1.00 (reasonable for 1 video)

**Checkpoint**: User Story 3 complete. CLI works end-to-end. Batch processing discovers and processes pending videos. Progress reported to stdout. Errors handled gracefully. Exit codes correct. Tests pass. Idempotency enforced.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Final refinements, documentation, and validation

- [ ] T050 [P] Add comprehensive docstrings to all public functions in `src/finfolio/`: modules, classes, functions (Args, Returns, Raises)
- [ ] T051 [P] Run code quality checks: `ruff check src/ tests/`, `ruff format src/ tests/`, `mypy src/ --strict` (add type hints to any untyped code)
- [ ] T052 [P] Add logging to all critical paths: LLM calls, search queries, errors (verify structured JSON format)
- [ ] T053 Run full test suite: `pytest tests/ --cov=src/finfolio --cov-report=term-missing` (aim for >85% coverage on fact_checker, storage, cli modules)
- [ ] T054 Run quickstart validation scenarios from `specs/003-fact-checking-module/quickstart.md`: verify all 8 scenarios work end-to-end
- [ ] T055 [P] Create `.env.example` file with template env vars: ANTHROPIC_API_KEY, TAVILY_API_KEY, FINFOLIO_STORAGE_DIR
- [ ] T056 Update project README.md: add "Fact-Checking Module" section with CLI usage, dependencies, environment setup
- [ ] T057 Create IMPLEMENTATION_NOTES.md: document key design decisions (Tavily selection, per-claim resumability strategy, atomic writes), gotchas, and debugging tips
- [ ] T058 Run final integration test: `pytest tests/integration/ -v` (all stories should pass independently)
- [ ] T059 Verify Constitution compliance: review code against principles (I: accuracy, II: no advice, III: fact/forecast separation, IV: transparency, VI: official APIs, VII: LangChain abstraction + temp=0); document audit trail

**Checkpoint**: Code is clean, tested, documented, and Constitution-compliant. Ready for review and merge.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 (Setup)**: No dependencies; can start immediately
- **Phase 2 (Foundational)**: Depends on Phase 1 completion → BLOCKS all user stories
- **Phase 3 (US1)**: Depends on Phase 2 completion
- **Phase 4 (US2)**: Depends on Phase 3 completion (builds on US1 logic)
- **Phase 5 (US3)**: Can start after Phase 2 (depends on Phase 3/4 for full functionality, but CLI structure can start earlier)
- **Phase 6 (Polish)**: Depends on all other phases

### User Story Dependencies

- **US1 (Fact-Check Claims)**: Foundation for US2 and US3
- **US2 (Partial Failures)**: Extends US1; refactors fact-checking loop for resumability
- **US3 (CLI)**: Depends on US1 and US2 for core logic; adds CLI wrapper

**Recommended Execution Order** (for independent testing):
1. Phase 1 → Phase 2 (foundation ready)
2. Phase 3 (US1) → verify independently
3. Phase 4 (US2) → verify with partial failure scenarios
4. Phase 5 (US3) → verify CLI with all stories
5. Phase 6 (polish)

### Parallel Opportunities

**Within Phase 2** (Foundation):
- All [P] tasks in data models can run in parallel (different files)
- All [P] tasks in storage can run in parallel (different files)
- All [P] tasks in LangChain setup can run in parallel (different files)
- Config + logging can run in parallel

**Within US1** (Phase 3):
- All [P] test tasks can run in parallel
- After tests pass, implementation tasks (T027-T032) must run sequentially (same file)

**Within US2** (Phase 4):
- All [P] test tasks can run in parallel

**Within US3** (Phase 5):
- All [P] test tasks can run in parallel

**Different User Stories**:
- Once Phase 2 is complete, US1, US2, US3 can be worked on by different developers in parallel
- However, US2 and US3 depend on US1 logic being implemented first

---

## Parallel Example: Phase 2 Foundation

```bash
# All these can run in parallel (different files):
Task T005: Create ClaimModel
Task T006: Create VerdictModel
Task T007: Create ReportModel
Task T008: Create CostModel
Task T010: Implement save_report()
Task T011: Implement has_report()
Task T012: Implement load_summary()
Task T013: Implement list_pending_videos()
Task T015: Create LangChain init
Task T016: Create cost tracking callback
Task T017: Create verdict prompts
Task T020: Create Config dataclass
Task T021: Create logging setup
```

Once all above complete, run tests in parallel:
```bash
Task T009: Test models
Task T014: Test storage
Task T022: Test foundation
```

---

## Parallel Example: US1 Implementation

```bash
# Tests (must run first, FAIL before implementation):
Task T023: Test verdict assignment (with mocks)
Task T024: Test opinion/forecast skipping
Task T025: Integration test single video
Task T026: Contract test report schema

# All tests must PASS before moving to implementation

# Implementation (sequential in same file):
Task T027: Create FactChecker class
Task T028: Extract claims helper
Task T029: Build report helper
Task T030: Verdict assignment logic
Task T031: Main run_fact_check_single_video()
Task T032: Add logging
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. **Phase 1**: Setup ✓
2. **Phase 2**: Foundation ✓
3. **Phase 3**: US1 - Fact-Check Claims ✓
4. **STOP and VALIDATE**: Run quickstart scenario 1 and 2; verify single video fact-checking works
5. Deploy/demo this as MVP

### Incremental Delivery

1. Setup + Foundation → Foundation ready
2. + US1 → MVP: Single video fact-checking ✓ Deploy
3. + US2 → Add resumability: Partial failures handled ✓ Deploy
4. + US3 → Add CLI: Batch processing ✓ Deploy
5. + Polish → Final polish and documentation ✓ Merge

### Parallel Team Strategy (3 developers)

1. **All together**: Phase 1 + Phase 2 (Foundation)
2. **Once Foundation done**:
   - **Dev A**: Phase 3 (US1 - Core fact-checking logic)
   - **Dev B**: Phase 4 (US2 - Resumability, depends on US1)
   - **Dev C**: Polish tasks + documentation
3. Reconverge for Phase 5 (US3 - CLI) and final validation

---

## Task Validation Checklist

Before marking a task done:

- [ ] Tests written and passing
- [ ] Code passes `ruff check` and `ruff format`
- [ ] Type hints added; `mypy` passes
- [ ] Function docstrings present
- [ ] Commit message clear and references task ID
- [ ] File paths match spec (finfolio/models.py, not src/models/finfolio.py)
- [ ] Logging added for debugging
- [ ] Error handling covers edge cases
- [ ] Related Constitution principles documented

---

## Next Steps After Task Completion

1. After all Phase 1 tasks: verify dependencies install cleanly
2. After all Phase 2 tasks: run `pytest tests/unit/` → foundation tests pass
3. After Phase 3 (US1): run `pytest tests/integration/test_fact_check_single_video.py` → US1 works standalone
4. After Phase 4 (US2): run `pytest tests/integration/test_resumability_partial_failure.py` → US2 works
5. After Phase 5 (US3): run `pytest tests/integration/test_cli_batch_mode.py` → CLI works
6. After Phase 6: run full suite `pytest tests/ --cov=src/finfolio` → >85% coverage
7. Run quickstart.md scenarios → all pass
8. Create PR with Constitution compliance audit
9. Merge to main

---

**Tasks Generated**: 59 tasks across 6 phases

**User Story Breakdown**:
- Phase 3 (US1): 10 tasks (T023-T032)
- Phase 4 (US2): 5 tasks (T033-T039)
- Phase 5 (US3): 6 tasks (T040-T049)
- Foundation (Phase 2): 18 tasks (T005-T022)
- Setup (Phase 1): 4 tasks (T001-T004)
- Polish (Phase 6): 10 tasks (T050-T059)

**Parallel Opportunities**:
- Phase 1: 2 tasks can parallelize
- Phase 2: ~12 tasks can parallelize (all [P] tasks)
- Phase 3: 4 test tasks parallelize; implementation sequential
- Phase 4: 2 test tasks parallelize
- Phase 5: 4 test tasks parallelize

**MVP Scope**: Complete Phase 1 + Phase 2 + Phase 3 (US1 only) = 32 tasks = ~2-3 weeks for 1 developer

**Full Feature Scope**: All 59 tasks = ~3-4 weeks for 1 developer, or 1.5-2 weeks with 2 developers

---

**Tasks Complete**: Ready for implementation. Each task is specific, has file paths, and can be tracked independently.

---

## Phase 6 (Convergence): Final Validation & Polish

**Purpose**: Complete remaining validation, testing, and documentation to finalize feature for production.

- [x] T060 Run full test suite: `pytest tests/ -v --cov=finfolio --cov-report=term-missing` (aim >85% coverage)
- [x] T061 Validate against quickstart.md scenarios: test all 8 scenarios end-to-end
- [x] T062 Type checking: `mypy src/ --strict` and fix any untyped code
- [x] T063 Code quality: `ruff check src/ tests/` and `ruff format src/ tests/`
- [x] T064 Final Constitution compliance audit: verify all 7 principles in code (already done, document)
- [x] T065 Create deployment guide: setup instructions, env vars, cost estimates
- [x] T066 Performance validation: test with 100-claim video, document latency & costs
- [x] T067 Final documentation review: ensure all docstrings complete, README up-to-date
- [x] T068 Mark Phase 6 tasks complete and prepare for merge to main

**Checkpoint**: Implementation feature-complete, tested, documented, and ready for production.
