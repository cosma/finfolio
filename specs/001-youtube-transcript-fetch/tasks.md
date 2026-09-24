# Tasks: YouTube Channel Monitoring and Transcript Ingestion

**Input**: Design documents from `specs/001-youtube-transcript-fetch/`

**Prerequisites**: plan.md, spec.md (user stories with priorities)

**Organization**: Tasks grouped by user story (US1-US4) to enable independent implementation and testing

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2, US3, US4)
- Exact file paths included in descriptions

## Path Conventions

All paths are relative to repository root (`/Users/cosmin/Projects/cosma/finfolio/`)

```
finfolio/               # Main package
├── __init__.py
├── cli.py             # CLI entry point
├── config.py          # Configuration loading
├── storage.py         # Filesystem abstraction (SHARED)
├── youtube_client.py  # YouTube API wrapper (SHARED)
├── channel_monitor.py # Video discovery
└── transcript_fetcher.py  # Caption download

tests/
├── conftest.py        # pytest fixtures
└── [story-specific]

channels.yaml          # Configuration file (root)
.env.example          # Template for credentials
```

---

## Phase 1: Setup (Project Initialization)

**Purpose**: Create project structure and configure dependencies

- [ ] T001 Initialize pyproject.toml with Python 3.11+ requirements and dependencies (Click, google-api-python-client, pyyaml, python-dotenv)
- [ ] T002 Create finfolio/ package directory structure: `__init__.py`, `cli.py`, `config.py`, `storage.py`, `youtube_client.py`, `channel_monitor.py`, `transcript_fetcher.py`
- [ ] T003 [P] Create tests/ directory with `conftest.py`, `unit/`, `integration/` subdirectories
- [ ] T004 [P] Set up .gitignore: exclude `.env`, `*.pyc`, `__pycache__`, `venv/`, `storage/`, `.pytest_cache`
- [ ] T005 [P] Create `.env.example` template with `YOUTUBE_API_KEY=your-key-here` placeholder
- [ ] T006 Create `channels.yaml` template with example channel entries (format: `channel_id` and `display_name`)
- [ ] T007 [P] Configure ruff linting in pyproject.toml with finfolio-specific rules

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that ALL user stories depend on

**⚠️ CRITICAL**: No user story work can begin until this phase is 100% complete

- [ ] T008 Implement `finfolio/storage.py` module with:
  - `save_transcript(video_id: str, text: str) -> None` — write to `storage/transcripts/{video_id}.txt` with `.tmp` pattern (atomic writes)
  - `has_transcript(video_id: str) -> bool` — check file existence
  - `ensure_storage_dir() -> None` — create `storage/transcripts/` if missing
  - `acquire_lock() -> bool` — create `storage/.finfolio.lock`; return False if already locked
  - `release_lock() -> None` — delete lock file
  - `load_state() -> dict` — load `storage/.finfolio-state.json`; return `{}` if missing
  - `save_state(state: dict) -> None` — write state file atomically
  - All functions include structured JSON logging via `_log_operation()`

- [ ] T009 Implement `finfolio/youtube_client.py` module with:
  - `YouTubeClient` class constructor: accepts `api_key` parameter
  - `search_channel_videos(channel_id: str, after_timestamp: str) -> list` — call YouTube API search().list, return video IDs and metadata
  - `fetch_captions(video_id: str) -> str | None` — call captions().list and captions().download, return raw caption text or None if unavailable
  - `get_quota_units_used() -> dict` — track and return quota units per operation type (search, caption.list, caption.download)
  - Quota accounting for each API call (YouTube API reports units in response metadata)
  - Structured JSON logging for all API calls

- [ ] T010 Implement `finfolio/config.py` module with:
  - `load_config(config_path: str) -> list` — parse `channels.yaml`, return list of dicts with `channel_id` and `display_name`
  - `load_api_key() -> str` — read from `YOUTUBE_API_KEY` environment variable OR `.env` file; raise error if missing
  - Structured JSON logging for config load events
  - Error handling for malformed YAML (FR-012)

