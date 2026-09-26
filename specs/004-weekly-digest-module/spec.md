# Feature Specification: Weekly Digest Module

**Feature Branch**: `004-weekly-digest-module`

**Created**: 2026-09-26

**Status**: Draft

**Input**: Build the weekly digest module for FinFolio. Given a target week, read all files in storage/reports/videos/ for videos published or processed in that week, and aggregate them into a single weekly digest: per-channel breakdown, overall verdict counts (True / Partially supported / Unverified / False) across the week, and a summary of any monetization disclosures flagged in that week's videos. Write the result to storage/reports/weekly/{year}-W{week}.json. Expose this as a CLI command, e.g. finfolio report --week <date>. Out of scope for this module: generating the per-video reports themselves (module 3), presenting the digest in a UI (modules 5 and 6).

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Generate Weekly Digest Report (Priority: P1)

An analyst runs a weekly digest report to aggregate fact-checking verdicts across all videos published or processed in a given week. The system reads all video reports from that week, summarizes verdict counts by channel, and generates a week-at-a-glance summary showing content quality and integrity issues.

**Why this priority**: Core aggregation functionality — enables leadership visibility into weekly content fact-checking performance and identifies channels with systematic issues.

**Independent Test**: Can be fully tested by running the CLI command with a specific week and verifying the aggregated digest is written correctly, with accurate verdict counts and channel breakdowns.

**Acceptance Scenarios**:

1. **Given** multiple videos exist in `storage/reports/videos/` with timestamps in week W36 of 2026, **When** `finfolio report --week 2026-W36` runs, **Then** a digest file is created at `storage/reports/weekly/2026-W36.json`.
2. **Given** 3 videos from Channel A have 10 True verdicts, 5 Partially supported, 2 Unverified, 1 False, **When** the digest is generated, **Then** the per-channel breakdown shows Channel A: {true: 10, partially_supported: 5, unverified: 2, false: 1}.
3. **Given** videos are from multiple channels (A, B, C), **When** the digest is generated, **Then** the overall verdict counts sum correctly across all channels.
4. **Given** a video has no published_timestamp or processed_timestamp in the target week, **When** filtering occurs, **Then** the video is excluded from the digest.

---

### User Story 2 - Identify Monetization Disclosure Issues (Priority: P2)

The analyst reviews the weekly digest to identify videos flagged for monetization disclosure violations, enabling spot-checks on compliance and policy enforcement.

**Why this priority**: Supports risk management and regulatory compliance — monetization disclosures are a key compliance concern in finance content.

**Independent Test**: Can be tested by checking that all monetization disclosure flags from video reports are surfaced in the weekly digest summary.

**Acceptance Scenarios**:

1. **Given** 5 videos in the week have monetization_disclosures_flagged: true, **When** the digest is generated, **Then** a summary lists all 5 videos with monetization disclosure issues.
2. **Given** a video has monetization_disclosures_flagged: false, **When** the digest is generated, **Then** it is excluded from the monetization disclosure summary.
3. **Given** the monetization disclosure summary is empty (no flags), **When** the digest is generated, **Then** the field explicitly shows zero flagged videos.

---

### User Story 3 - Retrieve Historical Digests (Priority: P2)

Users retrieve previously generated weekly digests for historical analysis or audit purposes.

**Why this priority**: Enables trend analysis and supports auditing — digests once written should be stable and retrievable.

**Independent Test**: Can be tested by verifying that previously generated digest files at `storage/reports/weekly/{year}-W{week}.json` are consistent and re-readable.

**Acceptance Scenarios**:

1. **Given** a digest was generated for week 2026-W35, **When** the file is read from storage, **Then** the content is valid JSON with all required fields.
2. **Given** a user requests a digest for a week with no videos, **When** the command executes, **Then** an empty digest is written with zero counts across all verdict categories.

---

### Edge Cases

