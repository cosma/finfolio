# Tasks: API Layer

**Input**: Design documents from `/specs/005-api-layer/`

**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/api.md, quickstart.md

**Tests**: Included. The spec's success criteria (SC-003, SC-005, SC-006, SC-007) can only be verified by tests, and the plan names a `tests/api` suite.

**Organization**: Tasks are grouped by user story so each story can be implemented and tested independently.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies on incomplete tasks)
- **[Story]**: Which user story this task belongs to (US1, US2, US3)
- Exact file paths are in each description

## Path Conventions

Single project. Source in `src/finfolio/`, tests in `tests/api/`, feature docs in `specs/005-api-layer/`.

---

## Phase 1: Setup (Project Initialization)

**Purpose**: Dependencies and package skeleton.

- [X] T001 Add `fastapi` and `uvicorn` to runtime dependencies, and `httpx` to dev dependencies, in `pyproject.toml`
- [X] T002 Regenerate the lockfile with `uv lock`, producing an updated `uv.lock`
- [X] T003 Create the API package with an empty `__init__.py` at `src/finfolio/api/__init__.py`
- [X] T004 Create `tests/api/conftest.py` with a fixture that builds a temporary storage tree (`reports/videos/`, `reports/monthly/`) under `tmp_path`, and monkeypatches the storage paths in `src/finfolio/storage.py` to point at it. Tests must never touch the real `storage/` directory.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Storage read access, the SQLite index, the app with Swagger UI, and the refresh endpoint. Every user story depends on these.

**CRITICAL**: No user story work can begin until this phase is complete.

- [X] T005 Add `list_report_ids()` and `load_report(video_id)` to `src/finfolio/storage.py`. `load_report` returns `None` when the file is missing and raises `ValueError` on invalid JSON, following the pattern of `load_summary`.
- [X] T006 Add `list_digest_months()` and `load_monthly_digest(year, month)` to `src/finfolio/storage.py`, reading `DIGESTS_DIR`, with the same missing and invalid-JSON behavior as T005.
- [X] T007 [P] Create Pydantic response models in `src/finfolio/api/schemas.py`: `DigestSummary`, `DigestDetail`, `ReportSummary`, `ReportDetail`, `ReportPage`, `RefreshResult`. Detail models use `extra="allow"` so stored fields are not dropped (data-model.md, Response models).
- [X] T008 Create the SQLite schema in `src/finfolio/api/index.py`: tables `reports`, `report_verdicts`, `digests` and the indexes listed in `specs/005-api-layer/data-model.md`.
- [X] T009 Implement index building in `src/finfolio/api/index.py`: read every report and digest through `storage.py`, insert rows, derive `fact_check_date` as the UTC date from `fact_checked_at`, and collect unreadable or malformed files into a `skipped` list with a reason for each. Malformed files must not stop the build (FR-014). Use only the canonical verdict names; any other value makes the file malformed (spec Edge Cases).
- [X] T010 Implement the atomic index swap in `src/finfolio/api/index.py`: build into `storage/.finfolio-api-index.sqlite.tmp`, then `os.replace` it onto `storage/.finfolio-api-index.sqlite`. Add a helper that opens a read-only connection to the current index file (FR-010).
- [X] T011 Create `src/finfolio/api/app.py` with the FastAPI app. A lifespan handler builds the index at startup and then serves requests (spec Edge Cases), and logs an `index_built` line with the counts. Swagger UI stays enabled at `/docs`, with the schema at `/openapi.json`.
- [X] T012 Add `POST /index/refresh` to `src/finfolio/api/app.py`. It rebuilds the index via T009/T010 and returns `RefreshResult`. Requests keep using the old index until the swap (FR-010).
- [X] T013 Add an exception handler in `src/finfolio/api/app.py` that maps `ValueError` from storage to HTTP 500 with a detail message that names the file (FR-013, FR-014).
- [X] T014 [P] Write `tests/api/test_index.py`: a build over fixture storage indexes all valid files, skips an invalid-JSON file and a non-canonical verdict file, and reports both in `skipped` (SC-006).
- [X] T015 [P] Write `tests/api/test_refresh.py`: `/docs` returns 200; `POST /index/refresh` reports the counts; a report file added after startup appears after one refresh and not before, and an edited file is reflected after refresh (SC-005, Edge Cases).

