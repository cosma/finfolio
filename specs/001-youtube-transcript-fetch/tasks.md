# Tasks: YouTube Channel Monitoring and Transcript Ingestion

**Input**: Design documents from `specs/001-youtube-transcript-fetch/`

**Prerequisites**: plan.md (tech stack), spec.md (user stories with priorities)

**Organization**: Tasks grouped by user story (US1-US4) to enable independent implementation and testing

**Testing Approach**: Tests are included where they validate critical flows; TDD approach for fact-checking logic compliance

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story (US1, US2, US3, US4)
- Exact file paths included in descriptions

## Path Conventions

All paths relative to repository root (`/Users/cosmin/Projects/cosma/finfolio/`)

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
├── unit/              # Unit tests
└── integration/       # Integration tests

channels.yaml          # Configuration file (root)
docs/SERVICE_ACCOUNT_SETUP.md  # Service account setup guide
```

---

## Phase 1: Setup (Project Initialization)

**Purpose**: Create project structure and configure dependencies

- [x] T001 Initialize pyproject.toml with Python 3.11+ requirements and dependencies (Click, google-api-python-client, google-auth, pyyaml)
- [x] T002 Create finfolio/ package directory structure: `__init__.py`, `cli.py`, `config.py`, `storage.py`, `youtube_client.py`, `channel_monitor.py`, `transcript_fetcher.py`
- [x] T003 [P] Create tests/ directory with `conftest.py`, `unit/`, `integration/` subdirectories
- [x] T004 [P] Set up .gitignore: exclude service account JSON key files, `.env`, `*.pyc`, `__pycache__`, `venv/`, `storage/`, `.pytest_cache`
- [x] T005 [P] Create `channels.yaml` template with example channel entries (format: `channel_id` and `display_name`)
- [x] T006 [P] Configure ruff linting in pyproject.toml with finfolio-specific rules

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that ALL user stories depend on

**⚠️ CRITICAL**: No user story work can begin until this phase is 100% complete

- [x] T007 Implement `finfolio/storage.py` module with:
  - `save_transcript(video_id: str, text: str) -> None` — write to `storage/transcripts/{video_id}.txt` with `.tmp` pattern (atomic writes)
  - `has_transcript(video_id: str) -> bool` — check file existence
  - `ensure_storage_dir() -> None` — create `storage/transcripts/` if missing
  - `acquire_lock() -> bool` — create `storage/.finfolio.lock`; return False if already locked
  - `release_lock() -> None` — delete lock file
  - `load_state() -> dict` — load `storage/.finfolio-state.json`; return `{}` if missing
  - `save_state(state: dict) -> None` — write state file atomically
  - `save_video_metadata(video_id: str, title: str, channel_id: str, published_at: str) -> None` — store video metadata
  - `get_video_metadata(video_id: str) -> dict | None` — retrieve video metadata
  - All functions include structured JSON logging via `_log_operation()`

- [x] T008 Implement `finfolio/youtube_client.py` module with:.py` module with:
  - `YouTubeClient` class constructor: accepts service account credentials (via google.auth library)
  - `search_channel_videos(channel_id: str, after_timestamp: datetime | None) -> list` — call YouTube API v3 search().list, return video IDs and metadata
  - `fetch_captions(video_id: str) -> str | None` — call official YouTube API v3 captions().list and captions().download, extract timing data, format as "MM:SS caption text", return formatted transcript or None if unavailable
  - `get_quota_units_used() -> dict` — track and return quota units per operation type (search, caption.list, caption.download)
  - Quota accounting for each API call (YouTube API reports units in response metadata)
  - Structured JSON logging for all API operations

- [x] T009 Implement `finfolio/config.py` module with:.py` module with:
  - `load_config(config_path: str) -> list` — parse `channels.yaml`, return list of dicts with `channel_id` and `display_name`
  - `load_credentials() -> google.auth.service_account.Credentials` — read service account JSON from `GOOGLE_APPLICATION_CREDENTIALS` env var; raise error if missing or invalid
  - Structured JSON logging for config load events
  - Error handling for malformed YAML and invalid credentials

- [x] T010 Implement `finfolio/cli.py` module with:.py` module with:
  - Click CLI setup with `@click.group()` decorator
  - Global options: `--config` for channels.yaml path (default: `./channels.yaml`)
  - Error handling and exit codes (0=success, 1=error, 2=locked)
  - Structured JSON logging to stdout (one object per line)

