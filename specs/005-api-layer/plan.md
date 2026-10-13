# Implementation Plan: API Layer

**Branch**: `005-api-layer` | **Date**: 2026-10-13 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/005-api-layer/spec.md`

## Summary

A read-only FastAPI service over the stored monthly digests and per-video fact-check reports. Filtering runs against a local SQLite index that is rebuilt from `storage/` at startup and on an explicit refresh. All file access goes through `src/finfolio/storage.py`; the API layer never opens stored files itself. Swagger UI is on by default so the endpoints can be exercised before the frontend (module 6) exists.

## Technical Context

**Language/Version**: Python 3.11+ (project `requires-python >=3.11`; code uses `X | None` and `datetime.UTC`)

**Primary Dependencies**: FastAPI (web framework, OpenAPI/Swagger UI built in), uvicorn (ASGI server), Pydantic v2 (already a dependency). Standard library `sqlite3` for the index.

**Storage**: Stored files (read-only from the API): `storage/reports/videos/{video_id}.json`, `storage/reports/monthly/YYYY-MM.json`. Derived index: `storage/.finfolio-api-index.sqlite` (inside the gitignored `storage/` directory, so no `.gitignore` change).

**Testing**: pytest with FastAPI's `TestClient` (uses the `httpx` package, added to dev dependencies). Tests use a fixture storage directory under `tmp_path`, not the real `storage/`.

**Target Platform**: Single user, macOS, local only (`127.0.0.1` by default).

**Project Type**: Web service (read-only REST API) added to the existing Python package.

**Performance Goals**: Digest list and single digest each under 1s on 24 months (SC-001). Filtered report list under 1s on 5,000 reports (SC-002). Startup, including index rebuild, under 10s on 5,000 reports (SC-004).

**Constraints**: Machine has 8 GB RAM and a 2 GiB Docker VM, so keep dependencies lean and avoid heavy in-memory data (CLAUDE.md). No Docker image is needed for this feature. No authentication (FR-012). No writes to stored data (FR-011).

**Scale/Scope**: 5,000 reports, 24 monthly digests, 1 user.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Note |
|---|---|---|
| I. Accuracy | Pass | API only reads verdicts; does not alter them. |
| II. No financial advice | Pass | Disclaimers are passed through as stored (FR-015). Digests get one via the pipeline data fix (clarified). |
| III. Facts vs. forecasts | Pass | Stored structure is passed through unchanged. |
| IV. Transparency | Pass | Transcript source is returned with each report (FR-015). |
| V. Monetization | Pass | Monetization disclosures are returned with digests and reports. |
| VI. Official API only | Pass | No YouTube access in this feature. |
| VII. Cost discipline | Pass | No LLM calls and no YouTube quota use. |
| Dev workflow: types & lint | Required | New code must pass `mypy src/` and `ruff check` / `ruff format`. |
| Dev workflow: TDD | Not triggered | TDD is mandated for fact-checking logic only. Tests are still written, but not as a gate. |

**Gate result**: PASS. No violations, so Complexity Tracking stays empty.

## Project Structure

### Documentation (this feature)

```text
specs/005-api-layer/
├── plan.md              # This file
├── research.md          # Phase 0
├── data-model.md        # Phase 1
├── quickstart.md        # Phase 1
├── contracts/
│   └── api.md           # Phase 1: endpoint contract
└── tasks.md             # Created later by /speckit-tasks
```

### Source Code (repository root)

```text
src/finfolio/
├── storage.py           # + read helpers for reports and monthly digests (no new file)
└── api/
    ├── __init__.py
    ├── app.py           # FastAPI app, routes, error mapping
    ├── index.py         # SQLite index: build, swap, query
    └── schemas.py       # Pydantic response models (drive the OpenAPI schema)

tests/api/
├── conftest.py          # Fixture storage directory and TestClient
├── test_index.py        # Filter combinations, ordering, malformed-file skipping
└── test_endpoints.py    # Status codes, validation errors, Swagger reachable

pyproject.toml           # + fastapi, uvicorn (runtime); + httpx (dev)
uv.lock                  # Regenerated
```

**Structure Decision**: One new subpackage, `finfolio/api/`, with three modules that each have one job: routes, index, response models. Storage reads are added to the existing `storage.py`, which the project already treats as the single file-access layer. No new top-level package.

**Run command** (after implementation):

```bash
uvicorn finfolio.api.app:app --host 127.0.0.1 --port 8000
# Swagger UI: http://127.0.0.1:8000/docs
```

## Design Decisions

1. **Index storage: SQLite file, rebuilt into a temp file and swapped in.** A refresh writes `storage/.finfolio-api-index.sqlite.tmp`, then `os.replace` swaps it in. In-flight reads keep the old file, and new requests see the new one. This meets the spec's "previous index keeps serving" rule (FR-010). Each request opens a short read-only connection.
2. **Date filter uses the UTC calendar date of `fact_checked_at`.** Report files store this field, not a `fact_check_date`. The index derives `fact_check_date` as the first 10 characters of `fact_checked_at`, which is UTC (`Z`).
3. **Channel filter** matches `channel_name` or `channel_url` exactly (spec assumption).
4. **Verdict filter** uses an `EXISTS` subquery against a `report_verdicts` table, so a report qualifies if any claim has that verdict. Zero-claim reports never match.
5. **Video ID validation** uses the pattern `^[A-Za-z0-9_-]{1,64}$`. This blocks path traversal before the ID reaches storage, and it accepts the existing non-YouTube fixture `test-video-001`.
6. **Refresh endpoint** `POST /index/refresh` is an addition beyond the four endpoints in the request. FR-010 and SC-005 require an owner-triggered refresh, and no endpoint otherwise provides one. It only rebuilds the derived cache, so FR-011 still holds.
7. **Digest disclaimer**: the API passes through whatever digests store. The disclaimer fix is a pipeline and one-time data change (clarified), not an API change.
8. **Malformed files**: skipped in lists, logged through the existing `_log_operation`, and returned by name in the refresh response. A single-item request for one returns HTTP 500 with a message naming the file, not a crash.
9. **Pydantic response models** in `schemas.py` so Swagger shows real field types. Item detail responses keep stored fields as-is (`extra="allow"`) so nothing is dropped or reworded.
10. **No ORM, no repository layer.** Plain `sqlite3` and functions. The spec asks for one index, not a data layer.

## Phase 0 & Phase 1 outputs

- `research.md`: decisions above with alternatives considered.
- `data-model.md`: index tables and stored-file fields used.
- `contracts/api.md`: endpoints, parameters, status codes, and error shapes.
- `quickstart.md`: how to start the server, open Swagger, and run the checks.

## Complexity Tracking

> No constitution violations. Nothing to justify.