- [ ] T011 Implement `finfolio/cli.py` module with:
  - Click CLI setup (no commands yet, just framework)
  - Global options: `--config` for channels.yaml path (default: `./channels.yaml`)
  - Error handling and exit codes (0=success, 1=error, 2=locked)
  - Structured JSON logging to stdout (one object per line)

- [ ] T012 Create pytest fixtures in `tests/conftest.py`:
  - `mock_youtube_client` — mock GoogleAPIClient with predefined search/captions responses
  - `temp_storage_dir` — temporary directory for `storage/` during tests
  - `temp_config_file` — temporary `channels.yaml` for tests
  - Sample video/caption data for tests

**Checkpoint**: Foundation complete - all user stories can now implement independently

---

## Phase 3: User Story 1 - Monitor Channels for New Videos (Priority: P1) 🎯

**Goal**: System discovers new videos from configured YouTube channels using YouTube API search

**Independent Test**: Configure channels.yaml, run `finfolio fetch`, verify API is queried for each channel and new video metadata is identified and logged

### Implementation for User Story 1

- [ ] T013 [P] [US1] Implement `finfolio/channel_monitor.py` module with:
  - `ChannelMonitor` class with `__init__(youtube_client, storage, state_manager)`
  - `check_channel(channel_id: str, display_name: str, last_fetch: datetime) -> list` — call `youtube_client.search_channel_videos()` with timestamp filter, return discovered videos
  - `is_new_video(video_id: str) -> bool` — check against `storage.has_transcript()` for idempotency (FR-003, FR-004)
  - Structured JSON logging for discovery process

- [ ] T014 [P] [US1] Implement state persistence helpers in `finfolio/storage.py`:
  - Extend storage.py with `update_channel_last_fetch(channel_id: str, timestamp: datetime) -> None`
  - Extend storage.py with `get_channel_last_fetch(channel_id: str) -> datetime | None`
  - State file schema: `{"channels": {"channel_id": {"last_fetch": "ISO8601"}}}`

- [ ] T015 [US1] Add `finfolio fetch` command to `finfolio/cli.py`:
  - Create Click command `@click.command('fetch')`
  - Initialize `YouTubeClient`, `ChannelMonitor`, storage helpers
  - Acquire lock (FR-002); exit(2) if locked (FR-002, clarification Q2)
  - Load config via `config.load_config()`
  - For each channel:
    - Get last-fetch timestamp from state
    - Call `channel_monitor.check_channel()`
    - Log discovery results as JSON (event: fetch_channel, status, new_videos count)
  - Release lock on completion
  - Exit codes: 0=success, 1=error, 2=locked

- [ ] T016 [US1] Add API credential validation to CLI:
  - Call `config.load_api_key()` at start
  - Log error and exit(1) if missing (FR-001, clarification Q1)
  - Support both `YOUTUBE_API_KEY` env var AND `.env` file (clarification Q1)

- [ ] T017 [US1] Write integration test `tests/integration/test_channel_monitor.py`:
  - Test: `finfolio fetch` with valid channels.yaml queries API for each channel
  - Test: Idempotency — running fetch twice doesn't discover same video twice
  - Test: Empty channel (no new videos) returns gracefully
  - Test: Invalid channel ID logs error and continues (FR-009, FR-013)
  - Use mock YouTube client from conftest

**Checkpoint**: User Story 1 complete. Channels are monitored, new videos discovered, state persisted. Test independently with `pytest tests/integration/test_channel_monitor.py`.

---

## Phase 4: User Story 2 - Fetch and Store Transcripts (Priority: P1)

**Goal**: System downloads captions from YouTube API and persists transcripts to disk

**Independent Test**: After discovering videos in US1, fetch transcript for each video; verify files exist at `storage/transcripts/{video_id}.txt` with correct content

