# Feature Specification: YouTube Channel Monitoring and Transcript Ingestion

**Feature Branch**: `001-youtube-transcript-fetch`

**Created**: 2026-09-24

**Status**: Draft

**Input**: Build the channel monitoring and transcript ingestion module for FinFolio. Maintain a channels.yaml config file listing about 10 YouTube financial/investment advisor channels (channel ID and display name), editable without touching code. Check each configured channel daily for new videos, using the YouTube Data API v3 search endpoint (roughly 2-3 new videos per channel per week expected). For each new video not already present in storage/transcripts/, fetch its captions using youtube-transcript-api and write the transcript to storage/transcripts/{video_id}.txt with timestamp markers at each caption segment in the format "MM:SS" so that fact-checking summaries can link back to specific moments in the video via YouTube timestamps (e.g., youtu.be/VIDEO_ID?t=90). Skip videos whose transcript file already exists, so runs are idempotent and safe to repeat daily. Log YouTube API quota usage for video search per run (transcript fetching via youtube-transcript-api does not consume YouTube API quota). Authenticate video search using API key. Expose this as a CLI command, e.g. finfolio fetch, that can be triggered manually or on a schedule. Out of scope for this module: summarization, fact-checking, and anything downstream of raw transcript storage.

## Clarifications

### Session 2026-09-24 (Timestamp Feature & Simplified Transcript Fetching)

**Transcript Fetching Clarifications**:
- Q: Should transcripts use official YouTube Data API v3 captions endpoints or youtube-transcript-api?
  → A: Use youtube-transcript-api for simplicity and ease of setup. It handles caption extraction without service account complexity. Video search still uses YouTube Data API v3 for reliability.
- Q: How should timestamps be formatted for fact-checking links?
  → A: MM:SS format (e.g., 03:45) prefixing each caption segment. Fact-checkers convert to seconds and append `?t=SECONDS` to YouTube URLs for jump-to-time links.
- Q: When youtube-transcript-api fails to fetch a transcript, should the system retry on next run or skip permanently?
  → A: Skip with logged error; next `finfolio fetch` run will retry (allows transient failures to self-heal without blocking current run).

**Earlier Clarifications (from prior session)**:

- Q: How should the system track "new videos since last run"? → A: Store state file (`storage/.finfolio-state.json`) with last-fetch timestamp per channel + always check file existence before download (hybrid approach for both efficiency and safety)
- Q: What format and destination should logs use? → A: Structured JSON logs to stdout with optional file rotation
- Q: How should the system detect and handle partially-written transcript files? → A: Use `.tmp` extension during download; rename to final name only on successful completion; clean up any `.tmp` files on startup
- Q: How should the system handle YouTube API credentials securely? → A: Support both environment variable (`YOUTUBE_API_KEY`) and `.env` config file; document that `.env` must be in `.gitignore` and never committed to version control
- Q: How should the system handle concurrent execution (manual + scheduled runs)? → A: Use lock file (`storage/.finfolio.lock`) to prevent concurrent execution; exit with error if another fetch is running

## User Scenarios & Testing

### User Story 1 - Monitor channels for new videos (Priority: P1)

A FinFolio operator configures a set of YouTube financial channels in channels.yaml and runs `finfolio fetch` to discover new videos published since the last run. The system queries each channel using YouTube Data API v3 search endpoint, identifies videos not yet in the transcript storage, and prepares them for transcript fetching.

**Why this priority**: This is the core capability that enables the entire system. Without detecting new videos, there's nothing to transcribe or fact-check. This is the foundational workflow that must work reliably before any downstream features can operate.

**Independent Test**: Can be fully tested by configuring a test channel, running the fetch command, and verifying that new video metadata (IDs, titles, published dates) is correctly identified and stored. Delivers the ability to track new content.

**Acceptance Scenarios**:

1. **Given** channels.yaml with a configured YouTube channel, **When** `finfolio fetch` is executed, **Then** the system queries the YouTube Data API v3 search endpoint for the channel and returns a list of videos matching the search criteria (title, publication date)
2. **Given** a previously fetched video ID, **When** `finfolio fetch` is executed again, **Then** the system does not duplicate the video in its internal tracking (idempotent)
3. **Given** a channel with no new videos since the last run, **When** `finfolio fetch` is executed, **Then** the system returns an empty list for that channel without error
4. **Given** invalid channel configuration (malformed ID), **When** `finfolio fetch` is executed, **Then** the system logs the error for that channel and continues processing other channels

---

### User Story 2 - Fetch and store transcripts with timestamps (Priority: P1)

