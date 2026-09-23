<!-- SYNC IMPACT REPORT
Version: 2.0.1 → 2.1.0 (MINOR: expanded Principle VII to mandate LangChain abstraction, cost monitoring,
and use-case-specific temperature defaults)
Modified Elements: Principle VII rewritten to require LangChain abstraction layer for all LLM interactions
  and explicit cost monitoring; Technical Constraints "Model Configuration" section renamed to
  "LLM Abstraction & Configuration" with detailed abstraction requirements; added "Temperature Defaults
  by Use Case" section mandating temperature=0 for fact-checking and temperature=0.3 for summarization
Ratified: 2026-09-23 | Last Amended: 2026-09-23
-->

# FinFolio Constitution

FinFolio is a Python pipeline and library that helps retail investors evaluate financial-advice
YouTube content by fact-checking it against independent sources. This constitution establishes
non-negotiable principles guiding all development, review, and deployment decisions.

## Core Principles

### I. Accuracy Over Speed (Non-Negotiable)

Every factual claim extracted from a video MUST be checked against independent primary sources
before it is reported. A claim that cannot be verified MUST be labeled "unverified" — it is never
guessed at and never silently dropped. No latency or throughput target justifies skipping
verification.

### II. No Financial Advice

The system reports facts and their accuracy only. It MUST NOT recommend buying, selling, or
holding any security. Every report MUST carry a short disclaimer stating this. This is a hard
boundary, not a style preference — outputs that read as a recommendation are non-compliant.

### III. Facts vs. Forecasts Separation

Verified factual claims (numbers, dates, named deals, figures) MUST be kept structurally distinct
from the advisor's opinions, predictions, and forecasts. Opinions and forecasts MUST NOT be
fact-checked as if they were verifiable claims — they are reported as opinion, not scored for
accuracy.

### IV. Transparency About Method

Every report MUST state which transcript source was used. If a transcript could not be retrieved,
this MUST be flagged plainly rather than fabricating a summary from the video's title or
description alone. Silent degradation of report quality is not permitted.

### V. Monetization Awareness

Reports MUST note, as a neutral disclosure rather than a judgment, when a channel promotes a paid
product (course, app, affiliate link) in the video being reviewed. This is disclosure, not
editorializing — the report states the fact of promotion without characterizing it as good or bad.

### VI. Reliability Over Cleverness

All YouTube data (channel search, video listing, captions) MUST come from the official YouTube
Data API v3. HTML scraping is prohibited. This keeps the pipeline from breaking whenever YouTube
changes its site markup, trading a small amount of API-coverage flexibility for long-term
stability.

### VII. Resource & Cost Discipline

YouTube Data API usage MUST stay under the 10,000-unit daily quota. LLM usage MUST be closely
cost-monitored at all times. The system MUST use an abstraction framework (LangChain) for all LLM
interactions to enable seamless switching between different LLM models and versions without
changing application code. The default model MUST be Haiku, invoked through the LangChain
abstraction layer — model selection is a configuration-only decision, never hardcoded.

## Technical Constraints

**Data Sourcing**:
- YouTube Data API v3 is the only permitted source for channel, video, and caption data (Principle VI)
- No HTML scraping, no unofficial/reverse-engineered endpoints

**LLM Abstraction & Configuration**:
- All LLM interactions MUST go through LangChain abstraction layer (no direct Claude API calls)
- Default model: `claude-haiku-4-5-20251001` via LangChain
- Model identifier and version MUST be read from configuration (environment variable or config file),
  never hardcoded in application code
- Switching models or versions is a configuration-only change, never requires code changes
- LangChain enables swapping LLM providers (Claude, OpenAI, etc.) and versions without touching
  application logic
- Cost monitoring MUST track and log every LLM call (model, tokens used, cost incurred)

**Temperature Defaults by Use Case**:
- Fact-checking operations: `temperature = 0` (deterministic, no randomness — same input always
  produces same output for verifiable consistency)
- Summarization operations: `temperature = 0.3` (slight variation to capture nuance while remaining
  focused and reliable)

**Resource Ceilings**:
- YouTube Data API: hard ceiling of 10,000 units/day — implement quota tracking and graceful
  backoff before the ceiling is hit, not after
- Claude API spend: target $10-20/month at ~20-30 videos/week across ~10 channels; cost per run
  MUST be observable (logged or reported), not just inferred after the invoice arrives
- Machine constraints: 8 GB RAM, 2 GB Docker VM — prefer prebuilt wheels, CPU-only ML dependencies,
  and lean single-stage Docker builds (see `CLAUDE.md` for full guidance)

## Development Workflow

**Test-First for Fact-Checking Logic**:
- Any code that extracts, verifies, or labels a claim MUST have tests written before
  implementation (Red-Green-Refactor)
- Test cases MUST include: a verifiable claim, an unverifiable claim (expect "unverified" label),
  and a forecast/opinion statement (expect no fact-check applied)

**Type Safety & Static Analysis**:
- New code MUST use type hints (Python 3.10+ syntax) and pass `mypy` before merge
- Untyped exceptions require documented rationale

**Clean Code**:
- Code MUST pass `ruff check` and `ruff format` before merge; linting failures are blocking

**Code Review Requirements**:
- Every PR requires at least one peer review before merge
- For changes touching fact-checking logic: reviewer MUST verify source traceability (Principle I)
  and correct fact/forecast separation (Principle III)
- For changes touching report output: reviewer MUST verify the disclaimer (Principle II) and
  monetization disclosure (Principle V) are still present
- Merge only when tests pass, types check, linting passes, and reviewer has approved

**Before Committing**:
- Run `pytest`, `mypy src/`, `ruff check src/ tests/`, `ruff format src/ tests/`
- Review `git diff` to ensure no API keys, secrets, or accidental large files are staged

## Governance

**Constitution Authority**:
This constitution supersedes all other project practices and guidance. Runtime implementation
detail lives in `CLAUDE.md`; the constitution sets policy and `CLAUDE.md` provides the how-to.
Where they conflict, the constitution wins and `CLAUDE.md` should be updated to match.

**Amendment Procedure**:
- Proposed changes MUST document what is changing, why, and the impact on existing reports or
  pipeline behavior
- Version bumps follow semantic versioning:
  - MAJOR: Backward-incompatible principle removals or redefinitions
  - MINOR: New principles, sections, or materially expanded guidance
  - PATCH: Clarifications, wording, typo fixes, non-semantic refinements

**Compliance Review**:
- All PRs touching fact-checking, report generation, or API integration MUST reference the
  relevant principle(s) above
- Principles I-VI (accuracy, no-advice, fact/forecast separation, transparency, monetization
  disclosure, official-API-only) are blocking and MUST NOT be waived
- Principle VII (resource/cost ceilings) MAY be temporarily exceeded only with an explicit,
  documented plan to bring usage back under the ceiling

**Version**: 2.1.0 | **Ratified**: 2026-09-23 | **Last Amended**: 2026-09-23
