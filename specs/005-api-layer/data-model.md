# Data Model: API Layer

The API reads two kinds of stored files and keeps one derived index. Stored files are the source of truth; the index can be deleted and rebuilt without losing anything (spec: Index entity).

## Stored file: Per-video report

Path: `storage/reports/videos/{video_id}.json`. Fields the API uses:

| Field | Type | Used for |
|---|---|---|
| `video_id` | string | Primary key; single-item route |
| `title` | string | List row |
| `channel_name` | string | Channel filter, list row |
| `channel_url` | string | Channel filter, list row |
| `fact_checked_at` | ISO-8601 UTC string | Date filter (UTC date) and default sort |
| `transcript_source` | string | Returned with report (FR-015) |
| `claim_count` | int | List row |
| `verdict_breakdown` | object of verdict name to count | List row |
| `verdicts` | list of claim objects, each with `verdict` | Verdict filter (via index table) and full report |
| `summary`, `cost`, `disclaimer` | objects / string | Full report only, returned as stored |

Validation on read: must be a JSON object with `video_id` present. A file that fails this is malformed (see Edge cases in the spec).

## Stored file: Monthly digest

Path: `storage/reports/monthly/YYYY-MM.json`. Fields:

| Field | Type | Used for |
|---|---|---|
| `month` | string `YYYY-MM` | Primary key; route parameter |
| `generated_at` | ISO-8601 UTC string | Digest list row |
| `report_count` | int | Digest list row |
| `verdict_breakdown` | object | Digest list row |
| `per_channel_breakdown` | list | Full digest only |
| `monetization_summary` | list | Full digest only |

The digest file has no `disclaimer` today. Clarified: the pipeline adds one, and existing files get the same one-time data fix as the verdict migration (see spec Assumptions).

## Derived index: SQLite

File: `storage/.finfolio-api-index.sqlite`. Built from the stored files; never written to by anything else.

```sql
CREATE TABLE reports (
    video_id          TEXT PRIMARY KEY,
    title             TEXT NOT NULL,
    channel_name      TEXT NOT NULL,
    channel_url       TEXT NOT NULL,
    fact_checked_at   TEXT NOT NULL,      -- full stored timestamp, for display
    fact_check_date   TEXT NOT NULL,      -- YYYY-MM-DD, UTC, for date filter
    claim_count       INTEGER NOT NULL,
    verdict_breakdown TEXT NOT NULL       -- JSON object
);
CREATE INDEX reports_channel_name ON reports(channel_name);
CREATE INDEX reports_channel_url  ON reports(channel_url);
CREATE INDEX reports_date         ON reports(fact_checked_at DESC, video_id);

CREATE TABLE report_verdicts (
    video_id TEXT NOT NULL REFERENCES reports(video_id),
    verdict  TEXT NOT NULL,               -- one of the four canonical names
    PRIMARY KEY (video_id, verdict)
);
CREATE INDEX report_verdicts_verdict ON report_verdicts(verdict, video_id);

CREATE TABLE digests (
    month             TEXT PRIMARY KEY,   -- YYYY-MM
    generated_at      TEXT NOT NULL,
    report_count      INTEGER NOT NULL,
    verdict_breakdown TEXT NOT NULL       -- JSON object
);
```

Notes:
- `report_verdicts` has one row per distinct verdict per report, so a verdict filter is an index lookup and a report with many "False" claims is stored once for that verdict.
- A report with zero claims has no `report_verdicts` rows and never matches a verdict filter (spec edge case).
- Digests are small (24 rows), so they are read from the index for the list and from the file for the single item. The single read still goes through `storage.load_monthly_digest`.

## Canonical verdict names

`True`, `Partially supported`, `Unverified`, `False`. The API accepts only these as filter values (FR-006). Stored data that uses anything else is malformed until the one-time migration runs (spec Assumptions).

## Response models

Pydantic models in `api/schemas.py`:

- `DigestSummary`: month, generated_at, report_count, verdict_breakdown
- `DigestDetail`: DigestSummary plus per_channel_breakdown, monetization_summary (`extra="allow"`)
- `ReportSummary`: video_id, title, channel_name, channel_url, fact_checked_at, claim_count, verdict_breakdown
- `ReportDetail`: full stored report (`extra="allow"`, so nothing is dropped)
- `ReportPage`: items, total, page, page_size
- `RefreshResult`: indexed, skipped (list of `{item, reason}`)