- [x] T011 Create pytest fixtures in `tests/conftest.py`:
  - `mock_youtube_client` — mock GoogleAPIClient with predefined search/captions responses
  - `temp_storage_dir` — temporary directory for `storage/` during tests
  - `temp_config_file` — temporary `channels.yaml` for tests
  - Sample video/caption data for tests

**Checkpoint**: Foundation complete — all user stories can now implement independently

---

## Phase 3: User Story 1 - Monitor Channels for New Videos (Priority: P1) 🎯

**Goal**: System discovers new videos from configured YouTube channels using official YouTube Data API v3 search

**Independent Test**: Configure channels.yaml, run `finfolio fetch`, verify API is queried for each channel and new video metadata is identified and logged

### Implementation for User Story 1

- [x] T012 [P] [US1] Implement `finfolio/channel_monitor.py` module with:.py` module with:
  - `ChannelMonitor` class with `__init__(youtube_client, storage)`
  - `check_channel(channel_id: str, display_name: str, last_fetch: datetime | None) -> list` — call `youtube_client.search_channel_videos()` with timestamp filter, return discovered videos
  - `is_new_video(video_id: str) -> bool` — check against `storage.has_transcript()` for idempotency
  - Structured JSON logging for discovery process

- [x] T013 [P] [US1] Implement state persistence helpers in `finfolio/storage.py`:
  - Extend with `update_channel_last_fetch(channel_id: str, timestamp: datetime) -> None`
  - Extend with `get_channel_last_fetch(channel_id: str) -> datetime | None`
  - State file schema: `{"channels": {"channel_id": {"last_fetch": "ISO8601"}}}`

- [x] T014 [US1] Add `finfolio fetch` command to `finfolio/cli.py`:
  - Create Click command `@click.command('fetch')`
  - Initialize `YouTubeClient` (with service account credentials from config.load_credentials)
  - Initialize `ChannelMonitor`, storage helpers
  - Acquire lock (exit(2) if locked)
  - Load config via `config.load_config()`
  - For each channel:
    - Get last-fetch timestamp from state
    - Call `channel_monitor.check_channel()`
    - Log discovery results as JSON (event: fetch_channel, status, new_videos count)
  - Release lock on completion
  - Exit codes: 0=success, 1=error, 2=locked

- [x] T015 [US1] Add service account credential validation to CLI:
  - Call `config.load_credentials()` at start of fetch command
  - Log error and exit(1) if `GOOGLE_APPLICATION_CREDENTIALS` env var is missing or credentials file is invalid
  - Validate that service account has YouTube Data API v3 enabled (via scope check if possible)

- [x] T016 [US1] Write integration test `tests/integration/test_channel_monitor.py`:
  - Test: `finfolio fetch` with valid channels.yaml queries API for each channel
  - Test: Idempotency — running fetch twice doesn't discover same video twice
  - Test: Empty channel (no new videos) returns gracefully
  - Test: Invalid channel ID logs error and continues (fetch processes other channels)
  - Use mock YouTube client from conftest

**Checkpoint**: User Story 1 complete. Channels are monitored, new videos discovered, state persisted. Test independently.

---

## Phase 4: User Story 2 - Fetch and Store Transcripts with Timestamps (Priority: P1)

**Goal**: System downloads captions from official YouTube Data API v3 and persists transcripts with MM:SS timestamp markers

**Independent Test**: After discovering videos in US1, fetch transcript for each video; verify files exist at `storage/transcripts/{video_id}.txt` with correct MM:SS timestamp format

### Implementation for User Story 2

- [x] T017 [P] [US2] Implement `finfolio/transcript_fetcher.py` module with:
  - `TranscriptFetcher` class with `__init__(youtube_client, storage)`
  - `fetch_and_save(video_id: str) -> bool` — call `youtube_client.fetch_captions()`, save via `storage.save_transcript()` using `.tmp` pattern, return True on success
  - `has_transcript(video_id: str) -> bool` — wrapper around `storage.has_transcript()` for idempotency
  - Handle missing captions gracefully: log "no transcript available" and return False
  - Structured JSON logging for each download attempt

- [x] T018 [US2] Implement timestamp formatting in `youtube_client.fetch_captions()`:
  - Call YouTube API v3 captions().list to get available captions
  - Call captions().download with tfmt='srt' to get SubRip format (includes timing)
  - Parse caption data: YouTube returns XML with `start` attribute (time in seconds)
  - Convert timestamp to MM:SS format (e.g., 45 seconds → "00:45")
  - Combine with caption text: "MM:SS caption text"
  - Join all segments with newlines to create final transcript
  - Example output: "00:15 Welcome to the video.\n00:30 Today we discuss...\n01:45 First point..."
  - Structured JSON logging showing transcript fetched with timestamp markers

- [x] T019 [US2] Extend `finfolio fetch` command to download transcripts:
  - After `channel_monitor.check_channel()` discovers videos, initialize `TranscriptFetcher`
  - Save video metadata: call `storage.save_video_metadata()` before transcript download
  - For each discovered video:
    - Check `transcript_fetcher.has_transcript()` (idempotency check)
    - If transcript exists, skip (log event: download_transcript, status: skipped)
    - If not exists, call `transcript_fetcher.fetch_and_save()`
    - Log result as JSON (event: download_transcript, status: success/failed, video_id)
  - If video has no captions, log event with status: no_captions
  - Continue processing other videos if one fails

- [x] T020 [US2] Add cleanup of leftover `.tmp` files:
  - At startup (in CLI command), scan `storage/transcripts/` for `*.tmp` files
  - Delete any `.tmp` files found
  - Log cleanup event as JSON

- [x] T021 [US2] Write integration test `tests/integration/test_transcript_fetcher.py`:
  - Test: `finfolio fetch` downloads transcripts for new videos
  - Test: Idempotency — existing transcripts are skipped on second run
  - Test: Video without captions is logged as unavailable and fetch continues
  - Test: `.tmp` files are cleaned up on startup
  - Test: Transcript files contain captions with MM:SS timestamp markers
  - Test: Timestamps can be converted to YouTube jump-link format (youtu.be/VIDEO_ID?t=SECONDS)
  - Use mock YouTube client from conftest

**Checkpoint**: User Story 2 complete. Transcripts downloaded and persisted with timestamps. Test independently.

---

## Phase 5: User Story 3 - Log API Quota Usage (Priority: P2)

**Goal**: System tracks and logs YouTube Data API quota consumption per run to stay under 10,000-unit daily ceiling

**Independent Test**: Run `finfolio fetch`, verify quota units are logged in JSON output for search, caption.list, and caption.download; sum units across operations to confirm they stay under 10,000-unit limit

### Implementation for User Story 3

- [x] T022 [US3] Extend_units_used()` to track:
  - Units consumed per operation type (search, caption.list, caption.download)
  - Total units for the run
  - Store in instance variable (e.g., `self.quota_usage: dict`)
  - YouTube API returns quota units in response metadata for each call

