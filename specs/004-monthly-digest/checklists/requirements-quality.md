# Requirements Quality Checklist: Monthly Digest Module

**Purpose**: Unit tests for requirements writing — validate that monthly digest requirements are complete, clear, consistent, measurable, and ready for implementation.

**Created**: 2026-09-27  
**Feature**: [spec.md](../spec.md) | [plan.md](../plan.md) | [data-model.md](../data-model.md) | [contracts/digest-schema.md](../contracts/digest-schema.md)

**Review Ownership**: This checklist is a reviewer-owned requirements-quality review artifact. Mark an item `[x]` only when the reviewer determines the requirements-quality criterion is satisfied.

**Marker Semantics**: `[x]` means the criterion has been reviewed and the requirements quality is satisfied. It does NOT mean implementation work is complete.

---

## Data Model & Entity Completeness

- [ ] CHK001 - Are all aggregation entities defined (Digest, ChannelDigest, MonetizationEntry)? [Completeness, Spec §Key Entities]
- [ ] CHK002 - Does each entity have explicitly documented fields with types and constraints? [Completeness, data-model.md §Core Entities]
- [ ] CHK003 - Are validation rules specified for each entity field (min/max length, format patterns, uniqueness)? [Completeness, data-model.md §Validation Rules]
- [ ] CHK004 - Is the relationship between Digest and ChannelDigest clearly documented (array structure, ordering)? [Clarity, data-model.md §Relationships]
- [ ] CHK005 - Are identity rules defined (e.g., channel uniqueness in per_channel_breakdown)? [Completeness, Gap]
- [ ] CHK006 - Is the data flow from Report → Digest aggregation steps explicitly documented? [Completeness, data-model.md §Data Flow]

## JSON Schema & Contract Clarity

- [ ] CHK007 - Is the exact JSON structure of digest output specified with a concrete example? [Clarity, contracts/digest-schema.md §Schema]
- [ ] CHK008 - Are all top-level digest fields documented with their exact names and JSON types? [Clarity, contracts/digest-schema.md §Field Definitions]
- [ ] CHK009 - Is the verdict_breakdown field structure unambiguous (field names: "True", "Partially supported", "Unverified", "False")? [Clarity, Spec §Digest Output Format]
- [ ] CHK010 - Is the monetization_summary array structure specified (simple {channel_name, disclosure} pairs, not nested)? [Clarity, Clarification Q3, contracts/digest-schema.md]
- [ ] CHK011 - Are field ordering and determinism rules documented (e.g., per_channel_breakdown sorted by channel_name)? [Completeness, data-model.md §Serialization]
- [ ] CHK012 - Can the JSON schema be validated programmatically (e.g., JSON Schema or Pydantic models provided)? [Measurability, contracts/digest-schema.md §Validation]

## Aggregation Logic & Functional Scenarios

- [ ] CHK013 - Are verdict aggregation rules explicit (sum across all reports in month)? [Clarity, data-model.md §Aggregation Rules]
- [ ] CHK014 - Is the per-channel grouping logic clearly defined (group by channel_name, sum verdicts per channel)? [Clarity, data-model.md §Aggregation Rules]
- [ ] CHK015 - Are monetization deduplication rules specified (deduplicate by channel_name + disclosure_text)? [Completeness, data-model.md §Aggregation Rules]
- [ ] CHK016 - Is the month assignment rule for reports documented (use publication_date from summary.metadata, not fact_checked_at)? [Clarity, Spec §Assumptions]
- [ ] CHK017 - Are the primary use scenarios documented (User Stories 1, 2, 3)? [Completeness, Spec §User Scenarios]
- [ ] CHK018 - Can each aggregation scenario be traced to explicit acceptance criteria? [Measurability, Spec §Acceptance Scenarios]

## External Dependency Contracts

- [ ] CHK019 - Are Module 3 Report format requirements documented (which fields digest depends on)? [Completeness, Gap]
- [ ] CHK020 - Is the publication_date field contract explicit (ISO 8601 format, presence guaranteed by Modules 1-3)? [Clarity, Spec §Assumptions]
- [ ] CHK021 - Are the required report fields listed (video_id, channel_name, channel_url, verdict_breakdown, monetization_disclosure, summary.metadata.publication_date)? [Completeness, data-model.md §Report]
- [ ] CHK022 - Is the verdict_breakdown field format from Module 3 documented (matching canonical names: True/Partially supported/Unverified/False)? [Clarity, Spec §Clarifications Q1]
- [ ] CHK023 - Are nullable field expectations documented (e.g., monetization_disclosure can be null)? [Completeness, data-model.md §Report]

## Edge Cases & Failure Scenarios

- [ ] CHK024 - Are requirements for empty months documented (report_count=0, all verdicts=0, empty arrays)? [Completeness, Spec §Edge Cases]
- [ ] CHK025 - Are handling requirements specified for malformed/unreadable report files? [Completeness, Spec §Edge Cases]
- [ ] CHK026 - Is the behavior for concurrent digest generation defined (last-write-wins via atomic .tmp pattern)? [Completeness, Spec §Edge Cases]
- [ ] CHK027 - Are very large month handling requirements specified (< 2 seconds for 100 videos, graceful degradation)? [Completeness, Spec §Edge Cases, Clarification Q4]
- [ ] CHK028 - Is idempotency explicitly required (running twice produces identical results)? [Completeness, Spec §Functional Requirements FR-007]
- [ ] CHK029 - Are partial failure scenarios addressed (partial digest generated even if some reports are malformed)? [Completeness, Spec §Requirements FR-010]

