# Feature Specification: API Layer

**Feature Branch**: `005-api-layer`

**Created**: 2026-10-13

**Status**: Draft

**Input**: User description: "Build the API layer for FinFolio: a read-only REST API over the stored monthly digests and per-video fact-check reports, with filtering for per-video reports, backed by a local index rebuilt from storage. No authentication for v1 (single-user, local/personal use). The web frontend is out of scope (module 6)."

## Clarifications

### Session 2026-10-13

- Q: Storage only has monthly digests today. Which should the API serve for digest endpoints in this module? → A: Monthly now (expose the existing monthly digests; weekly digests can be added later without changing the API shape)
- Q: Reports store the verdict as "Partially supported/overstated" but digests store it as "Partially supported". Which exact verdict names should the verdict filter accept? → A: Store everywhere as "Partially supported" (one canonical name across reports and digests)
- Q: How should the index pick up new or changed stored files while the API is running? → A: Startup + manual refresh (rebuild at startup; the owner triggers an explicit refresh; no background watching)

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Browse Monthly Digests (Priority: P1)

As the owner of FinFolio, I want to list the monthly digests that have been generated and open a single digest, so I can read the month's fact-check summary without opening files on disk.

**Why this priority**: Digests are the top-level summary of the pipeline's output. Without this, nothing downstream (including the frontend in module 6) has an entry point.

**Independent Test**: With a storage directory containing several monthly digests, request the digest list and then a single digest by its month identifier. Both return the stored content without the caller touching the filesystem.

**Acceptance Scenarios**:

1. **Given** storage holds digests for three months, **When** the digest list is requested, **Then** all three are returned, ordered newest month first, each with its month identifier, report count, and verdict breakdown.
2. **Given** a digest exists for a specific month, **When** that month is requested, **Then** the full digest is returned, including per-channel breakdown and monetization disclosures.
3. **Given** no digest exists for a requested month, **When** that month is requested, **Then** the response states the digest was not found, with no server error.
4. **Given** storage holds no digests, **When** the digest list is requested, **Then** an empty list is returned, not an error.

---

### User Story 2 - Find Per-Video Reports (Priority: P2)

As the owner, I want to list per-video fact-check reports and narrow them by channel, date range, or verdict, so I can see which claims were wrong or unverified in a given period or from a given channel.

**Why this priority**: Filtering is the core analytical use of the stored reports. It depends on the reports being readable, which is the base of Story 1 too.

**Independent Test**: With a known set of reports spanning several channels, dates, and verdicts, apply each filter alone and in combination, and confirm the returned set matches exactly the reports that satisfy the filters.

**Acceptance Scenarios**:

1. **Given** reports from several channels, **When** the list is filtered to one channel, **Then** only that channel's reports are returned.
2. **Given** reports spread across several months, **When** the list is filtered by a start and end date, **Then** only reports whose fact-check date falls within that range (inclusive) are returned.
3. **Given** reports with varying verdict counts, **When** the list is filtered by a verdict (for example "False"), **Then** only reports containing at least one claim with that verdict are returned.
4. **Given** a channel filter and a verdict filter together, **When** the list is requested, **Then** only reports matching both are returned.
5. **Given** no filters, **When** the list is requested, **Then** all reports are returned, newest fact-check first, with results paged so one response never holds the entire archive.
6. **Given** a filter value that matches nothing, **When** the list is requested, **Then** an empty result is returned, not an error.
7. **Given** an unrecognized verdict value or a start date after the end date, **When** the list is requested, **Then** the request is rejected with a message naming the invalid input.

---

### User Story 3 - Open a Single Per-Video Report (Priority: P3)

As the owner, I want to fetch one per-video report by its video ID, so I can read the full fact-check, including the verdict for each claim, the cost, and the disclaimer.

**Why this priority**: Single-report reads are simple once the list works, and they are the drill-down from Story 2.

**Independent Test**: Request a report by a known video ID and compare the response with the stored report.

**Acceptance Scenarios**:

1. **Given** a stored report for a video, **When** that video ID is requested, **Then** the full report is returned, including verdicts, summary, cost, and disclosures.
2. **Given** no report exists for a video ID, **When** it is requested, **Then** the response states the report was not found, with no server error.
3. **Given** a malformed video ID, **When** it is requested, **Then** the request is rejected as invalid.

---

### Edge Cases

