# Feature Specification: Search Fallback and Claim Re-check

**Feature Branch**: `fix/search-fallback-and-claim-cleanup`

**Created**: 2026-10-14

**Status**: Draft (written after implementation; records the behavior as built)

**Input**: User description: "Record the search fallback and claim cleanup as built. Claims are verified with DuckDuckGo first; a verdict is accepted only if it is not Unverified and its confidence is at least 0.8, otherwise the claim falls back to Tavily. Any Tavily failure stops factcheck with exit code 2; partial verdicts are kept and a re-run resumes. Verdicts record verified_by and confidence. Verdicts without verified_by are re-checked and replaced. True or False without a source_url is treated as invalid model output and checked again, not a crash. The pending list includes reports with re-checkable verdicts or checkable claims without a verdict. A one-time cleanup script removes Unverified verdicts from exhausted Tavily credits and marks the rest verified_by=tavily, dry-run by default. Tests stay off the network and off .env. This supersedes Tavily-only provider wording in spec 003."

## Clarifications

### Session 2026-10-14

- Q: Should the 0.8 confidence threshold stay fixed in the code, or be a setting you can change without editing code? → A: Setting with 0.8 default
- Q: When both DuckDuckGo and Tavily find no sources for a claim, should that Unverified verdict be final, or be searched again on a later run? → A: Final
- Q: What should a report's top-level `search_provider` field say now that claims can be verified by either DuckDuckGo or Tavily? → A: Remove the field

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Verify claims with the free source first (Priority: P1)

As the owner, I want each claim checked against a free web source first, so that the paid search credits are spent only on claims the free source cannot settle.

**Why this priority**: Search credits are limited. The free source covers many claims, and the paid one should be a fallback.

**Independent Test**: Run the fact-check on a video whose claims a free source can confirm. Every confirmed claim is recorded with the free source as its provider, and the paid search is never called for them.

**Acceptance Scenarios**:

1. **Given** a claim the free source answers confidently (not Unverified, confidence 0.8 or higher), **When** it is checked, **Then** its verdict is accepted and recorded as verified by the free source, with no paid search.
2. **Given** a claim the free source answers with low confidence or as Unverified, **When** it is checked, **Then** the paid search is used and its verdict is recorded as verified by the paid search.
3. **Given** a claim the free source returns no results for, **When** it is checked, **Then** the paid search is used.
4. **Given** the free source fails with an error, **When** a claim is checked, **Then** the paid search is used.

---

### User Story 2 - Stop the run when the paid search fails (Priority: P1)

As the owner, I want the fact-check run to stop when the paid search fails, so that no claim is silently recorded as Unverified because the search did not work.

**Why this priority**: Silent "Unverified" results from search failures corrupted the stored reports and had to be cleaned up.

**Independent Test**: Simulate a paid-search failure partway through a video. The run stops with exit code 2, the verdicts already found are kept, and the failed claim has no verdict.

**Acceptance Scenarios**:

1. **Given** the paid search reports that its credits are used up, **When** a claim needs it, **Then** the run stops with exit code 2 and a message that credits are used up.
2. **Given** the paid search fails for another reason (timeout, unreadable response, other error), **When** a claim needs it, **Then** the run stops with exit code 2 and a message naming the failure.
3. **Given** a run stopped partway, **When** the owner runs the fact-check again after fixing the cause, **Then** the run resumes with the remaining claims and does not repeat the verdicts already saved.

---

### User Story 3 - Check again the claims that were never really checked (Priority: P2)

As the owner, I want old "Unverified" results and results from failed model replies checked again, so that stored reports reflect real findings.

**Why this priority**: Earlier runs recorded empty search results as Unverified. These are not findings and should be replaced.

**Independent Test**: Take a report with a verdict that has no `verified_by` and a claim with no verdict. Run the fact-check. Each such claim gets a fresh verdict that replaces the old one, with `verified_by` set.

**Acceptance Scenarios**:

1. **Given** a stored Unverified verdict with no `verified_by`, **When** the fact-check runs, **Then** that claim is checked again, and the new verdict replaces the old one.
2. **Given** a checkable claim (not opinion or forecast) with no verdict in its report, **When** the owner lists pending videos, **Then** that video is listed.
3. **Given** the model replies with True or False but gives no source, **When** the claim is checked, **Then** the claim is treated as an invalid reply, recorded as Unverified with no `verified_by`, and checked again on the next run. The run does not stop.

---

### User Story 4 - Clean up stored verdicts (Priority: P2)

As the owner, I want to remove the empty-search Unverified verdicts from storage and mark the real verdicts with their source, so that the stored data matches what was actually found.

**Why this priority**: The earlier runs left about 1,200 empty verdicts in the stored reports.

**Independent Test**: Run the cleanup script in dry-run mode, then with `--apply`. Unverified verdicts are gone, every remaining verdict has `verified_by`, and `verdict_count` and `verdict_breakdown` match the remaining verdicts.

**Acceptance Scenarios**:

1. **Given** stored reports with Unverified verdicts, **When** the cleanup runs with `--apply`, **Then** those verdicts are removed, and the counts in each report are recalculated.
2. **Given** the cleanup is run without `--apply`, **When** it finishes, **Then** it reports the changes it would make and writes nothing.
3. **Given** remaining verdicts without `verified_by`, **When** the cleanup runs, **Then** they are marked as verified by Tavily, since Tavily was the only search source when they were produced.

---

### Edge Cases

- The model's confidence is outside 0 to 1: it is clamped to that range.
- The model's confidence is missing or not a number: the verdict has no confidence and is not accepted from the free source.
- A free-source result that is not Unverified but has confidence below 0.8: the paid search is used, and the free-source verdict is discarded.
- A claim with an opinion or forecast flag is not searched and gets no verdict.
- A report whose file cannot be parsed is skipped by the pending check and left unchanged.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The fact-checker MUST search the free source (DuckDuckGo) first for each claim that needs a verdict.
- **FR-002**: A free-source verdict MUST be accepted only if it is not Unverified and its confidence is at least 0.8. Otherwise the claim MUST be checked with the paid search (Tavily).
- **FR-003**: If the free source fails or returns no results, the claim MUST be checked with the paid search.
- **FR-004**: If the paid search fails for any reason, the fact-check run MUST stop with exit code 2 and a message that names the cause. The run MUST NOT record an Unverified verdict for the claim that failed.
- **FR-005**: When the run stops, the verdicts already found for the video MUST be kept in its report. A later run MUST resume with the claims that have no verdict.
- **FR-006**: Every verdict MUST record which search provider verified it (`verified_by`) and the model's confidence (`confidence`, 0 to 1). A verdict with no `verified_by` MUST NOT be treated as a finished check.
- **FR-007**: A stored verdict with no `verified_by` and an Unverified result MUST be checked again. A new verdict for the same claim MUST replace the old one, with no duplicates.
- **FR-008**: A model reply of True or False with no source MUST be treated as an invalid reply: the claim becomes Unverified with no `verified_by` and is checked again on the next run. The run MUST NOT stop.
- **FR-009**: The list of pending videos MUST include a video whose report has a verdict to check again, or a checkable claim (not opinion or forecast) that has no verdict.
- **FR-010**: A cleanup MUST remove Unverified verdicts, mark remaining verdicts without `verified_by` as Tavily, and recalculate `verdict_count` and `verdict_breakdown`. It MUST run as a dry run unless explicitly told to apply, and MUST write each file atomically.
- **FR-011**: The automated tests MUST NOT make network calls and MUST NOT read the `.env` file.
- **FR-012**: The confidence threshold for accepting a free-source verdict MUST be a configurable setting with a default of 0.8. Changing it MUST NOT require a code change. A value outside 0 to 1 MUST be rejected at startup with a message that names the setting and the value.
- **FR-013**: An Unverified verdict recorded after both the free source and the paid search returned no sources MUST be final. The run MUST NOT search that claim again automatically. The re-check rule in FR-007 still applies to verdicts without `verified_by`.
- **FR-014**: Reports MUST NOT carry a top-level `search_provider` field. Each verdict's `verified_by` is the only record of where its sources came from.

### Key Entities

- **Verdict**: The result for one claim. Attributes: claim, verdict (True, Partially supported, Unverified, False), note, source, `verified_by` (duckduckgo or tavily; absent when re-check is needed), `confidence` (0 to 1).
- **Search provider**: The source that produced a verdict. Free source (DuckDuckGo) first; paid source (Tavily) as fallback.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: After the cleanup, no stored verdict is Unverified, and every remaining verdict records which provider verified it.
- **SC-002**: A fact-check run never records an Unverified verdict caused by a search failure. Every search failure ends the run with a clear message.
- **SC-003**: The number of paid searches is no more than the number of claims the free source could not confirm confidently.
- **SC-004**: An interrupted fact-check run, once its cause is fixed, completes with no duplicate verdicts for any claim.

## Assumptions

- The free source is DuckDuckGo through the `ddgs` library. It has no API key and no fixed credit limit. The paid source is Tavily, which uses credits.
- The confidence threshold defaults to 0.8 and can be changed without a code change (FR-012).
- Confidence is the model's own estimate, reported with each verdict. It is not calibrated against outcomes.
- Verdicts from the earlier Tavily-only runs are attributed to Tavily because Tavily was the only search source at the time.
- The provider wording in spec 003 (Tavily as the only search provider, including the report's `search_provider` field) is superseded by this spec. The report's `search_provider` field is removed (FR-014); each verdict's `verified_by` replaces it.
- Monthly digests are regenerated from reports after a fact-check run. Until they are, their counts are out of date.
- Opinion and forecast claims are not searched and do not need verdicts.

## Out of Scope

- Calibrating model confidence against known outcomes.
- Retrying a failed paid search automatically without stopping the run.
- Changing the summarizer or the transcript fetcher.
