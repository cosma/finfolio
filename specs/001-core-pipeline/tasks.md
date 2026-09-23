# Tasks: FinFolio Core Pipeline

**Input**: Design documents from `specs/001-core-pipeline/`  
**Prerequisites**: plan.md (required), spec.md (required for user stories)  
**Tests**: Full TDD approach with test-first tasks  
**Organization**: Tasks grouped by user story (6 user scenarios) to enable independent implementation and testing.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3, US4, US5, US6)
- Include exact file paths in descriptions

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and basic structure

- [ ] T001 Create project structure per implementation plan (pyproject.toml, finfolio/, frontend/, config/, tests/)
- [ ] T002 Initialize Python 3.11+ project with pyproject.toml, install-requires, dev-requires
- [ ] T003 [P] Configure ruff (linting & formatting) in pyproject.toml
- [ ] T004 [P] Configure mypy (type checking) in pyproject.toml
- [ ] T005 [P] Setup pytest (testing framework) with conftest.py in tests/
- [ ] T006 Create .env.example with required environment variable placeholders (DATABASE_URL, ANTHROPIC_API_KEY, YOUTUBE_API_KEY, GOOGLE_SEARCH_API_KEY)
- [ ] T007 Setup GitHub Actions workflow (.github/workflows/finfolio-pipeline.yaml) for daily monitoring and Monday digest runs
- [ ] T008 Initialize Vue 3 + TypeScript + Vite frontend (package.json, vite.config.ts, tsconfig.json)
- [ ] T009 [P] Setup frontend linting (eslint/prettier in package.json)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [ ] T010 Setup PostgreSQL connection pooling and session management in finfolio/database/session.py
- [ ] T011 Initialize SQLAlchemy ORM models base class in finfolio/database/models.py
- [ ] T012 [P] Setup Alembic migration framework (alembic/ directory, env.py, script.py.mako)
- [ ] T013 [P] Create database models for Videos, ProcessingStatus, Claims, FactChecks, Reports, LLMCalls, Digests in finfolio/database/models.py (define all 7 entities)
- [ ] T014 [P] Create initial Alembic migration to create all tables with relationships in alembic/versions/001_initial_schema.py
- [ ] T015 Create config.py (environment loading, model selection, constants) in finfolio/config.py
- [ ] T016 [P] Implement YouTube API client wrapper in finfolio/pipeline/youtube.py (search, captions list/download)
- [ ] T017 [P] Implement Google Custom Search API wrapper in finfolio/pipeline/search.py
- [ ] T018 [P] Implement LangChain chain base setup and provider selection in finfolio/pipeline/chains.py (model selection from config, temperature discipline)
- [ ] T019 Setup FastAPI app factory in finfolio/api/app.py
- [ ] T020 [P] Create Pydantic schemas for API requests/responses in finfolio/api/schemas.py
- [ ] T021 [P] Setup logging and cost tracking utilities in finfolio/utils/logging.py and finfolio/utils/cost.py
- [ ] T022 Create CLI entry point and group in finfolio/cli/main.py (Click setup)

**Checkpoint**: Foundation ready - user story implementation can now begin in parallel

---

## Phase 3: User Story 1 - Monitor New Content (Priority: P1) 🎯 MVP

**Goal**: System monitors configured YouTube channels daily, fetches new video transcripts, and stores them for processing.

**Independent Test**: Can run `finfolio run --channels test.yaml --days 1` and retrieve new video transcripts from database without processing them further.

### Tests for User Story 1 (TDD: Write FIRST, expect FAIL)

- [ ] T023 [P] [US1] Contract test for YouTube channel search endpoint in tests/contract/test_youtube_search.py (verify API query structure and response parsing)
- [ ] T024 [P] [US1] Contract test for YouTube captions download endpoint in tests/contract/test_youtube_captions.py (verify captions retrieved and stored)
- [ ] T025 [P] [US1] Integration test for `finfolio run` CLI command in tests/integration/test_monitoring.py (end-to-end channel monitoring, deduplication check)
- [ ] T026 [P] [US1] Unit test for YouTube API quota tracking in tests/unit/test_quota_tracking.py

### Implementation for User Story 1

