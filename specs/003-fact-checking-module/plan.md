# Implementation Plan: [FEATURE]

**Branch**: `[###-feature-name]` | **Date**: [DATE] | **Spec**: [link]

**Input**: Feature specification from `/specs/[###-feature-name]/spec.md`

**Note**: This template is filled in by the `/speckit-plan` command; its definition describes the execution workflow.

## Summary

Implement a fact-checking module for FinFolio that processes extracted claims from video summaries, performs web searches via LangChain + Tavily API, assigns verdicts (True/Partially supported/Unverified/False), and generates reports. The module supports partial failure recovery by persisting per-claim verdicts incrementally, enabling resumption from interrupted checkpoints. Exposed via CLI command `finfolio factcheck` for batch processing.

## Technical Context

**Language/Version**: Python 3.10+

**Primary Dependencies**: 
- LangChain (LLM abstraction, tool-use orchestration)
- Tavily (web search API, integrated via LangChain)
- pydantic (data validation, report schema)
- pytest (testing framework)

**Storage**: JSON files (storage/summaries/{video_id}.json for input, storage/reports/videos/{video_id}.json for output)

**Testing**: pytest with pytest-cov for coverage

**Target Platform**: Linux/macOS CLI tool; runs as batch processing on local or server

**Project Type**: CLI tool / library (Python package)

**Performance Goals**: 
- Fact-check 15-20 claims per video within 2 minutes (accounting for web search latency)
- Process multiple videos sequentially in a single `finfolio factcheck` run

**Constraints**: 
- 8 GB RAM host, 2 GB Docker VM (per CLAUDE.md)
- LangChain must abstract all LLM calls; model selection via config only
- Temperature = 0 for fact-checking verdicts (deterministic per Constitution VII)
- Tavily API quota and cost monitoring via LangChain
- Atomic file writes via .tmp pattern (inherited from Module 2)

**Scale/Scope**: 
- 10-30 videos per week, 10 channels
- 15-25 claims per video
- 1-2 sentence verdict per claim + source URL

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

**Principle I (Accuracy Over Speed)**: ✓ Verified
- Every claim fact-checked against independent sources (Tavily searches)
- Unverifiable claims marked "Unverified", never guessed
- Search timeout gracefully degrades to "Unverified" (not omitted)

**Principle II (No Financial Advice)**: ✓ Verified
- Reports present facts and verdicts only
- No buy/sell/hold recommendations in report schema
- Disclaimer to be added in Phase 1 contract

**Principle III (Facts vs Forecasts)**: ✓ Verified
- Module accepts claim metadata from summarization (including opinion flag)
- Skips opinion/forecast claims (no fact-check applied)
- Verdicts only assigned to factual claims

**Principle IV (Transparency About Method)**: ✓ Verified
- Report includes source URLs and publication dates from search results
- Search source (Tavily) documented in report schema

**Principle VI (Official API Only)**: ✓ Verified
- Tavily is third-party search aggregator, not scraping
- YouTube data already sourced via official API (from Module 2 summaries)

**Principle VII (Resource & Cost Discipline)**: ✓ Verified
- LangChain abstraction layer for all LLM interactions
- Model name read from config (environment variable), never hardcoded
- Temperature = 0 for fact-checking verdicts (hardened against hallucination)
- Cost logging via LangChain integrated tools
- Tavily usage tracked and reported per run

**GATE RESULT**: PASS — All principles satisfied. No violations or waivers needed.

## Project Structure

### Documentation (this feature)

```text
specs/003-fact-checking-module/
├── spec.md              # Feature specification (input to planning)
├── plan.md              # This file (planning output)
├── research.md          # Phase 0: research & decision log
├── data-model.md        # Phase 1: entities, fields, relationships
├── quickstart.md        # Phase 1: validation scenarios & testing guide
├── contracts/           # Phase 1: public interfaces
│   ├── storage-api.md   # Storage API (extend finfolio.storage)
│   ├── cli-command.md   # CLI command signature & output format
│   └── report-schema.md # Report JSON schema & validation
└── tasks.md             # Phase 2 output (/speckit-tasks command — NOT created by /speckit-plan)
```

### Source Code (repository root) - Option 1: Single project

```text
src/finfolio/
├── __init__.py
├── storage.py           # EXTEND: add save_report(), has_report()
├── models.py            # NEW: Pydantic models (Claim, Verdict, Report)
├── fact_checker.py      # NEW: Core fact-checking logic (LangChain + Tavily)
├── cli.py               # NEW: CLI command (finfolio factcheck)
├── llm/
│   ├── __init__.py
│   ├── prompts.py       # LLM prompts for verdict reasoning
│   └── cost_tracking.py # LangChain callback for cost logging
└── search/
    ├── __init__.py
    └── tavily_client.py # Tavily API wrapper

tests/
├── unit/
│   ├── test_models.py           # Pydantic schema validation
│   ├── test_fact_checker.py      # Verdict logic (with mocks)
│   ├── test_storage.py           # Storage API (file I/O)
│   └── test_cli.py               # CLI parsing & output
├── integration/
│   ├── test_fact_check_e2e.py    # Full pipeline (real API)
│   ├── test_resumability.py      # Partial failure & recovery
│   └── test_idempotency.py       # Running twice produces same results
└── fixtures/
    └── summaries/                # Test summary fixtures

pyproject.toml           # EXTEND: add langchain, tavily, pydantic deps
```

**Structure Decision**: Single project (Option 1) — FinFolio is a CLI tool / library, all code lives in `src/finfolio/`. Module 2 (summarization) and Module 3 (fact-checking) are tightly integrated via shared storage and models. Fact-checking adds:
- **models.py**: Pydantic schemas for Claim, Verdict, Report (extends Module 2 schemas)
- **fact_checker.py**: Core logic for LangChain agent + Tavily search + verdict synthesis
- **cli.py**: Batch processing loop and CLI interface
- **llm/**: LLM-specific code (prompts, cost tracking, model configuration)
- **search/**: Search provider integration (Tavily)

## Complexity Tracking

**None**: All design decisions fit existing project scope. No violations of Constitution principles or technical constraints. Principle VII (LangChain abstraction) is satisfied by architecture. No waivers needed.