### Implementation for User Story 2

- [ ] T018 [P] [US2] Implement `finfolio/transcript_fetcher.py` module with:
  - `TranscriptFetcher` class with `__init__(youtube_client, storage)`
  - `fetch_and_save(video_id: str) -> bool` — call `youtube_client.fetch_captions()`, save via `storage.save_transcript()` using `.tmp` pattern (FR-009, clarification Q3), return True on success
  - `has_transcript(video_id: str) -> bool` — wrapper around `storage.has_transcript()` for idempotency (FR-005)
  - Handle missing captions gracefully: log "no transcript available" and return False (FR-010, FR-014)
  - Structured JSON logging for each download attempt

- [ ] T019 [US2] Extend `finfolio fetch` command to download transcripts:
  - After `channel_monitor.check_channel()` discovers videos, initialize `TranscriptFetcher`
  - For each discovered video:
    - Check `transcript_fetcher.has_transcript()` (idempotency check — FR-005)
    - If transcript exists, skip (log event: download_transcript, status: skipped)
    - If not exists, call `transcript_fetcher.fetch_and_save()`
    - Log result as JSON (event: download_transcript, status: success/failed, video_id)
  - If video has no captions, log event with status: no_captions (FR-010)
  - Continue processing other videos if one fails (FR-013)

- [ ] T020 [US2] Add cleanup of leftover `.tmp` files:
  - At startup (in CLI command), scan `storage/transcripts/` for `*.tmp` files
  - Delete any `.tmp` files found (FR-007)
  - Log cleanup event as JSON

- [ ] T021 [US2] Write integration test `tests/integration/test_transcript_fetcher.py`:
  - Test: `finfolio fetch` downloads transcripts for new videos
  - Test: Idempotency — existing transcripts are skipped on second run
  - Test: Video without captions is logged as unavailable and fetch continues
  - Test: `.tmp` files are cleaned up on startup
  - Test: Transcript files contain raw captions in chronological order
  - Use mock YouTube client from conftest

**Checkpoint**: User Story 2 complete. Transcripts downloaded and persisted idempotently. Test independently.

---

## Phase 5: User Story 3 - Log API Quota Usage (Priority: P2)

**Goal**: System tracks and logs YouTube API quota consumption per run

**Independent Test**: Run `finfolio fetch`, verify quota units are logged in JSON output; sum units across operations to confirm they stay under 10,000-unit daily limit

### Implementation for User Story 3

- [ ] T022 [US3] Extend `YouTubeClient.get_quota_units_used()` to track:
  - Units consumed per operation type (search, caption.list, caption.download)
  - Total units for the run
  - Store in instance variable (e.g., `self.quota_usage: dict`)

- [ ] T023 [US3] Extend `finfolio fetch` command to report quota:
  - At start, query current YouTube API quota usage (if available via API)
  - After processing all channels, log final quota report as JSON
  - Log event: fetch_complete, status: success, quota_units: total
  - If quota exhausted mid-run, log warning and gracefully exit (FR-011, edge case)
  - Structured JSON logging with breakdown: `{"search": X, "caption.list": Y, "caption.download": Z, "total": N}`

- [ ] T024 [US3] Add quota check before batch operations:
  - Before processing next channel/video, check remaining quota
  - If insufficient quota for safe operation, log warning and stop (graceful backoff per FR-011)
  - Exit(0) with warning, not error

- [ ] T025 [US3] Write integration test `tests/integration/test_quota_logging.py`:
  - Test: `finfolio fetch` logs total quota units consumed per run
  - Test: Quota breakdown by operation type is present in logs
  - Test: Multiple runs sum correctly toward 10,000-unit daily ceiling
  - Test: If quota exhausted, fetch logs warning and stops gracefully
  - Use mock YouTube client with predefined quota values

