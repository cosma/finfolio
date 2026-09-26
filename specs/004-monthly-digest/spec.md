# Feature Specification: Monthly Digest Module

**Feature Branch**: `004-monthly-digest`

**Created**: 2026-09-26

**Status**: Draft

**Input**: Build the Month digest module for FinFolio. Given a target month, read all files in storage/reports/videos/ for videos published or processed in that month, and aggregate them into a single month digest: per-channel breakdown, overall verdict counts (True / Partially supported / Unverified / False) across the month, and a summary of any monetization disclosures flagged in that month's videos. Write the result to storage/reports/monthly/{year}-{month}.json. Expose this as a CLI command, e.g. finfolio report --month <date>.

## Clarifications

### Session 2026-09-27

**Initial Specification Phase**:
- Q1: Where should the video publication date come from in the fact-checking report? → A: Publication date is extracted from YouTube by Module 1, stored in transcript files, and propagated through Modules 2 and 3 as `summary.metadata.publication_date`. Each module ensures this field is present even on reprocessing.
- Q2: Should the CLI output follow the same JSON logging pattern as other FinFolio modules? → A: Yes, use same structured JSON logging to stdout as other modules (one JSON object per line with `timestamp`, `event`, `status`, and event-specific fields).

**Clarification Phase** (speckit-clarify):
- Q3: What is the exact JSON structure of the digest file? → A: Digest file contains month, generated_at, report_count, overall verdict_breakdown (True/Partially supported/Unverified/False counts), per_channel_breakdown (array of objects with channel info and verdict counts), and monetization_summary (array of {channel_name, disclosure} for channels with monetization flags). Documented in "Digest Output Format" section.
- Q4: What is the actual performance target for digest generation? → A: Under 2 seconds for up to 100 videos (typical/edge cases), with graceful degradation for extreme outliers (500+ videos). Aligns with SC-004 and keeps digest generation responsive for most real-world scenarios.
- Q5: Should the module create `storage/reports/monthly/` if it doesn't exist? → A: Yes, create the directory automatically if missing. Follows progressive robustness principle and matches Modules 2 & 3 pattern of internal directory initialization. Added to FR-006.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Generate Monthly Digest for a Specific Month (Priority: P1)

An analyst needs to review financial content performance for a given month. The system reads all fact-checking reports processed in that month, aggregates verdict statistics across all videos, and produces a single digest file showing per-channel breakdown and overall trends.

**Why this priority**: Core feature—enables monthly reporting and trend analysis. Without this, users cannot aggregate insights across multiple videos.

**Independent Test**: Can be fully tested by running `finfolio report --month 2026-09` and verifying the digest file is created at `storage/reports/monthly/2026-09.json` with correct aggregations.

**Acceptance Scenarios**:

1. **Given** multiple fact-checking reports exist in `storage/reports/videos/` for September 2026, **When** `finfolio report --month 2026-09` is executed, **Then** a digest is written to `storage/reports/monthly/2026-09.json` with aggregated verdict counts and per-channel breakdown.
2. **Given** 10 videos in September with verdicts: 5 True, 2 Partially supported, 2 Unverified, 1 False, **When** the digest is generated, **Then** the verdict_breakdown shows exactly these counts.
3. **Given** videos from multiple channels exist in the month, **When** the digest is generated, **Then** the per-channel breakdown lists each channel and its verdict distribution.
4. **Given** a digest already exists for a month, **When** the command runs again, **Then** the digest is updated (idempotent overwrite) with the latest data.

### User Story 2 - Aggregate Monetization Disclosures (Priority: P1)

The analyst needs visibility into which channels have monetization disclosures in the month. The digest summarizes all monetization flags found in that month's videos as a list or tally.

**Why this priority**: Compliance and transparency—Principle V mandates monetization disclosure; the digest must surface this across all videos.

**Independent Test**: Can be fully tested by running the command and verifying the monetization_summary field lists all unique disclosures found in the month's videos.

**Acceptance Scenarios**:

1. **Given** 3 videos in the month have monetization_disclosure fields set, **When** the digest is generated, **Then** a monetization_summary field aggregates these disclosures (as a list of unique disclosure strings or a count).
2. **Given** a video has no monetization_disclosure, **When** aggregating, **Then** it does not contribute to the summary (null values are ignored).
3. **Given** multiple videos from the same channel have the same disclosure, **When** aggregating, **Then** the summary lists each disclosure once per channel or as a deduplicated list.

