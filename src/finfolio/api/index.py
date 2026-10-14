"""SQLite index over stored reports and digests, rebuilt from storage/ (FR-009, FR-010).

The index is derived data. It is rebuilt at startup and on an explicit refresh, never
kept live-synced with the files. Each build goes into a temp file which then replaces
the live index in one step, so requests keep reading the previous index until the swap.
"""

import json
import logging
import sqlite3
import threading
from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

from finfolio import storage

logger = logging.getLogger(__name__)

CANONICAL_VERDICTS = ("True", "Partially supported", "Unverified", "False")
_build_lock = threading.Lock()

SCHEMA = """
CREATE TABLE reports (
    video_id          TEXT PRIMARY KEY,
    title             TEXT NOT NULL,
    channel_name      TEXT NOT NULL,
    channel_url       TEXT NOT NULL,
    fact_checked_at   TEXT NOT NULL,
    sort_key          TEXT NOT NULL,
    fact_check_date   TEXT NOT NULL,
    claim_count       INTEGER NOT NULL,
    verdict_breakdown TEXT NOT NULL
);
CREATE INDEX reports_channel_name ON reports(channel_name);
CREATE INDEX reports_channel_url  ON reports(channel_url);
CREATE INDEX reports_date         ON reports(sort_key DESC, video_id);
CREATE INDEX reports_fact_date    ON reports(fact_check_date);

CREATE TABLE report_verdicts (
    video_id TEXT NOT NULL REFERENCES reports(video_id),
    verdict  TEXT NOT NULL,
    PRIMARY KEY (video_id, verdict)
);
CREATE INDEX report_verdicts_verdict ON report_verdicts(verdict, video_id);

CREATE TABLE digests (
    month             TEXT PRIMARY KEY,
    generated_at      TEXT NOT NULL,
    report_count      INTEGER NOT NULL,
    verdict_breakdown TEXT NOT NULL
);
"""


@dataclass
class BuildResult:
    reports: int = 0
    digests: int = 0
    skipped: list[dict[str, str]] = field(default_factory=list)


def index_path() -> Path:
    """Live index location, inside storage/ (gitignored)."""
    return storage.index_file_path()