For each new video identified, the system automatically fetches its transcript using the youtube-transcript-api library and writes it to storage with timestamp markers. Each caption segment is prefixed with its timestamp in MM:SS format, enabling fact-checking workflows to link back to specific moments in the video. Transcripts persist on disk in a predictable location for downstream processing (summarization, fact-checking, indexing). Fact-checkers can extract transcript segments with MM:SS timestamps and construct YouTube jump-to-time links (youtu.be/VIDEO_ID?t=SECONDS) to verify claims directly in the video.

**Why this priority**: Transcript retrieval is the core data collection mechanism. Without reliable transcript storage with timestamps, operators cannot link fact-check findings back to the source video for verification. This must work before any analysis features can be built.

**Independent Test**: Can be fully tested by providing a known video ID, running fetch, and verifying that the transcript file exists at the expected path with correct content and timestamp markers. Delivers persistent, timestamped transcript storage.

**Acceptance Scenarios**:

1. **Given** a new video ID identified by the monitor, **When** `finfolio fetch` is executed, **Then** the system fetches the transcript and writes it to storage/transcripts/{video_id}.txt with timestamp markers
2. **Given** a transcript file, **When** the file is read, **Then** each caption segment is prefixed with a timestamp in MM:SS format (e.g., "00:45 This is the caption text")
3. **Given** a fact-checker reviewing a transcript, **When** they identify a claim at timestamp 02:30, **Then** they can construct a YouTube link (youtu.be/VIDEO_ID?t=150) to jump directly to that moment
4. **Given** a video that already has a transcript file, **When** `finfolio fetch` is executed again, **Then** the system skips that video (idempotent, no re-download)
5. **Given** a video without available transcripts on YouTube, **When** `finfolio fetch` is executed, **Then** the system logs this as "no transcript available" and skips to the next video without crashing
6. **Given** the transcript file for a video, **When** the file is read, **Then** it contains the caption text in chronological order with accurate timestamps

---

### User Story 3 - Log API quota usage (Priority: P2)

After each run of `finfolio fetch`, the system logs how many YouTube Data API quota units were consumed during that run. This enables tracking of API cost against the 10,000-unit daily budget and helps detect anomalies (e.g., quota-exhausting bugs).

**Why this priority**: Quota monitoring is essential for staying within YouTube API limits and avoiding unexpected service interruptions. It's not part of the core video/transcript flow but is critical for operational reliability and cost management (per FinFolio Constitution Principle VII).

**Independent Test**: Can be fully tested by running fetch on a known set of channels and verifying that a quota usage report is logged showing units consumed for search operations and caption downloads. Delivers visibility into API cost.

**Acceptance Scenarios**:

1. **Given** a completed run of `finfolio fetch`, **When** the run finishes, **Then** the system logs total quota units consumed (broken down by operation type: search, caption.list, caption.download)
2. **Given** accumulated quota usage over multiple runs, **When** quota is logged each run, **Then** the operator can sum daily usage to stay under the 10,000-unit ceiling
3. **Given** a run that exhausts remaining daily quota, **When** the system detects quota exhaustion, **Then** it logs a warning and gracefully stops further API calls

---

### User Story 4 - Configure channels without code changes (Priority: P2)

An operator maintains a channels.yaml file listing ~10 YouTube financial/investment channels (channel ID and display name). Adding, removing, or updating channels requires only editing this YAML file; no code deployment is needed.

**Why this priority**: Configuration-driven design keeps the system flexible and allows non-technical operators to manage the channel list. This reduces friction for onboarding new channels and removes the need to re-deploy code for operational changes.

**Independent Test**: Can be fully tested by editing channels.yaml, rerunning fetch, and verifying that the new configuration is applied correctly (new channels are queried, removed channels are skipped). Delivers operational agility.

**Acceptance Scenarios**:

1. **Given** an empty or outdated channels.yaml, **When** the file is updated with new channel IDs and display names, **Then** `finfolio fetch` uses the new configuration on the next run without code changes
2. **Given** channels.yaml with malformed YAML syntax, **When** `finfolio fetch` is executed, **Then** the system reports a clear error message indicating the configuration issue and exits gracefully
3. **Given** a channels.yaml with a channel ID that is no longer valid on YouTube, **When** `finfolio fetch` is executed, **Then** the system logs an error for that channel but continues processing other channels

---

### Edge Cases