- [x] T023 [US3] Extend to report quota:
  - After processing all channels, log final quota report as JSON
  - Log event: fetch_complete, status: success, quota_units: total
  - Structured JSON logging with breakdown: `{"search": X, "caption.list": Y, "caption.download": Z, "total": N}`

- [x] T024 [US3] Add quota check before batch operations:
  - Before processing next channel/video, check remaining quota
  - Estimate quota needed: search ~100 units per channel, caption.list ~50 units per video, caption.download ~200 units per video
  - If insufficient quota for safe operation, log warning and stop (graceful backoff)
  - Exit(0) with warning, not error

- [x] T025 [US3] Write integration_logging.py`:
  - Test: `finfolio fetch` logs total quota units consumed per run
  - Test: Quota breakdown shows all operation types with correct units (search, caption.list, caption.download)
  - Test: Multiple runs sum correctly toward 10,000-unit daily ceiling
  - Test: If quota exhausted mid-run, fetch logs warning and stops gracefully
  - Use mock YouTube client with predefined quota values for each operation

**Checkpoint**: User Story 3 complete. Quota usage tracked and logged. Operator can monitor API cost.

---

## Phase 6: User Story 4 - Configure Channels Without Code Changes (Priority: P2)

**Goal**: Operators maintain channels.yaml file to manage YouTube financial channels without editing code

**Independent Test**: Edit channels.yaml to add/remove channels, rerun fetch, verify new configuration is applied correctly without code deployment

### Implementation for User Story 4

- [x] T026 [US4] Create validation for `channels.yaml`:
  - In `config.load_config()`, validate YAML syntax and required fields
  - Require fields: `channel_id`, `display_name`
  - Log clear error messages for malformed YAML (e.g., "Missing required field: channel_id in channel 2")
  - Continue on invalid channels but log warnings

- [x] T027 [US4] Add configuration validation to CLI:
  - At startup, validate channels.yaml before any API calls
  - Log error and exit(1) if configuration is invalid
  - Log summary: "Loaded N channels: [display names]"

- [x] T028 [US4] Write unit test `tests/unit/test_config.py`:
  - Test: `load_config()` with valid channels.yaml returns list of dicts
  - Test: `load_config()` with missing channel_id logs error for that channel
  - Test: `load_config()` with malformed YAML raises error with clear message
  - Test: `load_config()` with empty channels.yaml returns empty list

**Checkpoint**: User Story 4 complete. Channels are configuration-driven, no code changes needed.

---

## Phase 7: Service Account Setup & Documentation (Supporting Infrastructure)

**Goal**: Provide operators with clear guidance for creating and configuring service account credentials (Constitution Principle VI compliance)

**Independent Test**: Operator follows setup guide, creates a service account in Google Cloud, generates credentials file, sets `GOOGLE_APPLICATION_CREDENTIALS`, and runs `finfolio fetch` successfully

### Implementation for Service Account Setup

- [x] T029 Create service account setup guide at `docs/SERVICE_ACCOUNT_SETUP.md`:
  - Step-by-step instructions for:
    1. Creating a Google Cloud project
    2. Enabling YouTube Data API v3 for the project
    3. Creating a service account in the GCP Console
    4. Generating a JSON key file for the service account
    5. Downloading and storing the key file securely (.gitignore required)
    6. Setting `GOOGLE_APPLICATION_CREDENTIALS` environment variable
  - Local development instructions (path to JSON key file)
  - Production deployment instructions (GitHub Secrets, cloud platform env vars)
  - Troubleshooting section for common credential errors (403 Forbidden, 401 Unauthorized)

- [x] T030 Update is used for other configs):
  - Add note: "For YouTube authentication, set GOOGLE_APPLICATION_CREDENTIALS env var directly (not via .env)"
  - Add example comment: `# GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account-key.json`
  - Document that service account key file should NOT be in version control