- [ ] T027 [P] [US1] Implement YouTube Data API v3 channel search in finfolio/pipeline/youtube.py (search().list with date filtering)
- [ ] T028 [P] [US1] Implement YouTube Data API v3 caption download in finfolio/pipeline/youtube.py (captions().list → captions().download)
- [ ] T029 [P] [US1] Create channels configuration file loader in finfolio/config/channels.yaml (sample YAML with ~10 channels)
- [ ] T030 [US1] Implement video storage with deduplication check in finfolio/database/models.py queries (insert video, check if exists, skip if already processed)
- [ ] T031 [US1] Implement YouTube quota logging in finfolio/pipeline/youtube.py (track units per call, log cumulative per run)
- [ ] T032 [US1] Implement `finfolio run` CLI command in finfolio/cli/monitor.py (--channels, --days arguments)
- [ ] T033 [US1] Add error handling for missing captions in finfolio/pipeline/youtube.py (mark video as failed, not guessing)
- [ ] T034 [US1] Add logging for monitoring operations in finfolio/pipeline/youtube.py (channels checked, videos found, quota used)

**Checkpoint**: User Story 1 complete - daily monitoring works independently

---

## Phase 4: User Story 2 - Summarize & Extract Claims (Priority: P1)

**Goal**: For each transcript, LLM generates summary and extracts discrete factual claims, separated from opinions/forecasts.

**Independent Test**: Can run `finfolio process --video-id <id>` on a monitored video and retrieve summary + extracted claims from database.

### Tests for User Story 2 (TDD: Write FIRST, expect FAIL)

- [ ] T035 [P] [US2] Contract test for LLM summarization chain in tests/contract/test_summarization_chain.py (verify chain input/output structure, temperature=0.3)
- [ ] T036 [P] [US2] Contract test for claim extraction parsing in tests/contract/test_claim_extraction.py (verify facts/opinions/forecasts are separated)
- [ ] T037 [P] [US2] Integration test for `finfolio process` on summarization in tests/integration/test_extraction.py (end-to-end transcript → summary + claims)
- [ ] T038 [P] [US2] Unit test for claim parsing and validation in tests/unit/test_claim_parsing.py

### Implementation for User Story 2

- [ ] T039 [P] [US2] Implement LangChain summarization+extraction chain in finfolio/pipeline/chains.py (LCEL, temperature=0.3, prompt for facts/opinions separation)
- [ ] T040 [P] [US2] Implement LLM call logging (model, tokens, cost) in finfolio/database/models.py queries (log to LLMCalls table)
- [ ] T041 [P] [US2] Implement response parsing (summary, claims, opinions) in finfolio/pipeline/chains.py (structured output handling)
- [ ] T042 [US2] Implement claim storage in finfolio/database/models.py queries (insert Claims, set claim_type, link to video)
- [ ] T043 [US2] Implement vector embedding generation and storage in finfolio/pipeline/chains.py (embed claims via LangChain, store in pgvector)
- [ ] T044 [US2] Implement status update (pending → claims_extracted) in finfolio/database/models.py queries
- [ ] T045 [US2] Implement `finfolio process` CLI command in finfolio/cli/process.py (--video-id argument, trigger extraction)
- [ ] T046 [US2] Add error handling for LLM API failures in finfolio/pipeline/chains.py (retry logic, mark as failed)
- [ ] T047 [US2] Add logging for extraction operations in finfolio/pipeline/chains.py (claims found, opinions found, LLM cost)

**Checkpoint**: User Stories 1 & 2 complete - monitoring + extraction work independently

---

## Phase 5: User Story 3 - Fact-Check Claims (Priority: P1)

**Goal**: For each extracted claim, search web for independent sources, assign verdict (True/Partially Supported/Unverified/False), optionally use LLM for ambiguous cases.

**Independent Test**: Can run `finfolio process --video-id <id>` on claims and retrieve fact-checks with verdicts from database.

### Tests for User Story 3 (TDD: Write FIRST, expect FAIL)

- [ ] T048 [P] [US3] Contract test for web search integration in tests/contract/test_web_search.py (verify Google Custom Search API query)
- [ ] T049 [P] [US3] Contract test for fact-checking chain in tests/contract/test_factcheck_chain.py (verify LLM input/output, temperature=0)
- [ ] T050 [P] [US3] Integration test for claim fact-checking in tests/integration/test_factchecking.py (end-to-end claim → verdict with sources)
- [ ] T051 [P] [US3] Unit test for verdict assignment logic in tests/unit/test_verdict_logic.py (True/Partially Supported/Unverified/False rules)

### Implementation for User Story 3