- What happens if YouTube API rate limits are hit mid-run? (System should gracefully stop, log remaining quota, and inform operator)
- How does the system handle videos with no captions available? (Log as "no transcript available" and skip)
- What if youtube-transcript-api fails to fetch a transcript (network error, malformed data, etc.)? (Log as failed, skip with error message; next run will retry)
- What if the storage/transcripts/ directory doesn't exist? (System should create it automatically)
- How does the system behave if a transcript file is partially written (interrupted write)? (Skip the incomplete file on next run and re-download)
- What if the channels.yaml file is deleted or unreadable? (System reports error and halts)

## Requirements

### Functional Requirements

- **FR-001**: System MUST read YouTube Data API v3 key from the `YOUTUBE_API_KEY` environment variable on startup; if missing, log a warning and exit with error code
- **FR-002**: System MUST establish an exclusive lock (`storage/.finfolio.lock`) at startup; if another fetch process holds the lock, exit with error "Another fetch is running, please try again later"
- **FR-003**: System MUST release the lock file when the fetch completes (success or failure) to allow subsequent runs
- **FR-004**: System MUST read channel configuration from channels.yaml on startup (channel ID, display name)
- **FR-005**: System MUST maintain a state file (`storage/.finfolio-state.json`) tracking the last-fetch timestamp for each channel
- **FR-006**: System MUST query the YouTube Data API v3 search endpoint for each configured channel, filtering for videos published since that channel's last-fetch timestamp
- **FR-007**: System MUST track which video transcripts have already been fetched by checking storage/transcripts/{video_id}.txt file existence
- **FR-008**: System MUST skip videos whose transcript file already exists (idempotent behavior)
- **FR-009**: System MUST download transcripts using temporary `.tmp` files and rename to final name only after successful completion
- **FR-010**: System MUST clean up any leftover `.tmp` files on startup (from interrupted previous runs)
- **FR-011**: System MUST fetch captions using youtube-transcript-api library, which extracts timing data for each caption segment from YouTube transcripts
- **FR-012**: System MUST write transcript to storage/transcripts/{video_id}.txt with timestamp markers in MM:SS format, with each caption segment prefixed by its timestamp (format: "MM:SS Caption text here")
- **FR-012a**: System MUST preserve accurate timestamps from the transcript source so that fact-checkers can construct YouTube links (youtu.be/VIDEO_ID?t=SECONDS) to jump to specific moments in the video
- **FR-013**: System MUST log all operations as structured JSON to stdout (one object per line) including: timestamp, operation type, status, video/channel IDs, and quota units consumed
- **FR-014**: System MUST log API usage per run (quota tracking applies only to YouTube Data API v3 search operations; transcript fetching via youtube-transcript-api does not consume YouTube API quota)
- **FR-015**: System MUST expose a CLI command `finfolio fetch` that can be invoked manually or scheduled
- **FR-016**: System MUST continue processing other channels if one channel's API call fails
- **FR-017**: System MUST handle videos with no available captions gracefully (log as unavailable, skip)
- **FR-017a**: System MUST handle youtube-transcript-api fetch failures gracefully (log error with video ID and error message, skip to next video, allow retry on next run)
- **FR-018**: System MUST create the storage/transcripts/ directory if it does not exist
- **FR-019**: System MUST validate channels.yaml syntax on load and report configuration errors clearly
- **FR-020**: System MUST store video metadata in state file (`storage/.finfolio-state.json`) including: video ID, title, YouTube URL, published date, and channel ID for each fetched video
- **FR-021**: System MUST maintain a searchable index of fetched videos in state file organized by channel for easy reference and linking back to YouTube

### Key Entities

- **Channel**: Represents a YouTube channel with channel ID, display name, and last-fetch timestamp (metadata only, not stored persistently in this module)
- **Video**: Represents a YouTube video with video ID, title, channel ID, publish date, and caption availability status
- **Transcript**: A raw caption text file stored at storage/transcripts/{video_id}.txt, containing chronologically ordered captions from YouTube

## Success Criteria

### Measurable Outcomes

- **SC-001**: System fetches new transcripts for all configured channels (expect 2-3 new videos per channel per week) without manual intervention
- **SC-002**: System completes a full fetch run on 10 channels in under 5 minutes (includes API calls and transcript storage, assuming no rate limiting)
- **SC-003**: System runs are fully idempotent: repeating `finfolio fetch` twice in succession fetches zero transcripts the second time (all new videos from first run are already stored)
- **SC-004**: YouTube Data API quota usage for search operations is logged; transcript fetching does not consume YouTube API quota (uses youtube-transcript-api instead)
- **SC-005**: Non-critical failures (missing transcripts for one video, one channel unreachable) do not block processing of other channels; full run completes with logged warnings
- **SC-006**: Operator can add/remove channels by editing channels.yaml only; no code recompilation or deployment needed
- **SC-007**: All transcript files are readable as plain text UTF-8 and contain complete captions in chronological order with accurate timestamp markers (MM:SS format)
- **SC-008**: State file contains complete metadata for all fetched videos including title, URL, and published date; operator can easily construct YouTube links to watch videos
- **SC-009**: Fact-checkers can extract transcript segments with timestamps and construct jump-to-time YouTube links (youtu.be/VIDEO_ID?t=SECONDS) for direct video verification
- **SC-010**: Timestamp accuracy allows fact-checkers to resume transcript review from specific points and link fact-check findings back to source video moments