- **No videos in target week**: Generate a digest with all verdict counts at 0 and empty per-channel breakdown.
- **Timestamp ambiguity**: Both published_timestamp and processed_timestamp fields determine week membership — a video is included if either timestamp falls in the target week.
- **Partial data in video report**: If a video report is missing verdict counts or channel info, skip with error log; continue with remaining videos.
- **Concurrent digest generation**: Multiple `finfolio report --week` invocations for the same week race to write the digest — use atomic .tmp-then-rename pattern to prevent corruption.
- **Week boundary edge cases**: Handle weeks that span year boundaries (e.g., 2026-W52 may include dates in late December 2026 and early January 2027).

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Discover video reports — Scan `storage/reports/videos/` for all JSON files (video reports) with timestamps in the target week.
- **FR-002**: Extract weekly timestamp filter — Parse `--week <date>` argument (ISO 8601 week format: YYYY-Www) and map to the date range of that week (Monday 00:00 to Sunday 23:59 UTC).
- **FR-003**: Aggregate verdict counts — For each video in the target week, sum verdict counts (True, Partially supported, Unverified, False) across all claims in that video's report.
- **FR-004**: Per-channel breakdown — Group videos by channel name and compute per-channel verdict counts.
- **FR-005**: Monetization disclosure summary — Identify all videos in the week with monetization_disclosures_flagged: true and include them in a summary list.
- **FR-006**: Digest generation — Combine aggregated data into a single JSON digest with overall verdict counts, per-channel breakdown, monetization disclosure summary, and metadata (week, generation_timestamp).
- **FR-007**: Write digest file — Persist the digest to `storage/reports/weekly/{year}-W{week}.json` with atomic writes (write to .tmp file, then rename).
- **FR-008**: Idempotent processing — If the digest file already exists, verify it is valid JSON; if overwriting is needed, use atomic rename pattern to prevent partial writes.
- **FR-009**: CLI command — Expose via `finfolio report --week <YYYY-Www>` command with clear argument validation and error messages.
- **FR-010**: Error logging — Log all errors (missing timestamps, malformed reports, file I/O failures) as structured JSON events.

### Key Entities

- **Video Report**: JSON file in `storage/reports/videos/{video_id}.json` with claims, verdicts, channel, published_timestamp, processed_timestamp, monetization_disclosures_flagged.
- **Verdict**: One of {True, Partially supported, Unverified, False}; each claim has exactly one verdict per video report.
- **Weekly Digest**: JSON file at `storage/reports/weekly/{year}-W{week}.json` containing aggregated data for all videos in that week.
- **Channel Breakdown**: Dictionary mapping channel_name → {true, partially_supported, unverified, false, video_count}.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Accuracy — All videos with timestamps in the target week are included in the digest; no videos outside the week are included.
- **SC-002**: Verdict Aggregation — Verdict counts in the digest exactly match the sum of verdicts across all video reports in the week.
- **SC-003**: Idempotency — Running `finfolio report --week 2026-W36` twice produces identical digest files; second run overwrites with same content.
- **SC-004**: Latency — Generate a digest for a week with up to 100 videos in under 5 seconds.
- **SC-005**: Completeness — All per-channel breakdowns are included in the digest; no channels are omitted.
- **SC-006**: Monetization Compliance — All videos with monetization_disclosures_flagged: true are accurately listed in the digest summary.
- **SC-007**: Reliability — Partial video report corruption does not prevent digest generation; affected videos are skipped with error logging.

## Assumptions

- Video reports in `storage/reports/videos/` follow the schema established by the fact-checking module (module 3), with required fields: video_id, channel, claims (with verdicts), published_timestamp, processed_timestamp, monetization_disclosures_flagged.
- Week boundaries follow ISO 8601 standard: weeks run Monday to Sunday in UTC.
- Timestamps in video reports are in ISO 8601 format (YYYY-MM-DDTHH:MM:SSZ or similar).
- The `finfolio report` CLI command is the only way to generate weekly digests; no UI is in scope for this module.
- Digest files, once written, are not expected to change unless explicitly regenerated (no incremental updates per week).
- The storage directory structure (`storage/reports/videos/`, `storage/reports/weekly/`) already exists or is created during module initialization.
- Error handling defaults to skip-and-continue: if one video report is malformed, the digest is still generated with remaining videos included.