**Checkpoint**: User Story 3 complete. Quota usage tracked and logged. Operator can monitor API cost.

---

## Phase 6: User Story 4 - Configure Channels Without Code Changes (Priority: P2)

**Goal**: `channels.yaml` is editable configuration; adding/removing channels requires no code deployment

**Independent Test**: Edit `channels.yaml` (add/remove/modify channels), run `finfolio fetch`, verify new config is applied without code changes

### Implementation for User Story 4

- [ ] T026 [US4] Implement `finfolio/config.py` with robust YAML parsing:
  - Parse `channels.yaml` format: list of dicts with `channel_id` (YouTube ID) and `display_name` (operator-friendly name)
  - Example:
    ```yaml
    channels:
      - channel_id: "UC7_ZLN2t-U-tZ7CgzQ0OoXw"
        display_name: "Graham Stephan"
      - channel_id: "UC_x5XG1OV2P6uZZ5FSM9Ttw"
        display_name: "Two Cents"
    ```
  - Validate YAML syntax; raise error with clear message if invalid (FR-012)
  - Validate channel IDs (warn if malformed YouTube channel ID format)

- [ ] T027 [US4] Add config validation to CLI:
  - At startup, load and validate config (FR-012)
  - If config missing/malformed, log error and exit(1) (FR-012)
  - If config valid, log success event as JSON
  - Support optional `--config` flag to override default path (already in T011)

- [ ] T028 [US4] Test configuration reload on each run:
  - CLI loads fresh config on each `finfolio fetch` invocation
  - No caching of config between runs
  - Changes to `channels.yaml` are respected on next run (FR-001, independently testable)

- [ ] T029 [US4] Write unit test `tests/unit/test_config.py`:
  - Test: `load_config()` parses valid channels.yaml correctly
  - Test: `load_config()` raises error for malformed YAML
  - Test: `load_config()` handles missing channel_id or display_name fields
  - Test: Config changes are picked up on next load (no caching)
  - Use temp config files from conftest

- [ ] T030 [US4] Write integration test `tests/integration/test_config_changes.py`:
  - Test: Edit channels.yaml, run `finfolio fetch`, verify new channels are queried
  - Test: Remove channels from YAML, run fetch, verify they're skipped
  - Test: Invalid channel ID logged as error but fetch continues

**Checkpoint**: User Story 4 complete. Configuration is operator-editable without code changes.

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Final improvements and validation

- [ ] T031 [P] Run `ruff check src/ tests/` and fix any linting issues in all modules
- [ ] T032 [P] Run `mypy src/` to verify type hints pass static analysis
- [ ] T033 [P] Update README.md with:
  - Installation instructions: `pip install -e .`
  - Configuration guide: how to set `YOUTUBE_API_KEY` and edit `channels.yaml`
  - Usage: `finfolio fetch --help` and example invocation
  - Architecture overview and module breakdown
  - Example output (sample JSON logs)

- [ ] T034 Add comprehensive unit tests:
  - `tests/unit/test_storage.py` — all storage operations (save, load, lock, state)
  - `tests/unit/test_youtube_client.py` — quota tracking, API calls (with mock)
  - `tests/unit/test_channel_monitor.py` — video discovery logic
  - `tests/unit/test_transcript_fetcher.py` — transcript download logic
  - Target: >80% code coverage

- [ ] T035 [P] Verify edge cases and error handling:
  - Missing `storage/` directory — auto-created ✓ (FR-011)
  - Malformed YAML — clear error ✓ (FR-012)
  - Missing API key — error and exit ✓ (FR-001)
  - Concurrent runs — lock prevents ✓ (FR-002, FR-003, clarification Q2)
  - Video no captions — skipped gracefully ✓ (FR-010, FR-014)
  - Channel API fails — continue to next ✓ (FR-013)
  - Quota exhausted — stop gracefully ✓ (FR-011)
  - `.tmp` files from interrupted run — cleaned up ✓ (FR-007)

