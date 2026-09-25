# Feature Specification: Fact-Checking Module

**Feature Branch**: `003-fact-checking-module`

**Created**: 2026-09-25

**Status**: Draft

**Input**: Build the fact-checking module for FinFolio, kept deliberately separate from summarization so a partial failure never forces re-summarizing a video. For each video with a summary in storage/summaries/ but no corresponding file in storage/reports/videos/, read the extracted claims and, for each claim, run a web search against independent sources and assign a verdict (True, Partially supported/overstated, Unverified, False) with a short note and source. Write the per-video report to storage/reports/videos/{video_id}.json. Skip videos whose report file already exists (idempotent). Handle partial failure gracefully: if fact-checking fails partway through a video's claims, resume from claims not yet checked. Expose as CLI command `finfolio factcheck`. Out of scope: summarization (module 2), weekly aggregation (module 4).

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Fact-Check Extracted Claims (Priority: P1)

A fact-checker runs the FinFolio fact-checking pipeline to verify claims extracted from financial video transcripts. The system searches independent sources for each claim, assigns a verdict (True/Partially supported/Unverified/False), and generates a detailed report showing verified facts, overstatements, and unverified claims.

**Why this priority**: Core pipeline functionality — without fact-checking, the summarization pipeline has no downstream value. Enables compliance verification and user trust.

**Acceptance Scenarios**:

1. **Given** a video has extracted claims in `storage/summaries/{video_id}.json`, **When** `finfolio factcheck` runs, **Then** a report is created at `storage/reports/videos/{video_id}.json` with verdicts for each claim.
2. **Given** a claim is "Apple stock closed at $195.42", **When** fact-checked, **Then** the verdict is True/False/Unverified with supporting source URL and timestamp.
3. **Given** a report already exists for a video, **When** `finfolio factcheck` runs, **Then** the existing report is skipped (idempotent).
4. **Given** a web search fails partway through checking claims, **When** the error is caught, **Then** unchecked claims are retried on next run without re-checking completed claims.

### User Story 2 - Handle Partial Failures Gracefully (Priority: P1)

The system must resume fact-checking from the last verified claim if a search request times out or fails, so users don't need to re-verify successful claims. This decouples module failures from re-running the entire fact-checking pipeline.

**Why this priority**: Prevents cascading re-work; maintains separation-of-concerns from summarization module.

**Acceptance Scenarios**:

1. **Given** fact-checking has verified 5 claims and the 6th search times out, **When** the next run executes, **Then** only claims 6+ are fact-checked (claims 1-5 are skipped).
2. **Given** a network error occurs mid-report, **When** the module recovers, **Then** the partial report is saved and next run resumes from the last unchecked claim.

### User Story 3 - Expose Fact-Checking via CLI (Priority: P1)

Users trigger the fact-checking workflow via a simple CLI command that processes all pending summaries and reports progress.

**Why this priority**: Enables integration into automated pipelines and scheduled workflows.

**Acceptance Scenarios**:

1. **Given** the CLI is invoked with `finfolio factcheck`, **When** execution completes, **Then** stdout reports number of videos processed, number of claims verified, and number of errors.
2. **Given** a claim fact-check fails (search times out), **When** the error is caught, **Then** the claim is logged as unverified but processing continues with the next claim.

## Functional Requirements

**FR-001**: Discover unsummarized videos — Scan `storage/summaries/` for videos not yet in `storage/reports/videos/`.

**FR-002**: Idempotent processing — Skip videos with existing reports in `storage/reports/videos/`.

**FR-003**: Extract claims from summary — Load claims list from `storage/summaries/{video_id}.json`.

**FR-004**: Web search integration — For each claim, execute web search against independent sources via search API (TBD: Google Custom Search, SearXNG, or similar [NEEDS CLARIFICATION: which search backend]).

**FR-005**: Verdict assignment — Classify each claim as True, Partially supported/overstated, Unverified, or False based on search results.

**FR-006**: Source attribution — Record source URL, publication, and date for each verdict.

**FR-007**: Report generation — Write per-video report to `storage/reports/videos/{video_id}.json` with claims, verdicts, notes, sources, and summary carried over.

**FR-008**: Partial failure resilience — On search error, save state of which claims were verified and resume from next claim on retry.

**FR-009**: CLI command — Expose functionality via `finfolio factcheck` command with batch processing and progress logging.

**FR-010**: Error logging — Log all failures (search timeouts, malformed claims, API errors) as structured JSON events.

## Success Criteria

**SC-001**: Accuracy — 95% of verifiable claims receive a verdict (True/False/Partially supported/Unverified) within search timeout window.

**SC-002**: Coverage — All summaries without existing reports are processed in a single run.

**SC-003**: Idempotency — Running `finfolio factcheck` twice produces identical reports; second run reports 0 videos processed.

**SC-004**: Latency — Fact-check 20 claims per video in under 2 minutes (including search delays).

**SC-005**: Resilience — Partial failure on 1 claim does not block fact-checking of remaining 19 claims; partial report is saved.

**SC-006**: Compliance — Reports distinguish between verified facts, partially supported claims, and unverified items per Constitution Principle I.

## Key Entities

- **Video**: Identified by video_id; has summary and report.
- **Claim**: Extracted from summary; has type, text, quote, timestamp, confidence.
- **Verdict**: True / Partially supported / Unverified / False; includes note and source URL.
- **Report**: Per-video document with claims, verdicts, sources, and summary.

## Edge Cases

- **No internet connectivity**: Fact-checking falls back to "Unverified" for all claims.
- **Search API quota exhausted**: Partial report is saved; retry on next run.
- **Malformed claim**: Missing required fields (claim text, quote); skip with error log.
- **Duplicate reports**: If multiple `finfolio factcheck` runs execute concurrently, only one report is written via atomic .tmp pattern.
- **Very old claims**: Claims from years-old videos may have no searchable sources; verdict is "Unverified".
- **Opinion vs. fact**: Claims marked as opinions in summarization should not be fact-checked; skip with note.

## Assumptions

1. Summaries are already generated by Module 2 and exist in `storage/summaries/`.
2. Summaries include claim type (number, date, deal, company-fact, product-fact); opinions/forecasts are marked in the claim structure.
3. Web search API (Google, SearXNG, etc.) is available and has sufficient quota.
4. Search results are in English or translateable to English.
5. Atomic file writes via .tmp pattern are supported (same as Module 2).
6. Fact-checking verdicts are binary or ternary (not shades of grey); note field captures nuance.
7. User has internet connectivity; offline scenarios are handled gracefully as "Unverified".
8. Reports directory (`storage/reports/videos/`) is writable.
9. Fact-checking is separate from summarization; module failures don't cascade.

## Scope Boundaries

**In scope**:
- Web search against independent sources for each claim
- Verdict assignment (True/Partially supported/Unverified/False)
- Per-video report generation
- Idempotent processing
- CLI command
- Partial failure recovery

**Out of scope**:
- Transcript summarization (Module 2)
- Weekly aggregation and trend reports (Module 4)
- Interactive fact-checking UI
- Fact-checking of opinions or forecasts (these are excluded by Module 2)
- Manual review or override of verdicts