- [ ] T031 Add service account credential validation unit test in `tests/unit/test_config.py`:
  - Test: `load_credentials()` with valid service account JSON file — returns credentials object
  - Test: `load_credentials()` with missing `GOOGLE_APPLICATION_CREDENTIALS` env var — raises error with clear message
  - Test: `load_credentials()` with invalid/malformed JSON file — raises error with clear message
  - Test: Error messages guide operator to SERVICE_ACCOUNT_SETUP.md

**Checkpoint**: Service account setup is documented and validated. Operators have clear path to configure credentials (Constitution Principle VI compliance).

---

## Phase 8: Polish & Cross-Cutting Concerns

**Purpose**: Final improvements and validation across all user stories

- [ ] T032 [P] Add comprehensive docstrings to all public functions per PEP 257
- [ ] T033 [P] Add type hints to all function signatures (Python 3.11+ style)
- [ ] T034 [P] Run mypy type checking: `mypy finfolio/` should pass with no errors
- [ ] T035 [P] Run ruff linting: `ruff check finfolio/ tests/` should pass
- [ ] T036 [P] Run ruff formatter: `ruff format finfolio/ tests/`
- [ ] T037 Run full test suite: `pytest tests/` should pass with 100% coverage on finfolio/
- [ ] T038 Update project README.md with:
  - Feature overview
  - Quick start guide (setup, run, example output)
  - Architecture diagram (storage layout, API flow)
  - Contribution guidelines