**Checkpoint**: The app starts, builds the index from fixture storage, serves `/docs`, and refreshes. User story work can begin.

---

## Phase 2b: Remediation (from /speckit-analyze)

**Purpose**: Close the HIGH and MEDIUM findings from the analysis. Pipeline tasks (T032–T039) are required before this module ships, but they don't block the API tasks in Phases 3–5.

- [X] T032 [FR-016] Change the verdict name in `src/finfolio/models.py` from "Partially supported/overstated" to "Partially supported" in the `verdict` Literal (line ~69), the `verdict_breakdown` description (~128), and the expected key set (~162).
- [X] T033 [FR-016] Update `src/finfolio/fact_checker.py` (verdict breakdown initialization, ~226) and `src/finfolio/llm/prompts.py` (verdict definition and output schema hint, ~14 and ~19) to use "Partially supported".
- [X] T034 [FR-016] Update existing fixtures and expectations that use the legacy name in `tests/unit/test_models.py`, `tests/unit/test_fact_checker_verdict.py`, `tests/unit/test_storage.py`, `tests/integration/test_foundation.py`, `tests/integration/test_resumability.py`, and `tests/contract/test_report_schema.py`.
- [X] T035 [FR-016] [P] Add a test in `tests/unit/test_models.py` that a claim with verdict "Partially supported/overstated" fails validation.
- [X] T036 [FR-016] Create `scripts/migrate_verdict_names.py`: a one-time migration that rewrites the legacy name in `storage/reports/videos/*.json` and `storage/reports/monthly/*.json`. Dry-run by default; `--apply` writes each file via tmp file and replace. Do NOT run with `--apply` in this task. The owner runs it.
- [X] T037 [FR-015] Add the standard disclaimer to monthly digest output in `src/finfolio/digest.py`. Put the text in one shared constant in `src/finfolio/models.py` and use it in `src/finfolio/fact_checker.py` (~line 260) and `src/finfolio/digest.py`.
- [X] T038 [FR-015] [P] Add `tests/unit/test_digest.py` (new file) asserting a generated digest contains the `disclaimer` field with the constant's text.
- [X] T039 [FR-015] Extend `scripts/migrate_verdict_names.py` with a digest-disclaimer backfill for existing `storage/reports/monthly/*.json` files. Dry-run by default, same `--apply` gate as T036. Do NOT run with `--apply` in this task.
- [X] T040 [FR-009] [P] Write `tests/api/test_no_scan.py`: list and detail requests must not call the per-file helpers in `src/finfolio/storage.py` (patch them to raise).
- [X] T041 [SC-001, SC-002, SC-004] [P] Write `tests/api/test_performance.py`: generate a 5,000-report fixture and assert startup under 10s, filtered report list under 1s, and digest list and detail under 1s on 24 months of digests.
- [X] T042 [FR-010] [P] Extend `tests/api/test_refresh.py`: a request during an in-progress refresh still gets the old index, and a refresh that raises mid-build leaves the old index in use.
- [X] T043 [FR-016, FR-015] Run the migration script's dry run (without `--apply`) against `storage/` and record the file counts in `specs/005-api-layer/quickstart.md` under "Data migration (pending owner approval)".

---

## Phase 3: User Story 1 - Browse Monthly Digests (Priority: P1) MVP

**Goal**: List all monthly digests (newest first) and open one by year and month.

**Independent Test**: Fixture storage with digests for three months. `GET /digests` returns all three newest first. `GET /digests/{year}/{month}` returns the full digest. A missing month returns 404.

### Tests for User Story 1

- [X] T016 [P] [US1] Write `tests/api/test_digests.py` covering spec US1 acceptance scenarios 1–4: list ordering and fields, full single digest with per-channel breakdown and monetization data, 404 for a missing month, empty list when there are no digests, and 422 for month 13 or a 3-digit year.

### Implementation for User Story 1

- [X] T017 [US1] Add `list_digests()` to `src/finfolio/api/index.py`, returning summary rows from the `digests` table ordered by `month` descending.
- [X] T018 [US1] Add `GET /digests` to `src/finfolio/api/app.py`, returning `{"items": [...]}` with `DigestSummary` rows (contracts/api.md).
- [X] T019 [US1] Add `GET /digests/{year}/{month}` to `src/finfolio/api/app.py`. Use path constraints (year 4 digits, month 1–12) for 422. Read the full digest via `storage.load_monthly_digest`, returning 404 when it is missing (contracts/api.md).

