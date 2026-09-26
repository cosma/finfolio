# Tasks: Monthly Digest Module (Module 4)

**Input**: Design documents from `/specs/004-monthly-digest/`

**Prerequisites**: plan.md ✅, spec.md ✅, data-model.md ✅, contracts/digest-schema.md ✅, quickstart.md ✅

**Organization**: Tasks are grouped by user story (US1, US2, US3) to enable independent implementation and testing

**Tests**: NOT included in this task list (no TDD requested). Test scenarios documented in quickstart.md

## Format: `[ID] [P?] [Story?] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2, US3)
- All tasks include exact file paths

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and basic structure

**Estimated Duration**: 30 minutes

- [ ] T001 Create monthly digest module structure: `src/finfolio/digest.py`, `src/finfolio/storage.py` extension
- [ ] T002 [P] Add MonthlyDigest, ChannelDigest, MonetizationEntry Pydantic models in `src/finfolio/digest.py`
- [ ] T003 [P] Setup imports and dependencies: json, pathlib, datetime, pydantic, click in `src/finfolio/`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core storage and utility functions that ALL user stories depend on

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

**Estimated Duration**: 45 minutes

- [ ] T004 Extend `src/finfolio/storage.py` with `list_reports_for_month(year, month)` function
  - Scan `storage/reports/videos/` for JSON files
  - Filter reports by publication_date month (from summary.metadata.publication_date)
  - Return list of Report file paths
- [ ] T005 [P] Extend `src/finfolio/storage.py` with `save_monthly_digest(year, month, digest_data)` function
  - Create directory `storage/reports/monthly/` if missing
  - Write digest to `storage/reports/monthly/{year}-{month}.json` via atomic .tmp pattern
  - Return path to written file
- [ ] T006 [P] Create report loading utility in `src/finfolio/digest.py`
  - Function to safely load JSON report file with error handling
  - Extract required fields: summary.metadata.publication_date, channel_name, channel_url, verdict_breakdown, monetization_disclosure
  - Log errors on malformed files, return None instead of crashing
- [ ] T007 [P] Create month validation utility in `src/finfolio/digest.py`
  - Validate month format (YYYY-MM pattern)
  - Validate calendar month bounds (01-12)
  - Raise ValueError with clear message on invalid input

**Checkpoint**: Foundation ready - user story implementation can now begin in parallel

---

## Phase 3: User Story 1 - Generate Monthly Digest for a Specific Month (Priority: P1)

**Goal**: Implement core aggregation logic: read reports for a month, calculate overall verdict counts, produce per-channel breakdown

**Independent Test**: Run `finfolio report --month 2026-09` and verify digest file at `storage/reports/monthly/2026-09.json` with correct verdict aggregations (Acceptance Scenarios 1-4 from spec.md)

**Estimated Duration**: 1.5 hours

### Implementation for User Story 1

- [ ] T008 [US1] Create MonthlyDigest class in `src/finfolio/digest.py`
  - Constructor accepts month (YYYY-MM string)
  - Methods: `aggregate()`, `get_overall_verdict_counts()`, `get_per_channel_breakdown()`, `to_dict()`
- [ ] T009 [P] [US1] Implement verdict aggregation logic in `src/finfolio/digest.py`
  - Sum verdict_breakdown counts across all reports in month (True, Partially supported, Unverified, False)
  - Handle empty months (all counts = 0)
  - Store in overall verdict_breakdown
- [ ] T010 [P] [US1] Implement per-channel grouping in `src/finfolio/digest.py`
  - Group reports by channel_name
  - Calculate verdict_breakdown for each channel
  - Sort by channel_name for determinism
  - Create ChannelDigest objects with channel_name, channel_url, video_count, verdict_breakdown
- [ ] T011 [US1] Implement JSON serialization in `src/finfolio/digest.py`
  - Serialize MonthlyDigest to JSON with fields: month, generated_at (ISO 8601 UTC), report_count, verdict_breakdown, per_channel_breakdown
  - Ensure output matches schema from contracts/digest-schema.md
  - All numbers as integers (not strings)
- [ ] T012 [US1] Implement idempotency in `src/finfolio/digest.py`
  - Generate digest to produce consistent output on multiple runs
  - Use atomic file write via save_monthly_digest() from T005
  - Verify deterministic ordering (channels sorted by name)
- [ ] T013 [US1] Add input validation and error handling
  - Validate month parameter in constructor
  - Handle missing storage/reports/videos/ directory gracefully
  - Handle empty month (report_count = 0)
  - Log all errors without crashing

**Checkpoint**: At this point, User Story 1 should be fully functional and testable independently

---

## Phase 4: User Story 2 - Aggregate Monetization Disclosures (Priority: P1)

**Goal**: Extend verdict aggregation to include monetization disclosure collection and deduplication

**Independent Test**: Run command with reports containing monetization_disclosure fields and verify monetization_summary array in digest (Acceptance Scenarios 1-3 from spec.md)

