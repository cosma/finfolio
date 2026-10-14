# Tasks: Search Fallback and Claim Re-check

**Input**: Design documents from `/specs/006-search-fallback/`

**Prerequisites**: plan.md (required), spec.md (required), research.md, data-model.md, contracts/, quickstart.md

**Note**: The code for most tasks already exists on branch `fix/search-fallback-and-claim-cleanup` (PR #6). Those tasks are marked `[X]` with the file that satisfies them. Open tasks are the gaps found when checking the code against the spec.

**Tests**: Included. The spec's acceptance scenarios map to the test files named in each phase.

**Organization**: Grouped by user story (US1–US4) from the spec, after setup and foundational work.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: User story (US1–US4)

---

## Phase 1: Setup

- [X] T001 Add `ddgs>=9.16.0` to runtime dependencies in `pyproject.toml`
- [X] T002 Regenerate the lockfile `uv.lock` with `uv lock`

---

## Phase 2: Foundational

**Purpose**: Shared error types, the free search client, verdict fields, the prompt, and test isolation. Every user story depends on these.

- [X] T003 Create `SearchError` and `SearchQuotaError` in `src/finfolio/search/errors.py` (spec FR-004)
- [X] T004 Create the free search client `DuckDuckGoSearchClient` in `src/finfolio/search/ddg_client.py` (spec FR-001)
- [X] T005 Make `TavilySearchClient.search` raise `SearchError` and `SearchQuotaError` on any failure, instead of returning an empty list, in `src/finfolio/search/tavily_client.py` (spec FR-004)
- [X] T006 Add `verified_by` and `confidence` to `VerdictModel` and the rule `verdict_needs_recheck` in `src/finfolio/models.py` (spec FR-006, FR-007)
- [X] T007 Ask the model for a `confidence` field in the verdict prompt in `src/finfolio/llm/prompts.py` (spec FR-002)
- [X] T008 Stop `.env` loading and stub the free search for every test in `tests/conftest.py` (spec FR-011)

**Checkpoint**: Search clients, error types, and verdict fields exist. User stories can begin.

---

## Phase 3: User Story 1 - Verify claims with the free source first (P1)

**Goal**: Check each claim with the free source first; fall back to the paid source when the free one is not confident.

**Independent Test**: `tests/unit/test_search_chain.py` — confident free verdict accepted without paid search; low confidence, Unverified, empty results, or free-source error all fall back to paid.

- [X] T009 [US1] Implement the chain in `FactChecker.verify_claim` in `src/finfolio/fact_checker.py` (spec FR-001, FR-003)
- [X] T010 [US1] Accept a free-source verdict only if not Unverified and confidence ≥ threshold, in `FactChecker.verify_claim` in `src/finfolio/fact_checker.py` (spec FR-002). The threshold is currently a module constant, `DDG_CONFIDENCE_THRESHOLD`.
- [X] T011 [US1] Test the chain for all fallback cases in `tests/unit/test_search_chain.py` (spec US1 acceptance scenarios 1–4)
- [X] T029 [US1] Test that an opinion or forecast claim is skipped by the fact-check run, with no search and no verdict, in `tests/unit/test_search_chain.py` (constitution: mandated forecast/opinion test case)
- [X] T012 [US1] Make the threshold a configurable setting `FINFOLIO_SEARCH_MIN_CONFIDENCE`, default 0.8, validated to [0, 1]. Add `search_min_confidence` to `Config` in `src/finfolio/config.py`, use it in `verify_claim` in place of `DDG_CONFIDENCE_THRESHOLD`, and add a test in `tests/unit/test_search_chain.py` that a different value changes the outcome (spec FR-012, clarification session 2026-10-14)

---

## Phase 4: User Story 2 - Stop the run when the paid search fails (P1)

**Goal**: A paid-search failure stops the run with exit code 2, keeps partial verdicts, and a re-run resumes.

**Independent Test**: `tests/unit/test_search_quota.py` — quota stop keeps earlier verdicts and records no Unverified; CLI exits 2 with a clear message.

- [X] T013 [US2] Make `factcheck` catch `SearchError` and exit with code 2, with separate messages for quota and other failures, in `src/finfolio/cli.py` (spec FR-004; contracts/cli-factcheck.md)
- [X] T014 [US2] Keep partial verdicts when a run stops, in the error path of `run_fact_check_single_video` in `src/finfolio/fact_checker.py` (spec FR-005)
- [X] T015 [US2] Test the quota stop, partial save, and CLI exit code in `tests/unit/test_search_quota.py` and resume in `tests/integration/test_resumability.py` (spec US2 acceptance scenarios 1–3)

---

## Phase 5: User Story 3 - Check again claims that were never really checked (P2)

**Goal**: Re-check verdicts with no `verified_by`, replace them without duplicates, and queue videos with claims that have no verdict.

**Independent Test**: `tests/unit/test_recheck.py` and `tests/unit/test_search_chain.py` — legacy verdict is replaced; invalid True/False output is recorded as Unverified and does not crash.

- [X] T016 [US3] Skip re-checkable verdicts in the completed-claim set and drop an older verdict for the same claim before appending, in `src/finfolio/fact_checker.py` (spec FR-007)
- [X] T017 [US3] Include reports with re-checkable verdicts or checkable claims without a verdict in `list_pending_videos` via `_report_needs_recheck` in `src/finfolio/storage.py` (spec FR-009)
- [X] T018 [US3] Treat a True or False verdict with no `source_url` as invalid model output in `_parse_verdict_response` in `src/finfolio/fact_checker.py` (spec FR-008)
- [X] T019 [US3] Test re-check replacement, pending rules, and invalid output in `tests/unit/test_recheck.py`, `tests/unit/test_cleanup_verdicts.py`, and `tests/unit/test_search_chain.py` (spec US3 acceptance scenarios 1–3)
- [X] T030 [US3] Test that a missing confidence value is never accepted from the free source, in `tests/unit/test_search_chain.py` (spec Edge Cases)
- [X] T031 [US3] Test that an unreadable report is skipped by `list_pending_videos` without error, in `tests/unit/test_recheck.py` (spec Edge Cases)

---

## Phase 6: User Story 4 - Clean up stored verdicts (P2)

**Goal**: Remove empty-search Unverified verdicts, mark the rest `verified_by=tavily`, and remove the report-level provider field.

**Independent Test**: `tests/unit/test_cleanup_verdicts.py` for the rules; `scripts/cleanup_claim_verdicts.py` dry run then `--apply` on a copy of the data.

- [X] T020 [US4] Write the cleanup script `scripts/cleanup_claim_verdicts.py` with dry-run default and atomic writes (spec FR-010)
- [X] T021 [US4] Apply the cleanup to the local stored reports: 1,206 Unverified verdicts removed, 840 marked `verified_by=tavily` (spec SC-001). Stored data is gitignored, so this task has no file change in the repo.
- [X] T022 [US4] Test the cleanup rules in `tests/unit/test_cleanup_verdicts.py` (spec US4 acceptance scenarios 1–3)
- [X] T023 [US4] Make a verdict that is Unverified after both sources returned no sources final, by setting `verified_by=tavily` on it (spec FR-013). The re-check rule in T016 then skips it.
- [X] T024 [US4] (code done; existing stored reports still carry the field until the cleanup is applied) Remove the top-level `search_provider` field from `ReportModel` in `src/finfolio/models.py` (line ~123) and from `build_report` in `src/finfolio/fact_checker.py` (line ~316), and have `scripts/cleanup_claim_verdicts.py` remove the field from existing reports. Add a test that new reports have no `search_provider` (spec FR-014; plan Design Decision 7)

---

## Phase 7: Polish & Cross-Cutting Concerns

- [X] T025 [P] Attach the cost tracker to every LLM call on the verify path, so each call is logged with model, tokens, and cost. Today `CostTrackingCallback` is created in `FactChecker.__init__` (`src/finfolio/fact_checker.py`) but never used. Add a test that a verify call produces a cost entry. (Constitution Principle VII, see plan Constitution Check)
- [X] T026 Run the validation steps in `specs/006-search-fallback/quickstart.md`, after T012 and T024 are done, and fix any step whose expected output does not match. Run: steps 1, 2, 3. Not run: step 4 (spends search and LLM credits). Step 5 needs a new fact-check run to produce a record without `search_provider`. Step 3 found a bug in the cleanup, fixed: final Unverified verdicts (with `verified_by`) are no longer removed.
- [X] T027 Run the unit suites touched by this feature and confirm they pass without network or `.env`: `tests/unit/test_search_chain.py`, `tests/unit/test_recheck.py`, `tests/unit/test_search_quota.py`, `tests/unit/test_cleanup_verdicts.py`. Out of scope: 9 tests already failing on main (summarizer and `test_fact_check_single_video`).
- [X] T032 Log the number of free-source and paid-source searches for each run, and the claims that fell back, so SC-003 can be checked from run output (spec SC-003). Add a test in `tests/unit/test_search_chain.py` that the counts match the chain's decisions.
- [X] T028 Regenerate the monthly digests so their counts match the cleaned reports: `finfolio report --month YYYY-MM` for each month (spec Assumptions)

---

## Dependencies & Execution Order

- Phase 2 blocks all user stories.
- US1 (T012) and US2 are independent of each other.
- US3 depends on T006 and T016.
- US4's T024 depends on T020 (the script removes the field).
- Phase 7 depends on T012 and T024.

## Open items at a glance

T012 (threshold setting), T024 (remove `search_provider`), T025 (cost tracking), T026 (quickstart check), T028 (digest regeneration). T021 is done on local data only.