**Checkpoint**: US1 works on its own. This is the MVP.

---

## Phase 4: User Story 2 - Find Per-Video Reports (Priority: P2)

**Goal**: List per-video reports, newest fact-check first, filtered by channel, date range, and verdict, with pagination.

**Independent Test**: A fixture set spanning several channels, dates, and verdicts. Each filter alone and combined returns exactly the matching reports.

### Tests for User Story 2

- [X] T020 [P] [US2] Write `tests/api/test_reports_filters.py`: channel filter matches by name and by URL; the date range is inclusive at both ends; the verdict filter matches a report with at least one claim of that verdict; combined filters use AND; a zero-claim report is excluded from verdict results but included unfiltered; no filters returns everything newest first; a filter matching nothing returns an empty result (SC-003).
- [X] T021 [P] [US2] Write `tests/api/test_reports_validation.py`: unknown verdict returns 422 naming the value; `start` after `end` returns 422; a missing bound is treated as open; `page` beyond the last page returns `items: []` with the real `total`; `page_size` above 200 returns 422 (spec FR-003, FR-006, FR-013).

### Implementation for User Story 2

- [X] T022 [US2] Add `query_reports(channel, start, end, verdict, page, page_size)` to `src/finfolio/api/index.py`. Filters use parameterized SQL: channel matches `channel_name` or `channel_url`; the date uses `fact_check_date`; verdict uses `EXISTS` on `report_verdicts`. Order by `fact_checked_at` descending, then `video_id`. Return rows and the filtered total.
- [X] T023 [US2] Add `GET /reports` to `src/finfolio/api/app.py` with query parameters `channel`, `start`, `end`, `verdict` (enum of the four canonical names), `page` (default 1, minimum 1), `page_size` (default 50, minimum 1, maximum 200). Return `ReportPage`. Reject `start` after `end` with 422 naming both values (contracts/api.md).

**Checkpoint**: US1 and US2 both work independently.

---

## Phase 5: User Story 3 - Open a Single Per-Video Report (Priority: P3)

**Goal**: Fetch one per-video report by video ID.

**Independent Test**: Request a known video ID and compare the response with the stored file. Unknown and malformed IDs return the right status codes.

### Tests for User Story 3

- [X] T024 [P] [US3] Write `tests/api/test_reports_detail.py`: a known ID returns the full report; an unknown ID returns 404 naming the ID; a malformed ID (for example `../secret` or a 65-character string) returns 422; an unreadable file returns 500 naming the file (FR-008, FR-013).
- [X] T025 [P] [US3] Write `tests/api/test_passthrough.py`: the response's `disclaimer`, `transcript_source`, `summary`, and `cost` are byte-identical to the stored file's values, for both report and digest responses (FR-015).

### Implementation for User Story 3

- [X] T026 [US3] Add `GET /reports/{video_id}` to `src/finfolio/api/app.py`. Validate `video_id` against `^[A-Za-z0-9_-]{1,64}$` before any storage call (422). Read the file via `storage.load_report`, returning 404 when missing (contracts/api.md).

**Checkpoint**: All three stories work independently.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Read-only guarantee, code quality, and end-to-end verification.

- [X] T027 [P] Write `tests/api/test_readonly.py`: stored files under fixture storage keep identical bytes and modification times after list, detail, and refresh requests (FR-011).
- [ ] T028 Run `ruff check src/ tests/` and `ruff format src/ tests/`, and fix any findings (Constitution: Before Committing). Not done for the five pre-existing unformatted files (digest.py, fact_checker.py, storage.py, test_storage.py, test_foundation.py). Those were already unformatted at HEAD and reformatting them would mix unrelated changes. New and changed API code is formatted and ruff check passes on the whole tree.
- [X] T029 [P] Run `mypy src/` and fix type errors in the new code (Constitution: Type Safety).
- [ ] T044 Run the full `pytest` suite and fix any failures in files this feature touched (Constitution: Before Committing). Not done: 12 tests fail on clean HEAD too (missing TAVILY_API_KEY, summarizer tests). 196 pass; new API tests all pass.
- [X] T030 Run the commands in `specs/005-api-layer/quickstart.md` against a local server with fixture data, and correct any command or expected output that does not match.
- [X] T031 Run `graphify update .` to keep the knowledge graph current after code changes (CLAUDE.md).

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies.
- **Foundational (Phase 2)**: Depends on Setup. Blocks all user stories.
- **User Stories (Phases 3–5)**: All depend on Phase 2. They are independent of each other, so they can run in parallel or in priority order.
- **Polish (Phase 6)**: Depends on the user stories being complete.