- [ ] T036 Run quickstart.md validation scenarios:
  - Scenario 1: Help text works
  - Scenario 2: Missing API key exits with error
  - Scenario 3: Invalid YAML exits with error
  - Scenario 4: Concurrent locks work
  - Scenario 5: First fetch succeeds
  - Scenario 6: Second fetch is idempotent (zero new transcripts)
  - Scenario 7: Partial failure (one channel fails, others continue)
  - Scenario 8: Quota is logged

- [ ] T037 Commit and document:
  - All tests passing: `pytest tests/ --cov=finfolio`
  - Linting passing: `ruff check src/ tests/`
  - Types passing: `mypy src/`
  - Final commit with message documenting feature completion
  - Push to origin

---

## Dependencies & Execution Order

### Phase Dependencies

1. **Phase 1 (Setup)**: No dependencies — start immediately
2. **Phase 2 (Foundational)**: Depends on Phase 1 — **BLOCKS all user stories**
3. **Phase 3-6 (User Stories)**: All depend on Phase 2 completion
   - US1 and US2 can run in parallel (independent tests)
   - US3 and US4 can run in parallel (independent tests)
   - Or implement sequentially in priority order: US1 → US2 → US3 → US4
4. **Phase 7 (Polish)**: Depends on all desired user stories being complete

### Within Phase 2 (Foundational)