**Estimated Duration**: 45 minutes

### Implementation for User Story 2

- [ ] T014 [US2] Extend MonthlyDigest aggregation to collect monetization disclosures
  - For each report in month: extract monetization_disclosure field (if non-null)
  - Collect (channel_name, disclosure_text) pairs
- [ ] T015 [P] [US2] Implement deduplication logic in `src/finfolio/digest.py`
  - Deduplicate by (channel_name, disclosure_text) tuple
  - Remove duplicate disclosure_text for same channel
  - Create MonetizationEntry objects with channel_name, disclosure
- [ ] T016 [US2] Implement monetization ordering in `src/finfolio/digest.py`
  - Sort monetization_summary by channel_name, then by disclosure_text for determinism
  - Add to MonthlyDigest.to_dict() output as monetization_summary array
- [ ] T017 [US2] Handle null/missing monetization_disclosure fields
  - Skip null values (no disclosure)
  - Skip videos with no monetization_disclosure field
  - Generate digest with empty monetization_summary array if no disclosures found
  - Test scenarios: videos with disclosures, videos without, mixed

**Checkpoint**: At this point, User Stories 1 AND 2 should both work independently, and digest should include both verdict and monetization data

---

## Phase 5: User Story 3 - Expose Digest Generation via CLI (Priority: P1)

**Goal**: Add Click CLI command to trigger digest generation with month parameter, validation, and JSON logging output

**Independent Test**: Run `finfolio report --month 2026-09` and verify success message + digest file written (Acceptance Scenarios 1-3 from spec.md); test invalid month format error handling

**Estimated Duration**: 1 hour

### Implementation for User Story 3

- [ ] T018 [US3] Create CLI command function in `src/finfolio/cli.py`
  - Add Click command: `@cli.command(name='report')`
  - Accept `--month` parameter (optional, default to current month if omitted)
  - Call MonthlyDigest.aggregate() and save result
- [ ] T019 [P] [US3] Implement month parameter parsing in CLI
  - Accept YYYY-MM format
  - Parse into year and month integers
  - Validate format and bounds (01-12 for month)
  - Emit error message for invalid input (e.g., "2026-13", "09-2026")
  - Do NOT write digest file on validation error
- [ ] T020 [US3] Implement JSON logging output in `src/finfolio/cli.py`
  - Log to stdout: JSON object with timestamp (ISO 8601 UTC), event, status, month, digest_path, report_count, error (if applicable)
  - On success: `event='digest_generated'`, `status='success'`, include digest_path and report_count
  - On failure: `event='digest_generation_failed'`, `status='failed'`, include error message
  - Follow same logging pattern as other FinFolio modules (one JSON object per line)
- [ ] T021 [US3] Handle edge cases in CLI
  - No reports for requested month: create digest with report_count=0, all verdicts=0, empty arrays
  - Malformed report files: log error, continue processing, generate partial digest
  - Permission errors on directory creation: emit error message, do not proceed
  - Concurrent execution: rely on atomic .tmp pattern for safety
- [ ] T022 [US3] Test default month behavior
  - If `--month` not provided: use current calendar month (derived from date.today())
  - Generate digest for current month
  - Update spec.md and test documentation if needed

**Checkpoint**: All user stories should now be independently functional via CLI

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Testing, validation, and final integration

**Estimated Duration**: 1.5 hours

- [ ] T023 [P] Run quickstart.md validation scenarios
  - Scenario 1: Generate digest for current month, verify file and structure
  - Scenario 2: Default to current month (no --month flag)
  - Scenario 3: Empty month handling (no reports)
  - Scenario 4: Idempotent operation (two runs produce identical hash)
  - Scenario 5: Per-channel breakdown accuracy
  - Scenario 6: Monetization summary correctness
  - Scenario 7: Invalid month format error handling
- [ ] T024 [P] Verify schema compliance
  - Load generated digest JSON from storage/reports/monthly/
  - Validate against Pydantic models (Digest, ChannelDigest, MonetizationEntry, VerdictBreakdown)
  - Confirm all required fields present
  - Confirm field types match (integers, strings, arrays, objects)
- [ ] T025 [P] Test edge cases from spec.md
  - Empty month: report_count=0, all verdict counts=0, empty per_channel_breakdown, empty monetization_summary
  - Malformed report file: skip with error log, continue processing
  - Very large month: create test data with 100+ reports, verify < 2 seconds completion time
  - Concurrent execution: run two commands simultaneously, verify no corruption
- [ ] T026 Verify performance target
  - Measure digest generation time for month with 50 videos
  - Confirm < 2 seconds (from Clarification Q4, SC-004)
  - Document any performance bottlenecks found
- [ ] T027 [P] Code quality checks
  - Run `ruff check src/finfolio/digest.py src/finfolio/cli.py`
  - Fix any linting issues
  - Run `mypy src/finfolio/` for type checking
  - Ensure all imports are used, no unused variables