- [ ] T052 [P] [US3] Implement web search integration in finfolio/pipeline/search.py (Google Custom Search API wrapper for LangChain tool)
- [ ] T053 [P] [US3] Implement LangChain fact-checking chain in finfolio/pipeline/chains.py (search tool + LLM synthesis, temperature=0)
- [ ] T054 [P] [US3] Implement ambiguity detection and LLM escalation in finfolio/pipeline/chains.py (conflicting sources → LLM for verdict confirmation)
- [ ] T055 [US3] Implement fact-check storage in finfolio/database/models.py queries (insert FactChecks, link to claim, store sources and note)
- [ ] T056 [US3] Implement status update (claims_extracted → fact_checked) in finfolio/database/models.py queries
- [ ] T057 [US3] Add error handling for web search failures in finfolio/pipeline/search.py (graceful degradation → "Unverified")
- [ ] T058 [US3] Add logging for fact-checking operations in finfolio/pipeline/chains.py (verdict assigned, sources found, LLM consulted)

**Checkpoint**: User Stories 1, 2, & 3 complete - monitoring + extraction + fact-checking work independently

---

## Phase 6: User Story 4 - Generate Per-Video Report (Priority: P2)

**Goal**: Assemble per-video report (metadata, summary, fact-check table, accuracy score, monetization disclosure).

**Independent Test**: Can retrieve per-video report from database with all required fields and accurate accuracy score.

### Tests for User Story 4 (TDD: Write FIRST, expect FAIL)

- [ ] T059 [P] [US4] Integration test for report generation in tests/integration/test_report_generation.py (end-to-end claims → report with accuracy score)
- [ ] T060 [P] [US4] Unit test for accuracy score calculation in tests/unit/test_accuracy_calculation.py (True/Partially Supported vs. Unverified/False)

### Implementation for User Story 4

- [ ] T061 [P] [US4] Implement report assembly logic in finfolio/pipeline/processors.py (fetch video, summary, claims, verdicts; assemble JSON/HTML)
- [ ] T062 [P] [US4] Implement accuracy score calculation in finfolio/utils/cost.py (% of True + Partially Supported out of total claims)
- [ ] T063 [P] [US4] Implement monetization disclosure detection in finfolio/pipeline/processors.py (scan summary for keywords: "course", "affiliate", "paid", etc.)
- [ ] T064 [US4] Implement report storage in finfolio/database/models.py queries (insert Reports, calculate accuracy_score, set monetization_disclosed)
- [ ] T065 [US4] Implement HTML rendering for report in finfolio/pipeline/processors.py (generate HTML from report JSON for UI)
- [ ] T066 [US4] Implement status update (fact_checked → report_generated) in finfolio/database/models.py queries
- [ ] T067 [US4] Add logging for report operations in finfolio/pipeline/processors.py (accuracy score, monetization detected)

**Checkpoint**: User Stories 1–4 complete - full per-video pipeline works

---

## Phase 7: User Story 5 - Weekly Digest (Priority: P2)

**Goal**: Aggregate all per-video reports from a week into a weekly digest (aggregated stats, breakdown by channel).

**Independent Test**: Can generate weekly digest with aggregated statistics and links to all reports from that week.

### Tests for User Story 5 (TDD: Write FIRST, expect FAIL)

- [ ] T068 [P] [US5] Integration test for digest generation in tests/integration/test_digest_generation.py (end-to-end reports → aggregated digest)
- [ ] T069 [P] [US5] Unit test for statistics aggregation in tests/unit/test_digest_aggregation.py (accuracy avg, verdict distribution, monetization count)

### Implementation for User Story 5

- [ ] T070 [P] [US5] Implement digest aggregation logic in finfolio/pipeline/processors.py (fetch reports for week, calculate stats)
- [ ] T071 [P] [US5] Implement statistics calculation in finfolio/pipeline/processors.py (video count, avg accuracy, verdict distribution per channel)
- [ ] T072 [P] [US5] Implement HTML rendering for digest in finfolio/pipeline/processors.py (generate HTML from digest JSON)
- [ ] T073 [US5] Implement digest storage in finfolio/database/models.py queries (insert Digests with aggregated stats)
- [ ] T074 [US5] Implement `finfolio report --week` CLI command in finfolio/cli/report.py (--week argument, date parsing)
- [ ] T075 [US5] Add logging for digest operations in finfolio/pipeline/processors.py (channels aggregated, stats calculated)

**Checkpoint**: User Stories 1–5 complete - monitoring, extraction, fact-checking, reporting, and digest work

