# Implementation Plan: Monthly Digest Module

**Branch**: `004-monthly-digest` | **Date**: 2026-09-26 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/004-monthly-digest/spec.md`

**Approach**: Pure Python aggregation module extending existing storage and CLI infrastructure. No new external dependencies required.

## Summary

Build a monthly digest aggregation module that reads all fact-checking reports from `storage/reports/videos/` for a given month, computes per-channel verdict breakdowns, overall verdict counts, and monetization disclosure summaries, then writes the result to `storage/reports/monthly/{year}-{month}.json`. Expose via CLI command `finfolio report --month <YYYY-MM>`, defaulting to the current calendar month if no date is provided. Pure aggregation logic with no external API calls; reuses existing dependencies (pydantic, click, file I/O patterns from modules 1-3).

## Technical Context

**Language/Version**: Python 3.11+

**Primary Dependencies**: Click (CLI), Pydantic (data models), built-in libraries (json, pathlib, datetime)

**Storage**: JSON files on filesystem; extends existing storage.py module

**Testing**: pytest with pytest-cov (existing setup from modules 1-3)

**Target Platform**: Linux server / CLI tool

**Project Type**: CLI tool (FinFolio system component)

**Performance Goals**: Digest generation for 50 videos completes in < 2 seconds

**Constraints**: Memory usage stays minimal (no large buffers); processes reports streaming from disk

**Scale/Scope**: Supports monthly digests for months with 0-500 videos; 10-100 videos typical monthly volume

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

**Principle I (Accuracy Over Speed)**: ✅ PASS — Monthly digest aggregates counts from Module 3 reports; does not verify facts itself. Digest accuracy depends on upstream Module 3 accuracy. No shortcuts taken on computation.

**Principle II (No Financial Advice)**: ✅ PASS — Digest includes the fixed disclaimer from each report and includes only aggregated statistics, not recommendations or advice.

**Principle III (Facts vs. Forecasts)**: ✅ PASS — Digest aggregates verdicts already separated in Module 3. No new fact/forecast separation needed.

**Principle IV (Transparency About Method)**: ✅ PASS — Digest includes report metadata (which transcripts were used, which reports were aggregated). Timestamps logged for audit trail.

**Principle V (Monetization Awareness)**: ✅ PASS — Digest explicitly aggregates and surfaces monetization_disclosure fields from all reports in the month.

**Principle VI (Reliability Over Cleverness)**: ✅ PASS — Module reads from filesystem only. No unofficial APIs or scraping. Uses same file patterns as Modules 2 & 3.

**Principle VII (Resource & Cost Discipline)**: ✅ PASS — No LLM calls, no API quota usage. Pure Python file I/O. No new dependencies introduced. LangChain abstraction not needed (no LLM calls in this module).

**Gate Result**: ✅ PASS — All principles satisfied. Proceed to Phase 0.

## Project Structure

### Documentation (this feature)

```text
specs/004-monthly-digest/
├── plan.md              # This file (/speckit-plan command output)
├── research.md          # Phase 0 output (/speckit-plan command) — NONE NEEDED (no unknowns)
├── data-model.md        # Phase 1 output (/speckit-plan command)
├── quickstart.md        # Phase 1 output (/speckit-plan command)
├── contracts/           # Phase 1 output (/speckit-plan command)
│   └── digest-schema.md # Digest JSON schema (public interface)
└── tasks.md             # Phase 2 output (/speckit-tasks command)
```

### Source Code (repository root)

**Selected Structure**: Single Python project (Option 1), extending existing modules.

```text
src/finfolio/
├── storage.py           # EXTEND: add save_monthly_digest(), list_reports_for_month()
├── digest.py            # NEW: MonthlyDigest class with aggregation logic
├── cli.py               # EXTEND: add @cli.command() for report --month

tests/
├── unit/
│   └── test_digest.py           # NEW: unit tests for aggregation logic
├── integration/
│   └── test_digest_cli.py       # NEW: CLI integration tests
└── contract/
    └── test_digest_schema.py    # NEW: digest JSON schema validation
```

**Structure Decision**: Minimal extension to existing codebase. New `digest.py` module contains core aggregation logic; storage.py extended with two utility functions; CLI command added as Click subcommand. No new directories needed; keeps project lean.

## Complexity Tracking

No violations identified in Constitution Check. Complexity tracking not needed for this feature.
