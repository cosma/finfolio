# Feature Specification: Transcript Summarization Module

**Feature Branch**: `002-transcript-summarization`

**Created**: 2026-09-25

**Status**: Draft

**Input**: Build the summarization module for FinFolio. For each video with a transcript in storage/transcripts/ but no corresponding file in storage/summaries/, read the transcript and send it to Claude via LangChain to produce (a) a plain-language summary and (b) a structured list of discrete, checkable factual claims (specific numbers, dates, named deals, company or product facts), kept separate from the advisor's stated opinions and forecasts, per the project constitution. Write the result to storage/summaries/{video_id}.json. Skip videos whose summary file already exists, so runs are idempotent. Expose this as a CLI command, e.g. finfolio summarize. Ignore parts where the podcaster advertises a certain product or service. Strictly interested in their investment ideas.

## Clarifications

### Session 2026-09-25

- Q: What should happen if an LLM API call fails or times out? → A: Retry up to 3 times with exponential backoff before failing.
- Q: What should happen if two processes try to summarize the same transcript simultaneously? → A: Check for existing summary file; if present, skip immediately (let caller handle coordination).
- Q: Can existing summaries be regenerated/updated, or should they only be created once per video? → A: Summaries are immutable; once created, they are never updated. Users must manually delete files if regeneration is needed.
- Q: What format and destination for error and operational logs? → A: Log to stdout/stderr only; external orchestration tools (systemd, Docker, etc.) handle log persistence and rotation.
- Q: What should happen if the LLM API rate limit is hit during a batch summarization run? → A: Implement exponential backoff and retry after a delay (e.g., wait 60s, then retry).

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Summarize New Transcripts (Priority: P1)

A data analyst runs the FinFolio summarization pipeline to process newly fetched transcripts from a finance YouTube channel. The system reads each transcript not yet summarized, sends it to Claude via LangChain, and stores both a human-readable summary and a structured list of factual claims in a JSON file. This enables downstream fact-checking workflows.

**Why this priority**: Core pipeline functionality — without summarization, fact-checking cannot proceed. This is the main user journey.

**Independent Test**: Can be fully tested by running `finfolio summarize` on a test transcript directory and verifying output JSON files are created with expected structure.

**Acceptance Scenarios**:

1. **Given** a transcript file exists in `storage/transcripts/` with no corresponding file in `storage/summaries/`, **When** `finfolio summarize` runs, **Then** a JSON file is created at `storage/summaries/{video_id}.json` containing a summary and claims list.
2. **Given** a transcript file has already been summarized, **When** `finfolio summarize` runs again, **Then** the existing summary file is skipped (idempotent).
3. **Given** a transcript contains podcast sponsorships/advertisements, **When** summarized, **Then** sponsored product/service sections are excluded from the summary and claims list.

### User Story 2 - Separate Facts from Opinions (Priority: P1)

The pipeline must extract only discrete, verifiable factual claims from the transcript while excluding the advisor's opinions and forecasts. Each factual claim is tagged with claim type (number, date, deal, company fact, product fact) to enable targeted fact-checking.

**Why this priority**: Critical for compliance with the FinFolio Constitution Principle III (Facts vs. Forecasts Separation). Downstream fact-checkers must trust that claims are verifiable, not opinions.

**Independent Test**: Can be fully tested by running the pipeline on a transcript with mixed facts and opinions and verifying the output JSON correctly separates them.

**Acceptance Scenarios**:

1. **Given** a transcript contains "Apple released the iPhone 15 Pro in September 2023", **When** summarized, **Then** this appears in the claims list as a factual claim, not in opinions.
2. **Given** a transcript contains "I think Apple's stock will double by 2025", **When** summarized, **Then** this appears in the summary but NOT in the structured claims list (marked as opinion/forecast).
3. **Given** a transcript contains "The S&P 500 closed at 5,432 today", **When** summarized, **Then** this is extracted as a factual claim with type "number" or "market-data".

### User Story 3 - Invoke Summarization via CLI (Priority: P1)

Users trigger the summarization workflow via a simple CLI command. The command processes all pending transcripts and reports progress and any errors.