---

## Phase 8: User Story 6 - Search & Browse Reports (Priority: P2)

**Goal**: Users can search reports via vector search (semantic) and filters (channel, date, verdict), browse weekly digest and per-video reports via REST API and Vue 3 UI.

**Independent Test**: Can perform vector search on claim embeddings, filter by channel/date/verdict, and retrieve results. UI renders digest and report views.

### Tests for User Story 6 (TDD: Write FIRST, expect FAIL)

- [ ] T076 [P] [US6] Contract test for REST endpoints in tests/contract/test_api_contracts.py (GET /api/reports, /api/digest, /api/search, /api/cost)
- [ ] T077 [P] [US6] Integration test for vector search in tests/integration/test_vector_search.py (embed query, retrieve similar claims via pgvector)
- [ ] T078 [P] [US6] Integration test for REST API endpoints in tests/integration/test_api_endpoints.py (retrieve reports, digest, search results)

### Implementation for User Story 6

- [ ] T079 [P] [US6] Implement vector search in finfolio/database/models.py queries (embed query, use pgvector similarity search)
- [ ] T080 [P] [US6] Implement filter logic in finfolio/database/models.py queries (channel_id, date range, verdict, accuracy_min)
- [ ] T081 [P] [US6] Implement REST endpoints in finfolio/api/routes.py:
  - GET /api/reports (list, paginated)
  - GET /api/reports/{video_id} (detail)
  - GET /api/digest/{week_start_date} (weekly stats)
  - GET /api/search (vector + filters)
  - GET /api/cost (monthly spend)
- [ ] T082 [P] [US6] Implement cost dashboard endpoint in finfolio/api/routes.py (aggregate LLMCalls, calculate monthly spend by call_type)
- [ ] T083 [US6] Implement Vue 3 DigestView component in frontend/src/views/DigestView.vue (weekly stats display, report links)
- [ ] T084 [US6] Implement Vue 3 ReportView component in frontend/src/views/ReportView.vue (per-video report detail, fact-check table, accuracy score, monetization disclosure)
- [ ] T085 [US6] Implement Vue 3 SearchView component in frontend/src/views/SearchView.vue (search bar, filters, results listing)
- [ ] T086 [P] [US6] Implement API client wrapper in frontend/src/api.ts (fetch wrapper for all endpoints)
- [ ] T087 [P] [US6] Implement FactCheckTable, ReportCard, SearchBar components in frontend/src/components/
- [ ] T088 [US6] Implement App.vue routing and layout (Vue Router for DigestView, ReportView, SearchView)
- [ ] T089 [US6] Add styling for UI components (CSS modules or Tailwind, responsive design)
- [ ] T090 [US6] Add UI disclaimer for reports (non-financial-advice, facts only)

**Checkpoint**: All user stories complete - full end-to-end system works

---

## Phase 9: Polish & Cross-Cutting Concerns

**Purpose**: Improvements, hardening, and validation

- [ ] T091 [P] Run quickstart.md validation scenarios end-to-end (all 5 scenarios from plan)
- [ ] T092 [P] Security hardening: validate API auth (if required), SQL injection prevention, XSS prevention in frontend
- [ ] T093 [P] Performance optimization: database indexing (video_id, status, claim_type), caching where applicable
- [ ] T094 [P] Code cleanup: ruff formatting, mypy type checking pass across all modules
- [ ] T095 [P] Documentation: update README.md with setup, CLI usage, API reference, deployment instructions
- [ ] T096 [P] Frontend build optimization: Vite production build, bundle size analysis
- [ ] T097 Error handling coverage: audit all error paths, verify user-friendly messages
- [ ] T098 Logging audit: ensure all key operations logged (monitoring, extraction, fact-checking, API calls)
- [ ] T099 Cost monitoring validation: verify all LLM calls logged with correct token counts and costs
- [ ] T100 Final integration test: run full pipeline on 5–10 sample videos end-to-end, verify reports generated and searchable

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Stories (Phases 3–8)**: All depend on Foundational completion
  - Can proceed sequentially (P1 → P2) or in parallel if staffed
  - Phase 3 (US1–US3): Monitoring → Extraction → Fact-Checking (sequential within Phase, foundation of entire system)
  - Phases 4–8: Can run in parallel (report, digest, search)
- **Polish (Phase 9)**: Depends on all desired user stories being complete

### User Story Dependencies