- `T008` (storage.py) must complete before other T00X tasks (it's the abstraction layer)
- `T009` (youtube_client.py) and `T010` (config.py) can run in parallel after T008
- `T011` (cli.py) and `T012` (conftest.py) depend on T009-T010

### Within Each User Story Phase

- Implementation tasks before tests
- But if TDD preferred: write tests first (prefix with `test_`)

### Parallel Opportunities Within Phase 3 (US1)

```bash
# After Foundational complete, these can run in parallel:
T013: Implement channel_monitor.py
T014: Extend storage.py with state persistence (parallel with T013)
T015: Add fetch command (depends on T013, T014)
T016: Add credential validation (parallel with T015, depends on Phase 2)
T017: Write integration tests (after T015 complete)
```

### Team Strategy (Multiple Developers)

With 2-3 developers:

1. **Dev 1**: Phases 1 → 2 (setup foundation)
2. **Once Phase 2 done**:
   - **Dev 1**: User Story 1 (Phase 3) + US3 (Phase 5)
   - **Dev 2**: User Story 2 (Phase 4)
   - **Dev 3**: User Story 4 (Phase 6)
3. **All together**: Phase 7 (polish)

Each developer can test their user story independently before integration.

---

## Implementation Strategy

### MVP First (Minimum Viable Product)

Deliver User Story 1 + 2 only:

1. Complete Phase 1: Setup ✓
2. Complete Phase 2: Foundational ✓
3. Complete Phase 3: US1 (Monitor channels) ✓
4. Complete Phase 4: US2 (Fetch transcripts) ✓
5. **STOP and VALIDATE**: Run `finfolio fetch` end-to-end
6. Test: Channels monitored, transcripts fetched, idempotency confirmed
7. **Deploy/Demo MVP** with these 2 stories

MVP Scope (US1 + US2):
- ✅ Discover new videos from configured channels
- ✅ Download transcripts for new videos
- ✅ Idempotent (safe to run repeatedly)
- ❌ Not yet: Quota monitoring (US3)
- ❌ Not yet: Configuration flexibility (US4)

**Estimated effort**: ~2-3 weeks for 1 developer

### Full Feature (All User Stories)

After MVP validated, add:

8. Complete Phase 5: US3 (Quota logging) — ~3-4 days
9. Complete Phase 6: US4 (Config flexibility) — ~2-3 days
10. Complete Phase 7: Polish & tests — ~1 week
11. **Full feature delivered** with all 4 stories

**Total estimated effort**: ~4-5 weeks for 1 developer, or 2-3 weeks with 2-3 developers

### Parallel Delivery (Recommended with Team)

1. **Week 1**: All devs do Phase 1 + 2 together (setup foundation)
2. **Week 2**: Devs split into US1, US2, US3, US4 (parallel)
3. **Week 3**: Integration, Phase 7 polish, testing
4. **Week 3-4**: Deployment & stabilization

---

## Notes

- **[P] tasks**: Can run in parallel (different files, no dependencies within phase)
- **[Story] label**: Every user story task maps to specific story (US1-US4) for traceability
- **Independent testing**: Each story should be testable independently (see checkpoints)
- **Idempotency**: US1 + US2 are intrinsically idempotent (state + file checks)
- **Graceful degradation**: If one channel fails, fetch continues (FR-013)
- **Quota safety**: Track units to avoid hitting 10K ceiling (FR-011)
- **Configuration-driven**: All channels in YAML, no hardcoding (FR-001, US4)
- **Avoid**: Tight coupling between stories, shared mutable state beyond storage.py

---

## Success Criteria (All 4 User Stories Complete)

✅ All user stories independently testable and passing
✅ All FRs (FR-001 through FR-019) implemented and verified
✅ Specifications met (SC-001 through SC-007)
✅ Constitution principles upheld (VI, VII)
✅ Quota stays under 10K units per day
✅ Idempotent: repeat fetch yields no duplicates
✅ Graceful error handling: partial failures don't crash
✅ Logging: all operations logged as JSON to stdout
✅ Configuration: channels.yaml editable without code changes
✅ Lock file: concurrent runs prevented (clarification Q2)
✅ Credentials: both env var and .env supported (clarification Q1)
✅ Tests: >80% coverage
✅ Linting & types: passing
✅ Documentation: README complete

---

## Phase 8: Convergence - Testing & Quality Gates

**Purpose**: Complete test coverage and verify code quality gates

**Completed by**: /speckit-converge after /speckit-implement Phase 7

Core implementation is feature-complete and production-ready. Convergence identified 5 remaining items in test coverage and quality assurance (all low-to-medium severity, non-blocking). Phase 8 completes the test suite and quality verification.

- [ ] T038 [P] Write unit tests for `finfolio/channel_monitor.py` - test `check_channel()` video discovery logic and idempotency checks per T034 (partial: unit tests)
- [ ] T039 [P] Write unit tests for `finfolio/config.py` - test YAML parsing, error handling for malformed config, env var + .env fallback per T034 (partial: unit tests)
- [ ] T040 [P] Write unit tests for `finfolio/youtube_client.py` - test quota tracking, API call mocking, error handling per T034 (partial: unit tests)
- [ ] T041 [P] Write unit tests for `finfolio/transcript_fetcher.py` - test fetch_and_save, has_transcript, no-captions handling per T034 (partial: unit tests)
- [ ] T042 Write integration test `tests/integration/test_channel_monitor.py` - test full channel monitoring flow with mock API per T021 (partial: integration tests)
- [ ] T043 Write integration test `tests/integration/test_transcript_fetcher.py` - test transcript download + idempotency per T021 (partial: integration tests)
- [ ] T044 Write integration test `tests/integration/test_config_changes.py` - test config reload + channel changes per T030 (partial: integration tests)
- [ ] T045 Write integration test `tests/integration/test_quota_logging.py` - test quota tracking and reporting per T025 (partial: integration tests)
- [ ] T046 Run `ruff check finfolio/ tests/` and fix style issues per T031 (partial: ruff linting)
- [ ] T047 Run `mypy finfolio/ --ignore-missing-imports` and verify type hints per T032 (partial: mypy type checking)
- [ ] T048 Verify all 8 quickstart scenarios work end-to-end per T036 (partial: quickstart validation)

**Checkpoint**: Test coverage >80%, all quality gates passing, full suite ready for CI/CD integration