- [ ] T039 Run quickstart.md validation (if quickstart.md exists in spec):
  - Verify all documented flows work as specified
  - Test edge cases mentioned in spec

**Checkpoint**: Code quality validated, tests passing, documentation complete.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion — BLOCKS all user stories
- **User Stories (Phases 3-6)**: All depend on Foundational completion
  - User stories can proceed in parallel (if staffed) or sequentially
  - US1 and US2 are both P1 and can start simultaneously after Phase 2
  - US3 and US4 are P2 and can start after US1/US2 (or in parallel if capacity)
- **Service Account Setup (Phase 7)**: Can start after Phase 1 (independent of functional user stories, but required for production)
- **Polish (Phase 8)**: Depends on all desired user stories being complete

### Within Each User Story

- Foundational infrastructure tasks first
- Models/entities before services
- Services before CLI integration
- Integration tests after implementation

### Parallel Opportunities

- **Phase 1 Setup**: All [P] tasks can run in parallel
  - T003, T004, T005, T006 (project structure, gitignore, configs, linting)
- **Phase 2 Foundational**: All [P] tasks can run in parallel once Phase 1 complete
  - This phase is critical path — must be 100% done before Phase 3
- **Phase 3 (US1)**: After Phase 2 complete, all [P] tasks in US1 can run in parallel
  - T012 (ChannelMonitor) can run in parallel with other setup
- **Phase 4 (US2)**: After Phase 2 complete, [P] tasks can run in parallel
  - T017 (TranscriptFetcher) can run in parallel with T018 (timestamp formatting)
- **Phases 3 & 4 Together**: Once Phase 2 complete, US1 and US2 can both proceed in parallel (different files, no dependencies)
- **Phase 7 (Service Account)**: Can run in parallel with user story work after Phase 1
- **Phase 8 Polish**: Can start once Phase 2 is done, runs in parallel with user stories

---

## Parallel Example: Full Feature

```bash
# Setup phase (sequential, fast):
T001 → T002 → [T003, T004, T005, T006 in parallel]

# Foundational phase (sequential, critical path):
[T007, T008, T009, T010, T011] — all must complete before user stories

# User Stories in parallel (if 3+ developers):
Developer A: T012 → T013 → T014 → T015 → T016 (US1)
Developer B: T017 → T018 → T019 → T020 → T021 (US2)
Developer C: T022 → T023 → T024 → T025 (US3)

# Service Account setup (in parallel with stories):
Developer D: T029 → T030 → T031 (parallel with stories)

# Polish phase (after all stories done):
[T032, T033, T034, T035, T036] in parallel → T037 → T038 → T039
```

---

## Implementation Strategy

### MVP First (User Stories 1 & 2 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (CRITICAL)
3. Complete Phase 3: User Story 1 — Monitor channels
4. Complete Phase 4: User Story 2 — Fetch transcripts with timestamps
5. **STOP and VALIDATE**: Test both stories independently and together
6. Complete Phase 7: Service Account Setup (Constitution compliance)
7. Deploy/demo — **MVP complete with core functionality + official API compliance**

### Full Feature (All 4 User Stories)

Continue after MVP:
1. Complete Phase 5: User Story 3 — Quota logging
2. Complete Phase 6: User Story 4 — Configuration management
3. Complete Phase 8: Polish & validation
4. Deploy/demo — **Full feature ready**

### Recommended Staffing

- **Single developer**: Follow sequential order (Setup → Foundational → US1 → US2 → US3 → US4 → Service Account → Polish)
- **Two developers**: One does Setup + Foundational + US1, other does Service Account setup in parallel → both do US2 → both do Polish
- **Three+ developers**: Parallel all after Foundational (US1, US2, US3 in parallel; Service Account in parallel)

---

## Notes

- [P] tasks = different files, no dependencies — can run in parallel
- [Story] label maps task to specific user story for traceability
- Each user story should be independently completable and testable
- Service account setup is required for Constitution Principle VI compliance (official YouTube API v3 only)
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- Timestamps in transcripts enable fact-checkers to construct YouTube jump-links (youtu.be/VIDEO_ID?t=SECONDS) for verification