- **US1 (Monitor)**: Can start after Foundational - No dependencies on other stories
- **US2 (Extract)**: Depends on US1 (needs monitored videos) - Can start after Foundational
- **US3 (Fact-Check)**: Depends on US2 (needs extracted claims) - Can start after Foundational
- **US4 (Report)**: Depends on US3 (needs verdicts) - Can start after Foundational
- **US5 (Digest)**: Depends on US4 (needs reports) - Can start after Foundational
- **US6 (Search/UI)**: Depends on US4 (needs reports to search) - Can start after Foundational

### Within Each User Story

- Tests written first (contract, integration, unit) - expect to FAIL
- Implementation in order: Models → Services/Chains → Endpoints/UI
- Story complete before moving to next

### Parallel Opportunities

- **Phase 1 (Setup)**: All [P] tasks can run in parallel
- **Phase 2 (Foundational)**: All [P] tasks can run in parallel
  - T010, T012, T016, T017, T018, T020, T021 can be done simultaneously
- **Within each user story**: Tests can run in parallel, models can run in parallel
- **Across stories (after Foundational complete)**:
  - Team A: US1 → US2 → US3 (sequential, blocking dependency chain)
  - Team B: US4 (report) in parallel once US3 done
  - Team C: US5 (digest) once US4 done
  - Team D: US6 (search/UI) once US4 done

---

## Parallel Example: Phase 1 Setup

```
Task: T003 Configure ruff (linting & formatting)
Task: T004 Configure mypy (type checking)
Task: T005 Setup pytest (testing framework)
Task: T009 Setup frontend linting (eslint/prettier)
↓ All can run in parallel (different files)
```

---

## Parallel Example: Phase 3 User Stories 1–3

```
Task: T023–T026 [US1] Tests (contract, integration, unit for monitoring)
Task: T027–T033 [US1] Implementation (YouTube API, CLI, logging)
↓ US1 complete

Task: T035–T038 [US2] Tests (summarization chain, claim parsing)
Task: T039–T047 [US2] Implementation (LangChain chain, storage, CLI)
↓ US2 complete (depends on US1)

Task: T048–T051 [US3] Tests (web search, fact-checking chain)
Task: T052–T058 [US3] Implementation (search tool, chain, storage, logging)
↓ US3 complete (depends on US2)
```

---

## Implementation Strategy

### MVP First (User Stories 1–3: Monitoring → Extraction → Fact-Checking)

1. Complete Phase 1: Setup (2 days)
2. Complete Phase 2: Foundational (3 days)
3. Complete Phase 3: User Stories 1–3 (5 days)
4. **STOP and VALIDATE**: Monitor channels, extract claims, fact-check
5. Deploy MVP if ready (monitoring + extraction + fact-checking working)

**MVP Deliverable**: Daily monitoring of 10 YouTube channels, extracting and fact-checking claims, storing results in PostgreSQL.

### Incremental Delivery Beyond MVP

1. Phase 4: User Story 4 (Per-video reports) - 2 days
2. Phase 5: User Story 5 (Weekly digest) - 2 days
3. Phase 6: User Story 6 (Search/UI) - 3 days
4. Phase 9: Polish & hardening - 2 days

Each phase adds testable, independently deliverable value.

---

## Task Count Summary

- **Phase 1 (Setup)**: 9 tasks
- **Phase 2 (Foundational)**: 13 tasks
- **Phase 3 (US1–US3)**: 36 tasks (12 tests + 24 implementation)
- **Phase 4 (US4)**: 7 tasks (2 tests + 5 implementation)
- **Phase 5 (US5)**: 6 tasks (2 tests + 4 implementation)
- **Phase 6 (US6)**: 15 tasks (3 tests + 12 implementation)
- **Phase 9 (Polish)**: 10 tasks
- **Total**: 96 tasks

## MVP Scope

**Minimum Viable Product (Phase 1 + Phase 2 + Phase 3)**:
- Project setup and infrastructure
- Database schema and PostgreSQL connection
- YouTube Data API integration with quota tracking
- LangChain chains for summarization, extraction, fact-checking
- Web search integration for fact-checking
- CLI commands for monitoring and processing
- End-to-end monitoring → extraction → fact-checking pipeline
- Cost tracking for all LLM calls
- Basic logging and error handling

**Total MVP effort**: ~30 tasks (Phases 1–3, prioritize core implementation over tests for speed if needed)
**Estimated timeline**: 10–14 days with 2 developers