## Assumptions

- **Target User**: A FinFolio operator (could be automated scheduler or manual trigger by team member) with access to a machine where FinFolio CLI can run, with network access to YouTube API
- **Scope**: This module covers monitoring + transcript ingestion only. Summarization, fact-checking, report generation, and any downstream processing are explicitly out of scope
- **Trigger Mechanism**: `finfolio fetch` is triggered manually via CLI or via an external scheduler (cron, GitHub Actions, etc.). This module does not implement scheduling itself
- **Channel List**: Starting with ~10 channels; the system should handle up to 50+ channels without significant performance degradation
- **Transcript Format**: Transcripts are fetched via youtube-transcript-api library. Captions include timing data for each segment. Transcripts are stored with timestamp markers (MM:SS format) prefixing each caption segment to enable fact-checkers to link findings back to specific moments in the video. No cleaning, normalization, or deduplication of overlapping captions is performed in this module; raw caption text structure from YouTube is preserved with timing markers added
- **Error Recovery**: Failed API calls (e.g., rate limits, network errors) are logged but do not trigger retries within the same run; a future scheduled run will retry automatically
- **Configuration Format**: channels.yaml is a simple YAML file with channel entries; no environment-specific overrides or profile selection are needed
- **API Credentials**: YouTube Data API v3 search uses API key authentication via `YOUTUBE_API_KEY` environment variable. Transcript fetching via youtube-transcript-api does not require API credentials. The module assumes: (1) API key is valid and has YouTube Data API v3 search enabled, (2) API key is in `.gitignore` and never committed to version control, (3) operators use environment variables for production (GitHub Secrets, cloud deployment) and local files for development
- **Concurrent Execution Safety**: Only one `finfolio fetch` process can run at a time; exclusivity is enforced via a lock file (`storage/.finfolio.lock`); if a process is already running, new invocations exit immediately with an error message
- **Constitution Compliance**: Video search uses the official YouTube Data API v3 with API key authentication. Transcript fetching uses youtube-transcript-api, a stable community library that extracts publicly available caption data without circumventing YouTube's terms of service. This hybrid approach prioritizes reliability and ease of setup while maintaining respect for YouTube's data
- **State Persistence**: Last-fetch timestamp per channel is stored in `storage/.finfolio-state.json` to enable efficient delta queries (only fetching videos published since the last run). This state file is created automatically on first run
- **Idempotency Strategy**: Idempotency is enforced by a two-layer check: (1) state file tracks last fetch time per channel to avoid re-querying, and (2) file existence check before download ensures transcripts are never re-downloaded even if state is lost
- **Logging Format**: All logs are output as structured JSON (one object per line) to stdout, enabling machine-readable parsing by monitoring tools and log aggregators. Optional file rotation can be configured by redirecting stdout
- **Partial File Handling**: Downloads use a temporary `.tmp` extension; the file is renamed to its final name only after successful completion. On startup, any leftover `.tmp` files are deleted to clean up incomplete downloads from interrupted runs

## Transcript Format Specification

Transcripts are stored in UTF-8 text files at `storage/transcripts/{video_id}.txt` with timestamp markers in MM:SS format prefixing each caption segment.

### Example Format

```
00:00 Welcome to this video on investment strategies.
00:05 Today we'll discuss three key principles.
00:12 First, diversification is critical for long-term success.
01:30 Many investors make the mistake of over-concentrating.
02:15 Let me show you an example with NVIDIA stock.
03:45 As you can see from this chart, the growth potential is significant.
04:20 However, there are also risks to consider.
```

### Usage for Fact-Checking

When a fact-checker extracts a claim from the transcript (e.g., "NVIDIA stock growth is significant at 03:45"), they can:

1. Note the timestamp from the transcript (03:45)
2. Convert to seconds for YouTube URL: 03:45 = 3*60 + 45 = 225 seconds
3. Construct the jump-to-time YouTube link: `https://youtu.be/{video_id}?t=225`
4. Click the link to verify the claim directly in the video

This enables seamless linking between fact-check summaries and source video moments for verification and review.
