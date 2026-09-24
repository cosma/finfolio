# Implementation Plan: YouTube Channel Monitoring and Transcript Ingestion

**Branch**: `001-youtube-transcript-fetch` | **Date**: 2026-09-24 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/001-youtube-transcript-fetch/spec.md`

## Summary

Build a channel monitoring and transcript ingestion module (`finfolio fetch` CLI command) that automatically discovers new videos from configured YouTube financial channels and downloads their transcripts with timestamp markers using the official YouTube Data API v3. The module provides idempotent daily ingestion with state persistence and structured JSON logging. Transcripts with timestamps are persisted to `storage/transcripts/{video_id}.txt` in MM:SS format, enabling fact-checkers to link findings back to specific moments in the video.

**Technical Approach**:
- Python 3.11+ library/CLI tool using Click for the `finfolio fetch` command
- `google-api-python-client` wraps YouTube Data API v3 (search, captions.list, captions.download) — official API only per Constitution Principle VI
- Service account OAuth2 authentication (JSON credentials file via `GOOGLE_APPLICATION_CREDENTIALS` env var) — production-grade credential model
- Centralized `finfolio/storage.py` module abstracts all filesystem I/O (transcript save/load, state file, lock file)
- Configuration-driven: `channels.yaml` lists channel IDs and display names (editable without code changes)
- State file (`storage/.finfolio-state.json`) tracks last-fetch timestamp per channel for efficient delta queries
- Lock file (`storage/.finfolio.lock`) prevents concurrent runs
- Structured JSON logging to stdout; API quota tracked for all operations (search, captions)

## Technical Context

**Language/Version**: Python 3.11+

**Primary Dependencies**: 
- `google-api-python-client` (YouTube Data API v3 client for search, captions.list, captions.download)
- `google-auth` (service account OAuth2 authentication)
- `pyyaml` (channels.yaml parsing)
- `click` (CLI framework for `finfolio fetch` command)

**Storage**: Filesystem-based
- `storage/transcripts/{video_id}.txt` — raw transcripts
- `storage/.finfolio-state.json` — last-fetch timestamp per channel (JSON)
- `storage/.finfolio.lock` — exclusive lock file (presence indicates running fetch)
- `channels.yaml` — configuration file (project root or config directory)

**Testing**: pytest with pytest-cov (unit tests, integration tests with mock YouTube API)

**Target Platform**: Linux/macOS server (CLI tool), scheduled or manual invocation

**Project Type**: CLI tool / library module (part of larger finfolio system)

**Performance Goals**: 
- Full run on 10 channels completes in under 5 minutes (SC-002)
- Transcript fetching is fast and lightweight (youtube-transcript-api has minimal overhead)

**Constraints**: 
- 8 GB RAM, 2 GB Docker VM available (use lean dependencies, no large ML models)
- Transcript fetching uses youtube-transcript-api (lightweight, no OAuth setup required) while video discovery uses official YouTube Data API v3 search (Principle VI: Reliability Over Cleverness)

**Scale/Scope**: 
- Start with ~10 channels; system should handle up to 50+ channels without degradation
- Expected throughput: 2-3 new videos per channel per week (20-30 videos/week across ~10 channels)

## Constitution Check

**GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.**

### FinFolio Constitution Compliance

| Principle | Requirement | Plan Compliance | Status |
|-----------|-------------|-----------------|--------|
| **I. Accuracy Over Speed** | Claims verified before reporting | Not applicable to ingestion module (downstream responsibility) | ✅ N/A |
| **II. No Financial Advice** | Reports facts only, no recommendations | Not applicable to ingestion module | ✅ N/A |
| **III. Facts vs. Forecasts** | Separate opinion from factual claims | Not applicable to ingestion module | ✅ N/A |
| **IV. Transparency About Method** | State transcript source in reports | Not applicable to ingestion module (source implicit: video ID) | ✅ N/A |
| **V. Monetization Awareness** | Disclose promoted products | Not applicable to ingestion module | ✅ N/A |
| **VI. Reliability Over Cleverness** | All YouTube data MUST use official YouTube Data API v3; no scraping | ✅ Plan uses google-api-python-client exclusively for search and captions (official API v3); service account OAuth2 is the standard production-grade authentication model | ✅ PASS |
| **VII. Resource & Cost Discipline** | Stay under 10K units/day; log quota usage; use Haiku default; cost monitoring | ✅ Plan includes quota logging per run, state file for efficient queries, lock file for safe concurrent access; service account approach enables cost monitoring at scale | ✅ PASS |

**Gate Result**: ✅ **PASS** — Plan fully complies with Constitution Principles VI and VII (others not applicable to ingestion scope). Quota tracking and official API use are explicit requirements.

## Project Structure

### Documentation (this feature)

```text
specs/001-youtube-transcript-fetch/
├── spec.md                  # Feature specification
├── plan.md                  # This file (implementation plan)
├── research.md              # Phase 0 output (technical research)
├── data-model.md            # Phase 1 output (entities, state schema)
├── contracts/               # Phase 1 output (CLI contract)
│   └── cli-contract.md      # finfolio fetch command interface
├── quickstart.md            # Phase 1 output (validation/run guide)
├── checklists/
│   └── requirements.md      # Quality validation checklist
└── tasks.md                 # Phase 2 output (task breakdown for implementation)
```

### Source Code (repository root)

```text
finfolio/
├── __init__.py
├── cli.py                   # CLI entry point (finfolio fetch command)
├── channel_monitor.py       # Video discovery logic (search for new videos per channel)
├── transcript_fetcher.py    # Caption download logic (fetch transcripts via API)
├── storage.py               # Filesystem abstraction (save_transcript, has_transcript, state I/O, lock management)
├── youtube_client.py        # YouTube API wrapper (quota tracking, search, captions)
└── config.py                # Configuration loading (channels.yaml parsing)