- A report or digest file is malformed or unreadable: the item is skipped from list results and the failure is logged; the single-item request for that file returns an error that names the item, not a server crash.
- A file is added, changed, or removed in storage while the API is running: the index reflects the change after the next rebuild (startup or an explicit refresh), and a single-item request reads the current file.
- The index is missing or stale at startup: it is rebuilt from the files before the API serves requests.
- Storage is empty on first run: the API starts and returns empty lists.
- A report has zero claims: it appears in unfiltered lists and is excluded from any verdict filter.
- Two date filter bounds are given but one is missing: the open bound is treated as unbounded.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The API MUST list all stored monthly digests, newest month first, with each digest's month identifier, report count, and verdict breakdown.
- **FR-002**: The API MUST return a single monthly digest by its month identifier (YYYY-MM), including its per-channel breakdown and monetization disclosures.
- **FR-003**: The API MUST list per-video reports, newest fact-check first, with pagination.
- **FR-004**: The per-video list MUST support filtering by channel (exact channel name or channel URL).
- **FR-005**: The per-video list MUST support filtering by date range on the fact-check date, with inclusive start and end bounds, either bound optional.
- **FR-006**: The per-video list MUST support filtering by verdict, returning reports that contain at least one claim with that verdict. Accepted verdict names are the canonical set: True, Partially supported, Unverified, False. Any other value is rejected per FR-013.
- **FR-007**: Multiple filters MUST combine with AND logic.
- **FR-008**: The API MUST return a single per-video report by video ID, with the full report content.
- **FR-009**: Filtering and listing MUST NOT scan every stored file per request; they MUST be served from an index built from the stored files.
- **FR-010**: The index MUST be built from the stored files when the API starts. The owner MUST be able to trigger an explicit index refresh while the API is running, without restarting. The API MUST NOT watch the storage directory in the background.
- **FR-011**: The API MUST read stored data only through the project's existing storage access layer; it MUST NOT write, modify, or delete stored files.
- **FR-012**: The API MUST NOT require authentication for v1.
- **FR-013**: Invalid filter values, malformed identifiers, and unknown items MUST produce clear client-facing errors with the correct status meaning (invalid input vs. not found), never a server error.
- **FR-014**: Unreadable or malformed stored files MUST NOT stop the API from serving other items; they MUST be logged and reported as skipped.
- **FR-015**: Every report and digest response MUST include the disclaimer and transcript source present in the stored data, unchanged.

### Key Entities

- **Monthly Digest**: Summary of one month's reports. Attributes: month identifier, generation time, report count, verdict breakdown, per-channel breakdown, monetization disclosures.
- **Per-Video Report**: Fact-check of one video. Attributes: video ID, title, channel name and URL, fact-check date, transcript source, summary, verdicts, verdict breakdown, cost, disclaimer, monetization disclosure.
- **Verdict**: A claim-level outcome within a report. Canonical names: True, Partially supported, Unverified, False.
- **Index**: Derived, rebuildable lookup over reports and digests. Holds no data that is not in the stored files.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: The owner can list digests and open any single digest in under 1 second each, with an archive of 24 months of digests.
- **SC-002**: A filtered per-video list (any single filter, or channel plus verdict) returns in under 1 second with an archive of 5,000 reports.
- **SC-003**: Every filter combination returns exactly the set of reports that match the stated criteria, verified against a known fixture set with zero false inclusions or omissions.
- **SC-004**: The API starts and serves requests within 10 seconds on an archive of 5,000 reports.
- **SC-005**: After a stored file is added or changed, the owner triggers one index refresh, and the next list or single-item request reflects the change, with no API restart.
- **SC-006**: A single malformed stored file does not prevent any other report or digest from being listed or read.
- **SC-007**: Invalid input (bad verdict, bad date range, malformed video ID) is rejected with a message that names the invalid input in 100% of cases tested.

## Assumptions

- Single-user, local or personal use; the API listens only on the local machine by default. No accounts, roles, or access control in v1.
- Stored data is produced by the existing pipeline (transcript fetch, summarization, fact-checking, monthly digest). This feature only reads it.
- Digest endpoints serve the existing monthly digests (`storage/reports/monthly/YYYY-MM.json`). Weekly digests are not produced by this module; they can be added later without changing the API shape.
- The canonical verdict name for the partially-true outcome is "Partially supported" in reports and digests alike. Existing stored data and pipeline output that use "Partially supported/overstated" must be changed to this name by a pipeline/data change before this module ships; this module does not rename stored data (FR-011).
- The date filter for per-video reports uses the fact-check date recorded on each report, since it is always present.
- The channel filter matches the channel name or channel URL exactly; fuzzy or partial matching is out of scope.
- Pagination uses a fixed default page size (50) with a maximum (200).
- The index is held in process memory or in a local, gitignored cache file rebuilt from storage at startup. Either satisfies FR-009; the choice belongs to planning.
- Monetization disclosures and disclaimers are returned as stored; the API does not reword or interpret them (Constitution principles II and V).
- Out of scope: the web frontend (module 6), authentication, write endpoints, triggering pipeline runs from the API, and any financial recommendation features.