def open_index() -> sqlite3.Connection:
    """Open a read-only connection to the live index."""
    conn = sqlite3.connect(f"file:{index_path()}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def _sort_key(fact_checked_at: str) -> str:
    """Normalize a stored timestamp to fixed-width UTC so text ordering matches time ordering."""
    parsed = datetime.fromisoformat(fact_checked_at.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def _report_rows(report: dict[str, Any], video_id: str) -> tuple[tuple[Any, ...], list[str]]:
    """Build the reports row and the list of distinct verdicts for one stored report.

    Raises ValueError with a reason if the report is not usable.
    """
    if report.get("video_id") != video_id:
        raise ValueError("video_id in file does not match file name")
    verdicts = report.get("verdicts")
    if not isinstance(verdicts, list):
        raise ValueError("verdicts is missing or not a list")
    names: list[str | None] = [v.get("verdict") for v in verdicts if isinstance(v, dict)]
    non_canonical = [n for n in names if n not in CANONICAL_VERDICTS]
    if non_canonical:
        raise ValueError(f"non-canonical verdict name {non_canonical[0]!r}")
    breakdown = report.get("verdict_breakdown", {})
    if not isinstance(breakdown, dict):
        raise ValueError("verdict_breakdown is not an object")
    bad_keys = [k for k in breakdown if k not in CANONICAL_VERDICTS]
    if bad_keys:
        raise ValueError(f"non-canonical verdict name {bad_keys[0]!r} in verdict_breakdown")
    fact_checked_at = report.get("fact_checked_at")
    if not isinstance(fact_checked_at, str):
        raise ValueError("fact_checked_at is missing")
    try:
        sort_key = _sort_key(fact_checked_at)
    except ValueError as e:
        raise ValueError(f"fact_checked_at is not a valid timestamp: {fact_checked_at!r}") from e
    row = (
        video_id,
        str(report.get("title", "")),
        str(report.get("channel_name", "")),
        str(report.get("channel_url", "")),
        fact_checked_at,
        sort_key,
        sort_key[:10],
        int(report.get("claim_count", len(verdicts))),
        json.dumps(report.get("verdict_breakdown", {})),
    )
    return row, sorted({n for n in names if isinstance(n, str)})


def build_index() -> BuildResult:
    """Build a fresh index from storage/ and swap it in. Malformed files are skipped, not fatal."""
    with _build_lock:
        live = index_path()
        tmp = live.with_name(live.name + ".tmp")
        storage.prepare_index_build(tmp)

        result = BuildResult()
        conn = sqlite3.connect(tmp)
        try:
            conn.executescript(SCHEMA)
            for video_id in storage.list_report_ids():
                try:
                    report = storage.load_report(video_id)
                    if report is None:
                        continue
                    row, verdicts = _report_rows(report, video_id)
                except (ValueError, OSError, TypeError, AttributeError) as e:
                    result.skipped.append({"item": f"reports/{video_id}.json", "reason": str(e)})
                    logger.warning("skipped report %s: %s", video_id, e)
                    continue
                conn.execute("INSERT INTO reports VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)", row)
                conn.executemany(
                    "INSERT INTO report_verdicts VALUES (?, ?)", [(video_id, v) for v in verdicts]
                )
                result.reports += 1

            for month in storage.list_digest_months():
                year, mon = (int(part) for part in month.split("-"))
                try:
                    digest = storage.load_monthly_digest(year, mon)
                    if digest is None:
                        continue
                    conn.execute(
                        "INSERT INTO digests VALUES (?, ?, ?, ?)",
                        (
                            month,
                            str(digest.get("generated_at", "")),
                            int(digest.get("report_count", 0)),
                            json.dumps(digest.get("verdict_breakdown", {})),
                        ),
                    )
                    result.digests += 1
                except (ValueError, OSError, TypeError, AttributeError) as e:
                    result.skipped.append({"item": f"monthly/{month}.json", "reason": str(e)})
                    logger.warning("skipped digest %s: %s", month, e)

            conn.commit()
        except BaseException:
            conn.close()
            storage.discard_index_build(tmp)
            raise
        conn.close()
        storage.publish_index_build(tmp, live)
        logger.info(
            "index_built reports=%d digests=%d skipped=%d",
            result.reports,
            result.digests,
            len(result.skipped),
        )
        return result


def list_digests(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    rows = conn.execute(
        "SELECT month, generated_at, report_count, verdict_breakdown FROM digests ORDER BY month DESC"
    ).fetchall()
    return [
        {
            "month": r["month"],
            "generated_at": r["generated_at"],
            "report_count": r["report_count"],
            "verdict_breakdown": json.loads(r["verdict_breakdown"]),
        }
        for r in rows
    ]


def query_reports(
    conn: sqlite3.Connection,
    *,
    channel: str | None,
    start: date | None,
    end: date | None,
    verdict: str | None,
    page: int,
    page_size: int,
) -> tuple[list[dict[str, Any]], int]:
    """Return one page of matching reports (newest first) and the total match count.

    Filter values are bound as parameters. The SQL fragments below are fixed strings.
    """
    clauses: list[str] = []
    params: list[Any] = []
    if channel is not None:
        clauses.append("(r.channel_name = ? OR r.channel_url = ?)")
        params += [channel, channel]
    if start is not None:
        clauses.append("r.fact_check_date >= ?")
        params.append(start.isoformat())
    if end is not None:
        clauses.append("r.fact_check_date <= ?")
        params.append(end.isoformat())
    if verdict is not None:
        clauses.append(
            "EXISTS (SELECT 1 FROM report_verdicts v WHERE v.video_id = r.video_id AND v.verdict = ?)"
        )
        params.append(verdict)
    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""

    total = conn.execute(f"SELECT COUNT(*) FROM reports r {where}", params).fetchone()[0]
    rows = conn.execute(
        f"SELECT r.* FROM reports r {where} ORDER BY r.sort_key DESC, r.video_id LIMIT ? OFFSET ?",
        [*params, page_size, (page - 1) * page_size],
    ).fetchall()
    items = [
        {
            "video_id": r["video_id"],
            "title": r["title"],
            "channel_name": r["channel_name"],
            "channel_url": r["channel_url"],
            "fact_checked_at": r["fact_checked_at"],
            "claim_count": r["claim_count"],
            "verdict_breakdown": json.loads(r["verdict_breakdown"]),
        }
        for r in rows
    ]
    return items, int(total)
