# Research: API Layer

Resolves the open technical choices in `plan.md`. Each entry: decision, rationale, alternatives.

## 1. Web framework: FastAPI

- **Decision**: FastAPI, with uvicorn as the server.
- **Rationale**: Chosen in the request. Its OpenAPI schema and Swagger UI come from the code, so they stay in sync. Query validation via `Annotated[..., Query(...)]` returns 422 with the invalid field named, which covers FR-013. Current versions: fastapi 0.143.0, uvicorn 0.54.0.
- **Alternatives**: Flask plus a hand-written spec (more code, no built-in OpenAPI). Starlette alone (no request validation).

## 2. Filter index: SQLite file, rebuilt at startup and on refresh

- **Decision**: `storage/.finfolio-api-index.sqlite`, built into a `.tmp` file and swapped with `os.replace`.
- **Rationale**: `sqlite3` is in the standard library, so there is no new dependency. Indexed columns make filters fast without scanning files per request (FR-009). The atomic swap keeps the previous index serving during a rebuild (FR-010, clarified). `storage/` is already gitignored.
- **Alternatives**:
  - In-process Python dicts: simplest, but a 5,000-report archive held in memory with per-filter loops is harder to keep fast, and the spec allows either option.
  - Live file watching: rejected by FR-010.
  - Querying files on each request: rejected by FR-009.

## 3. Reading stored files: extend `storage.py`

- **Decision**: Add `list_report_ids`, `load_report`, `list_digest_months`, `load_monthly_digest` to `src/finfolio/storage.py`. Use the same pattern as `load_summary` (return `None` if missing, raise `ValueError` on bad JSON, log the failure).
- **Rationale**: The request says all data access goes through `storage.py`. Today it has write helpers and `list_reports_for_month`, which reads every report file and is too slow to call per request. It also has no single-report or digest reader.
- **Alternatives**: Reading the directories directly from `api/` (violates the requirement). Reusing `list_reports_for_month` (scans everything, and only filters by month).

## 4. Date basis for the date filter

- **Decision**: UTC calendar date of `fact_checked_at`.
- **Rationale**: Reports store `fact_checked_at` as a UTC ISO string (for example `2026-10-12T22:19:57.384033Z`). There is no `fact_check_date` field. Using the UTC date is the only basis that is always present and consistent with the stored data.
- **Alternatives**: `summary.metadata.publication_date` (the video's publication date, not the fact-check date; the spec asks for the fact-check date). A local timezone (unnecessary, since everything is stored in UTC).

## 5. Video ID validation

- **Decision**: `^[A-Za-z0-9_-]{1,64}$`.
- **Rationale**: The ID is used as a file name, so it has to be checked before it reaches storage (path traversal). The pattern accepts the 11-character YouTube IDs and the existing fixture `storage/reports/videos/test-video-001.json`. Exact 11-character matching would make that fixture unreadable through the API.
- **Alternatives**: Exact 11-character YouTube pattern (rejects the fixture). No validation (unsafe).

## 6. Digest endpoint shape

- **Decision**: `GET /digests/{year}/{month}`, monthly only.
- **Rationale**: The spec and the files on disk are monthly. The user chose this option over weekly.
- **Alternatives**: `/digests/{year}/{week}` backed by new weekly generation (out of scope). A week route that returns 404 (documents a path that never works).

## 7. Digest disclaimer

- **Decision**: API passes through what is stored. The pipeline is changed to write the disclaimer, and existing digests get a one-time data fix.
- **Rationale**: Chosen by the user. The API never invents content (FR-015, "unchanged").
- **Alternatives**: API adds the disclaimer at read time (invents content). Dropping the requirement (violates Constitution II).

## 8. Tests

- **Decision**: pytest plus `fastapi.testclient.TestClient`, with fixture storage in `tmp_path`.
- **Rationale**: Already in the project's dev dependencies. Fixture storage keeps tests away from the real archive. TestClient needs `httpx`, which is added to dev dependencies.
- **Alternatives**: Starting uvicorn in tests (slower, more moving parts).

## Open items (not blocking)

- `storage/reports/videos/test-video-001.json` is a test fixture inside the real storage directory. The index will list it. Decide separately whether to delete it.
- Stored report `channel_name` is `"Unknown"` in the sample. The filter matches it like any other value; it is a data-quality issue, not an API one.