## CLI & User-Facing Interface

- [ ] CHK030 - Is the CLI command interface specified (finfolio report --month YYYY-MM)? [Clarity, Spec §Functional Requirements FR-009]
- [ ] CHK031 - Is the default month behavior specified (what happens if --month omitted)? [Completeness, Spec §User Story 3, Acceptance Scenario 1]
- [ ] CHK032 - Are month validation requirements documented (YYYY-MM format, valid calendar month 01-12)? [Completeness, Spec §Functional Requirements FR-008]
- [ ] CHK033 - Is the output format specified (JSON logging to stdout per other modules)? [Clarity, Spec §Functional Requirements FR-011]
- [ ] CHK034 - Are success/error message formats documented (timestamp, event, status, event-specific fields)? [Completeness, Spec §Functional Requirements FR-011]

## Non-Functional Requirements

- [ ] CHK035 - Is the performance target quantified (< 2 seconds for up to 100 videos)? [Clarity, Spec §Success Criteria SC-004, Clarification Q4]
- [ ] CHK036 - Are memory constraints specified (streaming I/O, no large buffers)? [Completeness, Spec §Technical Context]
- [ ] CHK037 - Is scalability addressed (how performance degrades for 500+ videos)? [Completeness, Spec §Edge Cases, Clarification Q4]
- [ ] CHK038 - Are reliability requirements specified (error resilience, partial digest generation)? [Completeness, Spec §Success Criteria SC-007]
- [ ] CHK039 - Are storage reliability requirements documented (atomic .tmp writes, no corruption on concurrent access)? [Completeness, Spec §Edge Cases]

## Consistency & Terminology

- [ ] CHK040 - Are verdict field names canonical and consistent (always "Partially supported", never "overstated")? [Consistency, Spec §Clarifications, data-model.md]
- [ ] CHK041 - Is the term "report" used consistently (never conflated with "digest" or "video")? [Consistency, Spec §Key Entities]
- [ ] CHK042 - Are "publication_date" and "fact_checked_at" terminology used consistently and distinctly? [Consistency, Spec §Assumptions]
- [ ] CHK043 - Is "deduplication" clearly defined in monetization context (per channel_name + disclosure_text)? [Clarity, data-model.md §Aggregation Rules]

## Storage & Directory Handling

- [ ] CHK044 - Is the output file path specified (storage/reports/monthly/{year}-{month}.json)? [Clarity, Spec §Functional Requirements FR-006]
- [ ] CHK045 - Is directory auto-creation behavior specified (create if missing)? [Completeness, Spec §Functional Requirements FR-006, Clarification Q5]
- [ ] CHK046 - Are atomic write safety requirements documented (.tmp pattern)? [Completeness, Spec §Assumptions]
- [ ] CHK047 - Are idempotent overwrite requirements specified (old digest completely replaced)? [Completeness, Spec §Functional Requirements FR-007]

## Measurability & Testability

- [ ] CHK048 - Can "verdicts aggregated correctly" be objectively verified (with acceptance scenarios)? [Measurability, Spec §Acceptance Scenarios]
- [ ] CHK049 - Can "per-channel breakdown accurate" be tested (with specific channel and count assertions)? [Measurability, Spec §User Story 1, Acceptance Scenario 3]
- [ ] CHK050 - Can "monetization summary complete" be verified (with disclosure presence checks)? [Measurability, Spec §User Story 2, Acceptance Scenario 1]
- [ ] CHK051 - Can "performance target < 2 seconds" be validated (with specific test data size)? [Measurability, Spec §Success Criteria SC-004]
- [ ] CHK052 - Are test data requirements documented for validation scenarios? [Completeness, quickstart.md §Test Scenarios]

## Ambiguities & Conflicts

- [ ] CHK053 - Are all vague terms quantified ("reasonable time", "large months", etc.)? [Clarity]
- [ ] CHK054 - Do verdict count aggregation and per-channel sums logically align (no contradictions)? [Consistency]
- [ ] CHK055 - Does the performance target (< 2 seconds) conflict with any other requirements? [Conflict]
- [ ] CHK056 - Is "deduplication" defined consistently across all monetization scenarios? [Consistency]

## Notes

- **Checklist Type**: Lightweight pre-commit requirements validation (PR review level)
- **Focus Areas**: Data model completeness, JSON schema clarity, functional scenarios, edge cases, external dependency contracts
- **Depth**: Standard — emphasizes gaps and ambiguities that would block implementation
- **Status**: Ready for reviewer evaluation
- Mark items `[x]` only after confirming the requirement-quality criterion is satisfied
- Use this checklist as a gate before proceeding to `/speckit-tasks` (Phase 2 implementation planning)
- `/speckit-implement` will read checklist state; do not modify markers during implementation

---

**Checklist Version**: 1.0 | **Items**: 56 | **Status**: Generated 2026-09-27