- [ ] T028 [P] Add inline documentation
  - Docstrings for MonthlyDigest class and all public methods
  - Comments for complex aggregation logic (verdict summing, deduplication)
  - Type hints on all function parameters and returns
- [ ] T029 Verify Constitution compliance
  - Confirm no financial advice in output (digest = statistics only)
  - Confirm monetization disclosure transparency (Principle V)
  - Confirm no external APIs or LLM calls needed (pure aggregation)
  - Confirm error handling and logging for observability (Principle IV)
- [ ] T030 Final integration test
  - Run full end-to-end: `finfolio report --month 2026-09` with real report data
  - Verify digest file created with expected structure
  - Verify CLI output matches spec (JSON logging format)
  - Commit all changes with message: "feat: monthly digest module (Module 4) implementation"

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Stories (Phase 3, 4, 5)**: All depend on Foundational phase completion
  - US1 (verdict aggregation) can start after Foundational
  - US2 (monetization) depends on US1 logic, can start after US1 models created
  - US3 (CLI) depends on US1 and US2, integrates both
- **Polish (Phase 6)**: Depends on all user stories being complete

### Within Each Phase

- **Phase 1**: T002 and T003 can run in parallel (both create models/imports)
- **Phase 2**: T005, T006, T007 marked [P] can run in parallel (different functions, no dependencies)
- **Phase 3**: T009, T010 marked [P] can run in parallel (verdict sum vs channel grouping)
- **Phase 4**: T015 marked [P] can run with T014 (both work on monetization, independent logic)
- **Phase 5**: All tasks sequential (CLI depends on aggregation from US1/US2)
- **Phase 6**: All T023-T028 marked [P] can run in parallel (independent validations)

### Parallel Example: Phase 3 (User Story 1)

```bash
# Launch verdict aggregation and per-channel grouping in parallel:
Task: "Implement verdict aggregation logic in src/finfolio/digest.py" [T009]
Task: "Implement per-channel grouping in src/finfolio/digest.py" [T010]

# Both read from same report list but write to different aggregation structures
# No conflicts; can start together after T008 (MonthlyDigest class created)
```

---

## Implementation Strategy

### MVP First (All 3 User Stories)

The monthly digest module is relatively small and tightly coupled:

1. Complete Phase 1: Setup (30 min)
2. Complete Phase 2: Foundational (45 min)
3. Complete Phase 3: User Story 1 - Verdict aggregation (1.5 hrs)
4. **VALIDATE**: Test US1 independently with quickstart.md Scenarios 1-4
5. Complete Phase 4: User Story 2 - Monetization (45 min)
6. **VALIDATE**: Test US2 with quickstart.md Scenarios 5-6
7. Complete Phase 5: User Story 3 - CLI command (1 hr)
8. **VALIDATE**: Test full CLI with quickstart.md Scenarios 1-7
9. Complete Phase 6: Polish (1.5 hrs)
10. **SHIP**: Deploy as complete feature (all 3 stories = MVP)

**Total Time Estimate**: ~7 hours

### Parallel Team Strategy (if staffed)

With 2-3 developers:

1. Developer A: Phase 1 + Phase 2 (1.25 hrs) - Foundation work
2. Once Phase 2 complete:
   - Developer A: Phase 3 (User Story 1) - Verdict aggregation
   - Developer B: Phase 4 (User Story 2) - Monetization (start immediately after Phase 2)
3. Developer C: Phase 5 (CLI) - can start as soon as US1 models are created (after T008)
4. All: Phase 6 (Polish) - run validation tasks in parallel

---

## Checkpoint Summary

| Checkpoint | What's Working | What's NOT Yet | Next Step |
|-----------|---|---|---|
| After Phase 1 | Models defined | Nothing runs | Start Phase 2 |
| After Phase 2 | Storage layer ready | No aggregation | Start Phase 3 (US1) |
| After Phase 3 | Verdict aggregation works | No monetization, no CLI | Start Phase 4 (US2) |
| After Phase 4 | Verdicts + Monetization | No CLI command | Start Phase 5 (US3) |
| After Phase 5 | Full end-to-end CLI | Polish/testing missing | Start Phase 6 |
| After Phase 6 | Feature complete + tested | Ready to ship | Commit and merge |

---

## Notes

- [P] tasks = different files, no dependencies on same resource
- [Story] label maps task to specific user story for traceability
- Each user story is independently testable after its phase completes
- Quickstart.md has full validation scenarios for manual testing
- Constitution compliance verified (no financial advice, pure aggregation, no external APIs)
- Performance target: < 2 seconds for 100 videos (validated in T026)
- Commit after each phase or major milestone
- All file paths are relative to repository root (`src/`, `storage/`, etc.)

---

**Task List Version**: 1.0 | **Total Tasks**: 30 | **Status**: Ready for Implementation