### User Story 3 - Expose Digest Generation via CLI (Priority: P1)

Users trigger digest generation via CLI with a month parameter. The command validates the input, discovers relevant reports, and outputs progress and completion status.

**Why this priority**: Enables automation and integration into scheduled workflows; simple command-line interface for end-users.

**Acceptance Scenarios**:

1. **Given** the CLI is invoked with `finfolio report --month 2026-09`, **When** execution completes, **Then** stdout reports success and the path to the generated digest file.
2. **Given** no reports exist for a requested month, **When** the command runs, **Then** a digest file is created at `storage/reports/monthly/{year}-{month}.json` with all verdict counts set to 0 and an empty per-channel breakdown.
3. **Given** an invalid month format is provided (e.g., `2026-13`), **When** the command is invoked, **Then** an error message is shown and no file is written.

## Edge Cases

- **No reports for requested month**: Digest is generated with all counts at zero, or a message informs the user that no reports exist for that month.
- **Report file format changes**: System gracefully skips or logs malformed reports; partial digest is still generated from valid files.
- **Concurrent digest generation**: If multiple commands run simultaneously, only one digest is written via atomic .tmp pattern (same pattern as Module 2 & 3).
- **Mixed publication dates**: Reports are always assigned to the month of their video's publication date (`summary.metadata.publication_date`), which comes from YouTube via Module 1. This may differ from the fact-checking date (`fact_checked_at`), which is expected and correct.
- **Very large months**: Months with 100+ videos should complete in under 2 seconds where possible; extreme outliers (500+ videos) may take longer but must remain memory-efficient and not crash.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Discover all reports — Scan `storage/reports/videos/` for files processed or published in the target month.
- **FR-002**: Extract verdict data — Load each report and extract `verdict_breakdown` and video metadata (video_id, channel_name, channel_url).
- **FR-003**: Aggregate by channel — Group verdict counts by channel and produce a per-channel breakdown (list of {channel, True count, Partially supported count, Unverified count, False count}).
- **FR-004**: Calculate overall verdicts — Sum all verdict counts across all videos in the month to produce overall verdict_breakdown.
- **FR-005**: Collect monetization disclosures — Extract and deduplicate all non-null `monetization_disclosure` fields from reports in the month.
- **FR-006**: Write digest to storage — Output the aggregated digest to `storage/reports/monthly/{year}-{month}.json` in the standard JSON format. Create the `storage/reports/monthly/` directory if it does not exist (atomic create-if-missing, fail only on permission errors).
- **FR-007**: Idempotent processing — Running the command multiple times for the same month overwrites the digest with consistent results.
- **FR-008**: Validate month parameter — CLI command accepts month in YYYY-MM format and validates the format and reasonable date bounds.
- **FR-009**: CLI command — Expose functionality via `finfolio report --month <YYYY-MM>` with structured JSON logging to stdout (same pattern as other modules) and success/error messages.
- **FR-010**: Handle partial failures — If a single report is malformed or unreadable, log the error and continue processing other reports; partial digest is still generated.
- **FR-011**: JSON logging output — Each CLI event is a JSON object on stdout with fields: `timestamp` (ISO 8601), `event` (event type), `status` (success/failed), plus event-specific fields (`month`, `digest_path`, `report_count`, `error`, etc.).

### Key Entities

- **Report**: Per-video fact-checking report in `storage/reports/videos/{video_id}.json` (produced by Module 3).
- **Digest**: Aggregated monthly statistics written to `storage/reports/monthly/{year}-{month}.json`.
- **Channel**: Identified by channel_name and channel_url; used for per-channel breakdown.
- **Verdict Counts**: {True, Partially supported, Unverified, False} — aggregated across all videos.
- **Monetization Summary**: List of unique monetization disclosures found in the month, organized by channel.

### Digest Output Format

The digest file is a single JSON object written to `storage/reports/monthly/{year}-{month}.json` with the following structure:

```json
{
  "month": "2026-09",
  "generated_at": "2026-09-27T14:30:00Z",
  "report_count": 3,
  "verdict_breakdown": {
    "True": 5,
    "Partially supported": 2,
    "Unverified": 1,
    "False": 1
  },
  "per_channel_breakdown": [
    {
      "channel_name": "Financial Wisdom Daily",
      "channel_url": "https://youtube.com/@financialwisdom",
      "video_count": 2,
      "verdict_breakdown": {
        "True": 3,
        "Partially supported": 1,
        "Unverified": 0,
        "False": 0
      }
    }
  ],
  "monetization_summary": [
    {
      "channel_name": "Financial Wisdom Daily",
      "disclosure": "This video is sponsored by InvestXYZ trading course ($199)"
    }
  ]
}
```

**Field Definitions**:
- `month`: ISO 8601 partial date (YYYY-MM) for the aggregated month
- `generated_at`: ISO 8601 timestamp when the digest was created
- `report_count`: Total number of reports (videos) aggregated in this digest
- `verdict_breakdown`: Object with counts for each verdict type (top-level, across all videos in month)
- `per_channel_breakdown`: Array of objects, one per channel with at least one report in the month
  - `channel_name`: Channel name from report metadata
  - `channel_url`: Channel URL from report metadata
  - `video_count`: Number of videos from this channel in the month
  - `verdict_breakdown`: Verdict counts for only this channel's videos
- `monetization_summary`: Array of objects showing channels with monetization disclosures
  - Only includes channels that have at least one video with a non-null `monetization_disclosure` field
  - Entries are deduplicated per channel (one entry per unique disclosure text per channel)

## Success Criteria *(mandatory)*

- **SC-001**: Accuracy — All verdicts from reports in the target month are counted exactly once in the digest.
- **SC-002**: Completeness — All reports matching the month criteria are included in the digest (none are skipped except on error).
- **SC-003**: Idempotency — Running the command twice for the same month produces identical digests.
- **SC-004**: Performance — Digest generation completes in under 2 seconds for months with up to 100 videos; graceful degradation accepted for outliers (500+ videos).
- **SC-005**: Coverage — Per-channel breakdown includes all channels with at least one report in the month.
- **SC-006**: Monetization Visibility — All monetization disclosures from the month are captured in the digest summary.
- **SC-007**: Error Resilience — If 1 of 50 reports is malformed, the digest is still generated with counts from the other 49 reports.

## Assumptions

- Reports are already generated by Module 3 and exist in `storage/reports/videos/`.
- Each report file contains `fact_checked_at` (timestamp when fact-checking completed), `verdict_breakdown` fields, and embedded summary metadata.
- Summary metadata includes `publication_date` field (ISO 8601 timestamp) extracted from YouTube and preserved through Modules 1, 2, and 3.
- **Publication date flow**: Module 1 (transcript fetch) extracts publication date from YouTube and stores it in transcript files. Module 2 (summarization) propagates it to summary metadata. Module 3 (fact-checking) includes it in the report's embedded summary. Each downstream module ensures publication_date is present even if the input file is reprocessed.
- Reports are assigned to a month based on `summary.metadata.publication_date` (video publication month from YouTube), not the fact-checking date.
- The month parameter is provided in YYYY-MM format (ISO 8601 partial date).
- The `storage/reports/monthly/` directory exists or can be created by the module.
- Atomic file writes via .tmp pattern are supported (same as Module 2 & 3).
- Digest files can be overwritten if the command runs multiple times for the same month (idempotent).
- Monetization disclosures are either null (no disclosure) or a string (disclosure text); no other data type is expected.
- Users have read access to `storage/reports/videos/` and write access to `storage/reports/monthly/`.

## Scope Boundaries

**In scope**:
- Reading and aggregating fact-checking reports from a given month
- Calculating overall verdict counts
- Generating per-channel breakdown
- Summarizing monetization disclosures
- Writing digest file to storage
- CLI command for month parameter input
- Idempotent processing
- Error handling and partial failures

**Out of scope**:
- Generating per-video fact-checking reports (Module 3)
- Presenting the digest in a UI (Modules 5 & 6)
- Weekly digest aggregation (Module 5)
- Fact-checking the facts themselves
- Manual override or correction of verdicts
