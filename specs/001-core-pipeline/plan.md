# FinFolio Core Pipeline — Implementation Plan

## Executive Summary

FinFolio is a Python-based fact-checking system for financial advice YouTube content. This plan outlines the architecture, technology stack, data model, API contracts, and validation strategy for building and deploying the system.

**Tech Stack**: Python 3.11+ (CLI + backend), FastAPI (REST API), Vue 3 + TypeScript + Vite (frontend), PostgreSQL + pgvector (database), LangChain (LLM orchestration), google-api-python-client (YouTube API).

**Architecture**: 
- **Data layer**: PostgreSQL with pgvector extension for vector search and deduplication
- **Pipeline layer**: Python CLI with LangChain-orchestrated chains for summarization, extraction, and fact-checking
- **API layer**: FastAPI exposing reports and search endpoints
- **UI layer**: Vue 3 SPA for browsing reports and searching across fact-checks
- **Scheduling**: Daily cron/GitHub Actions for monitoring; Monday runs for weekly digest

---

## Constitution Compliance Check

**Verified against FinFolio Constitution v2.1.0**:

✓ **Principle I (Accuracy Over Speed)**: Spec requires fact-checks against independent sources; architecture includes web search + LLM verification for ambiguous cases.

✓ **Principle II (No Financial Advice)**: Reports contain facts and verdicts only; UI explicitly disclaims advice.

✓ **Principle III (Facts vs. Forecasts Separation)**: LangChain chain extracts opinions/forecasts separately from facts; stored in distinct database tables.

✓ **Principle IV (Transparency About Method)**: Reports include transcript source and LLM metadata; web search sources logged.

✓ **Principle V (Monetization Awareness)**: LLM extraction detects monetization mentions; reports flag them; digest aggregates them.

✓ **Principle VI (Reliability Over Cleverness)**: YouTube Data API v3 only; no scraping.

✓ **Principle VII (Resource & Cost Discipline)**: LangChain abstracts LLM calls; Haiku default via config; cost logged per call; YouTube quota tracked per run.

**Gate Status**: **PASS** — All principles enforced in architecture.

---

## Key Architecture Decisions

### 1. Language & Runtime
- **Python 3.11+**: Modern async support, type hints, pattern matching; required for LangChain.
- **PyPI package `finfolio`**: Enables global CLI.

### 2. LLM Orchestration
- **LangChain LCEL**: Composable chains for summarization+extraction (one chain) and fact-check synthesis (separate).
- **Temperature discipline**: Summarization 0.3, fact-checking 0.
- **Web search tool**: LangChain wrapper around Google Custom Search API.

### 3. Data Layer
- **PostgreSQL single database**: Video metadata, transcripts, claims, verdicts, LLM calls.
- **pgvector**: Semantic search and cross-video claim deduplication.
- **Idempotency**: PK on `video_id` in ProcessingStatus; skip if status='report_generated'.

### 4. Pipeline Architecture
- **CLI-first**: `finfolio run` (daily), `finfolio report --week` (digest).
- **Async processing**: Each step independent; status table coordinates.
- **Scheduling**: cron or GitHub Actions.

### 5. API & Frontend
- **FastAPI**: REST endpoints for reports, search, digest, cost.
- **Vue 3 + TS + Vite**: Minimal SPA, no state library; learning vehicle.

### 6. External Integrations
- **YouTube API v3**: Quota logged; fail safely if captions unavailable.
- **Google Custom Search API**: Web search for fact-checking.
- **LangChain provider**: Haiku default; swappable via config.

---

## Data Model

### Core Entities

**Videos**
- `video_id` (PK), `channel_id`, `title`, `published_date`, `transcript_text`, `source_url`, `created_at`

**ProcessingStatus**
- `video_id` (FK, PK), `status` (enum: pending | processing | claims_extracted | fact_checked | report_generated | failed), `updated_at`, `error_message`

**Claims**
- `claim_id` (PK), `video_id` (FK), `claim_text`, `claim_type` (enum: fact | opinion | forecast), `extraction_timestamp`, `embedding` (pgvector)