### Within Each Story

- Tests are written first and should fail before implementation.
- Index query before endpoint.

### Parallel Opportunities

- T007 is parallel with T005–T006 (different files).
- T014 and T015 are parallel once T009–T012 exist.
- Within each story, the test tasks marked [P] are parallel.
- After Phase 2, US1, US2, and US3 can be worked on by different people, since they touch separate test files and separate functions in `index.py`. The endpoint tasks in `app.py` must be merged carefully.

---

## Parallel Example: User Story 2

```bash
# Write both test files together:
Task: "T020 [P] [US2] Write tests/api/test_reports_filters.py"
Task: "T021 [P] [US2] Write tests/api/test_reports_validation.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 only)

1. Complete Phase 1 (Setup).
2. Complete Phase 2 (Foundational). This is the critical blocker.
3. Complete Phase 3 (US1).
4. Stop and validate: start the server and check `/digests` in Swagger UI.

### Incremental Delivery

1. Setup + Foundational → app runs, `/docs` works, refresh works.
2. Add US1 → digest browsing (MVP).
3. Add US2 → filtered report list.
4. Add US3 → single report drill-down.
5. Polish → read-only guarantee and lint/type checks.

---

## Notes

- Each task names an exact file path so it can be executed without more context.
- [P] tasks touch different files and have no dependencies on incomplete tasks.
- Commit after each task or logical group.
- Stop at any checkpoint to validate that story on its own.

---

## Phase 7: Convergence

**Purpose**: Tasks appended by `/speckit-converge` for gaps between the spec, plan, and tasks and the current code. CRITICAL and HIGH first.

- [X] T045 CRITICAL: Run `ruff format` on `src/finfolio/digest.py`, `src/finfolio/fact_checker.py`, `src/finfolio/storage.py`, `tests/unit/test_storage.py`, and `tests/integration/test_foundation.py` so `ruff format --check src/ tests/` passes per Constitution Clean Code (contradicts)
- [X] T046 CRITICAL: Fix the `mypy src/` errors in `src/finfolio/storage.py`, `src/finfolio/digest.py`, and `src/finfolio/fact_checker.py` per Constitution Type Safety; start with the `ChatAnthropic(model=...)` call at `src/finfolio/fact_checker.py:48`, which may be a real bug (contradicts)
- [X] T047 CRITICAL: Make the failing tests in files this feature touched pass per Constitution Before Committing: `tests/integration/test_foundation.py::test_tavily_client_initialization` (set a dummy `TAVILY_API_KEY` in the test fixture, not a real key) and the two failing tests in `tests/integration/test_resumability.py` (contradicts)
- [X] T048 HIGH: Owner-gated: run `python scripts/migrate_verdict_names.py --apply` after the owner approves, so that stored reports and digests use the canonical verdict name and the disclaimer per FR-016 and FR-015. Do not run without that approval (partial) Applied with the owner's approval. The apply run reported 0 changes because the data was already canonical; see Completion Report for the batch rewrite at 16:28.
- [X] T049 MEDIUM: Move the index-file filesystem operations (`mkdir`, `unlink`, `os.replace` in `src/finfolio/api/index.py`, around lines 131, 133, 178, and 181) into helpers in `src/finfolio/storage.py`, so the API layer never touches the filesystem directly per the plan summary (partial)
- [X] T050 LOW: Replace the inline `ValueError` handling in `src/finfolio/api/app.py` with a global exception handler that maps storage `ValueError` to HTTP 500 naming the file, per T013 and FR-013 (partial)
- [X] T051 LOW: Add a test to `tests/api/test_refresh.py` that a file removed from storage disappears from list results after one refresh, per the spec's Edge Cases (missing)