**Why this priority**: Enables integration into automation and scheduled pipelines. Core usability.

**Independent Test**: Can be fully tested by running `finfolio summarize` and verifying command executes, reports completion status, and returns appropriate exit codes.

**Acceptance Scenarios**:

1. **Given** the CLI is invoked with `finfolio summarize`, **When** execution completes, **Then** stdout reports number of transcripts processed and number of errors (if any).
2. **Given** a transcript contains an error (e.g., malformed JSON), **When** summarized, **Then** the error is logged and reported but does not halt processing of remaining transcripts.
3. **Given** no new transcripts exist, **When** `finfolio summarize` runs, **Then** command exits cleanly reporting "0 transcripts processed".

### User Story 4 - Cost-Aware Summarization (Priority: P2)

The system logs the cost of each LLM call to enable cost tracking. This supports the FinFolio Constitution Principle VII (Resource & Cost Discipline) requirement to monitor spending and ensure pipeline costs stay within target ($10-20/month across ~20-30 videos/week).

**Why this priority**: Essential for budgeting and monitoring but not blocking for initial MVP. Cost visibility prevents accidental spending spikes.

**Independent Test**: Can be tested by running summarization and verifying cost logs are recorded and accurate.

**Acceptance Scenarios**:

1. **Given** a transcript is summarized, **When** the LLM call completes, **Then** cost metadata (model, tokens used, estimated cost) is logged.
2. **Given** multiple transcripts are summarized in one run, **When** command completes, **Then** a summary of total cost is reported.

### Edge Cases

- **Empty transcript file**: System MUST detect empty or whitespace-only transcripts and report them as errors without creating a summary.
- **LLM API failure/timeout**: System retries up to 3 times with exponential backoff (per FR-013). If all retries fail, the transcript is marked as failed and processing continues with next transcript.
- **LLM API rate limit**: System implements exponential backoff and retries per FR-018. If rate limit persists after retries, processing pauses and reports rate-limit error.
- **Transcript exceeds context limits**: If transcript is longer than LLM context window (e.g., 100k+ tokens), system either truncates with warning or rejects with clear error message (implementation to choose during planning).
- **Malformed JSON in existing summary file**: System detects corruption and reports error; if summary file is corrupted, user must manually delete and re-run to regenerate.
- **Missing transcript/summary directories**: System MUST create directories if missing (per Assumption about output directory creation). If creation fails due to permissions, error is reported.
- **Concurrent summarization attempts**: Two processes attempting to summarize the same video simultaneously — handled by checking for existing summary file; second process skips (per FR-015).
- **Summary immutability**: If user manually deletes a summary file, next run will regenerate it. Updates are never automatic (per FR-016).

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST scan `storage/transcripts/` directory for all transcript files (format: `{video_id}.txt` or `.json` with transcript content).
- **FR-002**: System MUST check `storage/summaries/` directory to identify transcripts that have already been summarized (file exists = skip).
- **FR-003**: System MUST read each unprocessed transcript and send it to Claude via LangChain abstraction layer for analysis.
- **FR-004**: System MUST use `temperature = 0.3` for summarization (per constitution, deterministic with slight variation for nuance).
- **FR-005**: System MUST extract a plain-language summary (1-2 paragraphs) capturing the advisor's key investment insights and recommendations.
- **FR-006**: System MUST extract a structured list of discrete factual claims, each with type (number, date, deal, company-fact, product-fact) and source quote from transcript.
- **FR-007**: System MUST separate factual claims from opinions/forecasts; claims list MUST contain only verifiable statements, never opinions.
- **FR-008**: System MUST exclude podcast sponsorships and advertisements from summary and claims (sections marked "sponsored by", "this episode is brought to you by", etc.).
- **FR-009**: System MUST write output as JSON to `storage/summaries/{video_id}.json` with schema: `{ summary, claims: [{ type, claim, quote, source_timestamp (optional) }], metadata: { transcript_tokens, model, temperature, timestamp } }`.
- **FR-010**: System MUST be idempotent — running the command twice with the same input produces the same output without reprocessing existing summaries.
- **FR-011**: System MUST expose a CLI command `finfolio summarize` that processes all pending transcripts and reports progress.
- **FR-012**: System MUST log all LLM interactions (model, input tokens, output tokens, estimated cost) for cost monitoring.
- **FR-013**: System MUST handle errors gracefully — if one transcript fails, continue processing remaining transcripts instead of halting. On LLM API failure, retry up to 3 times with exponential backoff before marking transcript as failed.
- **FR-014**: System MUST validate output JSON against schema before writing to disk.
- **FR-015**: System MUST handle concurrent summarization by checking for existing summary files; if present, skip processing (idempotent). Caller is responsible for external coordination to avoid concurrent attempts on the same transcript.
- **FR-016**: System MUST treat summaries as immutable; once created, summaries are never automatically regenerated or updated. Users must manually delete summary files if regeneration is required.
- **FR-017**: System MUST log all operational messages, errors, and progress updates to stdout/stderr in plain text format; external orchestration tools (systemd, Docker, etc.) handle log persistence.
- **FR-018**: System MUST implement exponential backoff with retry when LLM API rate limits are encountered (e.g., wait 60 seconds, then retry); stop after a reasonable number of retries (at least 2-3) and report rate-limit error.

