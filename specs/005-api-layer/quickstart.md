# Quickstart: API Layer

How to run the API and check it works end to end. Endpoint details are in [contracts/api.md](contracts/api.md); stored fields are in [data-model.md](data-model.md).

## Prerequisites

- Project venv set up (`source venv/bin/activate`) with dependencies installed, including the new `fastapi` and `uvicorn`.
- Stored data under `storage/` (reports and monthly digests from earlier modules). Empty storage also works and returns empty lists.

## 1. Start the server

```bash
uvicorn finfolio.api.app:app --host 127.0.0.1 --port 8000
```

On startup the index is built from `storage/`. Expected: the process logs an `index_built` line, then serves requests. Startup should take under 10 seconds on 5,000 reports (SC-004).

## 2. Open Swagger UI

Open <http://127.0.0.1:8000/docs>. Every endpoint in the contract is listed. Use "Try it out" to call them.

## 3. Check with curl

```bash
# Digests: newest month first
curl -s http://127.0.0.1:8000/digests | python3 -m json.tool

# One digest (replace year/month with one that exists)
curl -s http://127.0.0.1:8000/digests/2026/8 | python3 -m json.tool

# Reports: filtered by verdict and date range
curl -s "http://127.0.0.1:8000/reports?verdict=False&start=2026-09-01&end=2026-10-31" | python3 -m json.tool

# One report (use a video_id from the list above)
curl -s http://127.0.0.1:8000/reports/-OYNQ74oG9k | python3 -m json.tool

# Expected errors
curl -s "http://127.0.0.1:8000/reports?verdict=Partly%20true"   # 422, names the verdict
curl -s "http://127.0.0.1:8000/reports?start=2026-10-01&end=2026-09-01"  # 422, start after end
curl -s http://127.0.0.1:8000/digests/2026/7                      # 404 if no July digest
curl -s http://127.0.0.1:8000/reports/..%2Fsecret                 # 422, bad video ID
```

## 4. Check a refresh picks up a change

1. Note a report's `video_id` and confirm it is absent from a filter that should match it.
2. Add or edit a file under `storage/reports/videos/`.
3. Without restarting: `curl -s -X POST http://127.0.0.1:8000/index/refresh`.
4. Re-run the list request. The change should now appear (SC-005).

## 5. Run the tests

```bash
pytest tests/api
ruff check src/finfolio/api tests/api
mypy src/finfolio/api src/finfolio/storage.py
```

Expected: all `tests/api` tests pass, and ruff and mypy report no errors.

## Troubleshooting

- **Empty lists but files exist**: run `POST /index/refresh` and check its `skipped` list for malformed files.
- **500 on a single item**: the response names the file. Check its JSON with `python3 -m json.tool`.

## Data migration (pending owner approval)

Stored data still uses the legacy verdict name and digests lack the disclaimer. Both must be fixed before this module ships (FR-015, FR-016). The script is dry-run by default:

```bash
python scripts/migrate_verdict_names.py          # dry run: shows what would change
python scripts/migrate_verdict_names.py --apply  # writes the changes (owner runs this)
```

Last dry run (2026-10-14): 69 reports with 344 legacy verdict occurrences to change; 5 digests to receive the disclaimer. Nothing has been written.