tests/
├── unit/
│   ├── test_storage.py
│   ├── test_channel_monitor.py
│   ├── test_transcript_fetcher.py
│   ├── test_youtube_client.py
│   └── test_config.py
├── integration/
│   └── test_cli_fetch.py    # End-to-end CLI test with mock YouTube API
└── conftest.py              # pytest fixtures (mock API, temp storage dir)

channels.yaml               # Configuration file (channel IDs, display names)
.env.example                # Template for local development (YOUTUBE_API_KEY)
```

**Structure Decision**: Single-module CLI tool integrated into the larger finfolio package. No multi-package or separate frontend/backend needed at this stage. All filesystem I/O is centralized in `storage.py` to support future extensions (data persistence, caching, etc.).

---

## Phase 0: Research & Clarification

**Status**: No NEEDS CLARIFICATION markers remaining in Technical Context (all resolved via /speckit-clarify).

**Resolved Items**:
- API credential handling: Environment variable (`YOUTUBE_API_KEY`) + optional `.env` file (both supported per user choice in clarification Q1)
- Concurrent execution: Lock file pattern confirmed (clarification Q2)
- State persistence: State file with last-fetch timestamp per channel (clarification Q1)
- Logging: Structured JSON to stdout (clarification Q2)
- Partial file handling: .tmp pattern for atomic writes (clarification Q3)

**Research Output**: No additional research artifacts needed; all technical decisions are documented in spec and clarifications. Proceed to Phase 1.

---

## Phase 1: Design & Contracts

### 1. Data Model

**File**: `data-model.md` (to be generated)

**Entities**:

- **Channel** (in-memory concept, no persistent storage in this module)
  - Fields: `channel_id` (str, YouTube channel ID), `display_name` (str), `last_fetch_timestamp` (ISO8601)
  - Uniqueness: channel_id is unique key
  - Lifecycle: Loaded from `channels.yaml` at startup; `last_fetch_timestamp` updated in state file after each fetch

- **Video** (in-memory concept during fetch)
  - Fields: `video_id` (str), `title` (str), `channel_id` (str), `published_at` (ISO8601), `caption_available` (bool)
  - Uniqueness: video_id is globally unique
  - Lifecycle: Discovered via API search; checked for existing transcript; downloaded if new

- **Transcript** (filesystem entity)
  - Storage: `storage/transcripts/{video_id}.txt`
  - Format: UTF-8 plain text with timestamp markers in MM:SS format (e.g., "00:45 Caption text here")
  - Timestamps sourced from official YouTube Data API v3 captions, enabling fact-checkers to construct YouTube jump-links (youtu.be/{video_id}?t=SECONDS)
  - Lifecycle: Created once per video; never overwritten (checked via `has_transcript(video_id)`)

- **State File** (filesystem entity)
  - Path: `storage/.finfolio-state.json`
  - Schema: `{ "channels": { "channel_id": { "last_fetch": "2026-09-24T10:00:00Z" } } }`
  - Lifecycle: Created on first run; updated after each channel fetch; persists across runs for efficiency

- **Lock File** (filesystem entity)
  - Path: `storage/.finfolio.lock`
  - Format: Simple file (presence indicates running process, no content needed)
  - Lifecycle: Created at fetch startup; deleted at completion (success or failure)

### 2. Interface Contracts

**File**: `contracts/cli-contract.md` (to be generated)

**CLI Command**: `finfolio fetch`

```
Usage:
  finfolio fetch [OPTIONS]