**FactChecks**
- `fact_check_id` (PK), `claim_id` (FK, UNIQUE), `verdict` (enum: True | Partially Supported | Unverified | False), `source_urls` (JSON), `note_text`, `llm_consulted`, `created_at`

**Reports**
- `report_id` (PK), `video_id` (FK, UNIQUE), `report_json`, `report_html`, `accuracy_score`, `monetization_disclosed`, `generated_at`

**LLMCalls**
- `llm_call_id` (PK), `video_id` (FK, nullable), `call_type` (enum: summarization | fact_checking), `model`, `tokens_input`, `tokens_output`, `cost_estimated`, `created_at`

**Digests**
- `digest_id` (PK), `week_start_date`, `digest_json`, `digest_html`, `generated_at`

---

## API Contracts

### REST Endpoints

**GET `/api/reports`** — List reports (paginated by week, channel, or limit)
**GET `/api/reports/{video_id}`** — Full per-video report
**GET `/api/digest/{week_start_date}`** — Weekly digest aggregation
**GET `/api/search?q=<query>&channel_id=<id>&verdict=<type>&accuracy_min=<0-100>`** — Vector search + filters
**GET `/api/cost`** — Monthly LLM spend breakdown

### CLI Commands

**`finfolio run [--channels <file>] [--days <N>]`** — Monitor channels, fetch transcripts
**`finfolio report --week <YYYY-MM-DD>`** — Generate weekly digest
**`finfolio process --video-id <id>`** — Manually process a single video

---

## Validation Strategy

### Prerequisites
- PostgreSQL + pgvector
- Environment vars: DATABASE_URL, ANTHROPIC_API_KEY, YOUTUBE_API_KEY, GOOGLE_SEARCH_API_KEY

### Runnable Scenarios
1. **Monitor**: `finfolio run --channels test.yaml --days 7` → Finds new videos, fetches transcripts
2. **Process**: `finfolio process --video-id <id>` → Summarize, extract claims, fact-check, generate report
3. **Digest**: `finfolio report --week 2026-09-22` → Aggregate reports, calculate stats
4. **API Search**: `curl "http://localhost:8000/api/search?q=interest+rates"` → Vector search results
5. **Cost Dashboard**: `curl "http://localhost:8000/api/cost"` → LLM spend tracking

### Acceptance Criteria
- ✓ No duplicate processing (idempotent via ProcessingStatus)
- ✓ Per-video processing completes within 2 hours
- ✓ Vector search returns results in <2 seconds
- ✓ Monthly LLM cost ≤ $20
- ✓ YouTube quota tracking confirms <10k units/day

---

## File Structure

```
finfolio/
├── finfolio/
│   ├── cli/ (main.py, monitor.py, report.py, process.py)
│   ├── pipeline/ (youtube.py, chains.py, processors.py, search.py)
│   ├── database/ (models.py, session.py, migrations/)
│   ├── api/ (app.py, routes.py, schemas.py)
│   ├── config.py
│   └── utils/ (logging.py, cost.py)
├── frontend/ (src/views, src/components, vite.config.ts)
├── config/ (channels.yaml)
├── tests/
├── pyproject.toml
├── .env.example
├── .github/workflows/ (finfolio-pipeline.yaml)
└── README.md
```

---

## Dependencies

**Backend**: python-dotenv, sqlalchemy, alembic, psycopg2, langchain, google-api-python-client, fastapi, uvicorn, pydantic, click, pytest, mypy, ruff.

**Frontend**: vue, typescript, axios (or fetch), vite.

---

## Risk Mitigations

| Risk | Mitigation |
|------|------------|
| YouTube quota exceeded | Alert at 8k units/day; implement backoff |
| LLM rate limit | Exponential backoff; queue requests |
| Database loss | Connection pool with retry; backups |
| Fact-check errors | Human audit sample quarterly |
| Duplicate processing | Idempotent via ProcessingStatus |
| High costs | Cost dashboard alerts; Haiku default |

---

## Next: `/speckit-tasks`

Generate actionable task list covering schema, chains, API, UI, CLI, tests, and deployment automation.