### Key Entities

- **Transcript**: Input text file containing the raw audio transcript of a finance YouTube video. Attributes: `video_id`, `content` (text), `channel` (optional, extracted from metadata).
- **Summary**: Output document containing both plain-language summary and structured claims list. Attributes: `summary_text`, `claims` (list), `metadata` (model config, timestamp, token counts).
- **Claim**: Discrete, verifiable factual statement extracted from transcript. Attributes: `type` (enum: number, date, deal, company-fact, product-fact), `claim` (text), `quote` (exact source text), `source_timestamp` (optional, HH:MM:SS in video).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of transcripts with a corresponding `storage/summaries/{video_id}.json` file are skipped (idempotency verified).
- **SC-002**: Each summary contains a plain-language summary of 150-400 words and a claims list with 3-15 discrete claims per typical 30-60 minute finance video.
- **SC-003**: Claims list contains zero opinions or forecasts (verified by human spot-check on sample runs); factual claims are correctly separated from advisor opinions.
- **SC-004**: Sponsored content (advertisements, product endorsements marked as "brought to you by") is excluded from output in 99% of cases (verified by audit on sample set).
- **SC-005**: Pipeline processes a typical 50-minute transcript in under 1 minute (including LLM call, parsing, and JSON write).
- **SC-006**: Cost per transcript averages $0.01-0.05 USD with Haiku model (tracked via cost logs).
- **SC-007**: System handles transcripts up to 50k tokens without errors or context window overflow.
- **SC-008**: CLI command reports accurate progress (transcripts processed, errors encountered, total cost) in human-readable format.
- **SC-009**: LLM API failures are handled with automatic retry (up to 3 attempts with exponential backoff); at least 80% of transient failures are recovered without manual intervention.
- **SC-010**: Concurrent processes summarizing the same video do not create duplicate or corrupted summary files; idempotency is maintained.
- **SC-011**: All operational messages, errors, and cost logs are written to stdout/stderr in plain text; no file-based logs are created by the application itself.

## Assumptions

- Transcript files are stored as plain text (`.txt`) or JSON (`.json`) with content under a `content` or `text` key.
- Transcript directory structure is `storage/transcripts/` with files named `{video_id}.txt` or `{video_id}.json`.
- Output directory structure is `storage/summaries/` and will be created if missing.
- LangChain is already integrated into the project and Claude API credentials are configured via environment variables.
- Default LLM model is Haiku (`claude-haiku-4-5-20251001`) configured via LangChain (no model hardcoding in code).
- Sponsored content is identifiable by common markers ("this episode is brought to you by", "sponsor", "brought to you by") and exact patterns are configurable via a YAML/JSON config file.
- Downstream fact-checking modules (module 3) expect claims to be structured exactly as defined in FR-009 schema.
- Video metadata (channel, upload date) is available separately or will be retrieved by caller; this module focuses on transcript analysis only.