Options:
  --config FILE             Path to channels.yaml config file (default: ./channels.yaml)
  --help                    Show this help message

Environment Variables:
  YOUTUBE_API_KEY          YouTube Data API key (required; set via env var or .env file)

Exit Codes:
  0                         Success (all channels fetched, transcripts saved)
  1                         General error (configuration, API auth failure, etc.)
  2                         Another fetch is already running (lock file present)

Output (STDOUT):
  Structured JSON logging (one object per line):
    {
      "timestamp": "2026-09-24T10:15:30Z",
      "event": "fetch_start" | "fetch_channel" | "download_transcript" | "fetch_complete" | "error",
      "channel_id": "UCxxxxx" (if applicable),
      "video_id": "dQw4w9WgXcQ" (if applicable),
      "status": "success" | "skipped" | "failed",
      "quota_units": 100 (only for search operations; transcript fetching does not consume quota),
      "message": "string"
    }

Exit Behavior:
  - If YOUTUBE_API_KEY missing: log warning and exit(1)
  - If lock file exists: log error "Another fetch is running..." and exit(2)
  - If channels.yaml invalid: log error with YAML details and exit(1)
  - If any channel's API call fails: log error for that channel, continue to next channel, exit(0) with warnings
  - If quota exhausted mid-run: log warning, stop API calls, exit(0) with logged units consumed

Example Run:
  $ YOUTUBE_API_KEY=abc123... finfolio fetch
  {"timestamp": "2026-09-24T10:15:30Z", "event": "fetch_start", "status": "success"}
  {"timestamp": "2026-09-24T10:15:31Z", "event": "fetch_channel", "channel_id": "UCxxxxx", "status": "success", "new_videos": 2}
  {"timestamp": "2026-09-24T10:15:45Z", "event": "download_transcript", "video_id": "dQw4w9WgXcQ", "status": "success"}
  {"timestamp": "2026-09-24T10:16:00Z", "event": "fetch_complete", "status": "success", "quota_units": 87}
```

### 3. Quickstart Validation Guide

**File**: `quickstart.md` (to be generated)

**Validation Scenarios**:

1. **CLI help and version**: `finfolio fetch --help` returns usage info without errors
2. **Missing API key**: Running without `YOUTUBE_API_KEY` logs error and exits(1)
3. **Invalid channels.yaml**: Running with malformed YAML logs error and exits(1)
4. **Lock file concurrency**: Two concurrent `finfolio fetch` calls; second exits(2) with lock error
5. **Successful single fetch**: Run with valid config and API key; transcripts are saved to `storage/transcripts/`, quota is logged
6. **Idempotency**: Run twice in succession; second run fetches zero new transcripts (all already stored)
7. **Partial failure**: One channel's API call fails; fetch continues for other channels; exits(0) with warning
8. **Timestamps in transcripts**: Verify fetched transcripts contain MM:SS timestamp markers that fact-checkers can use to construct YouTube jump-links
9. **Quota logging**: After run, verify quota units are logged in JSON output (search operations only; transcript fetching has no quota cost)

---

## Complexity Tracking

> No Constitution violations. No complexity exceptions needed.

---

## Next Steps

1. **Phase 0 output ready**: No additional research needed (all technical decisions clarified).
2. **Phase 1 artifacts**: Generate `research.md`, `data-model.md`, `contracts/cli-contract.md`, `quickstart.md` in `specs/001-youtube-transcript-fetch/`.
3. **Phase 2**: Run `/speckit-tasks` to break Phase 1 design into executable, dependency-ordered tasks.
4. **Phase 3**: Run `/speckit-implement` to write source code and tests.
