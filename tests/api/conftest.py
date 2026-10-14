"""Fixtures for API tests: a temporary storage tree, helpers to fill it, and a started client.

Tests write their data first and then call make_client(), because the index is built at startup.
Nothing here touches the real storage/ directory.
"""

import json
from collections.abc import Callable, Iterator
from pathlib import Path
from typing import Any

import pytest

from finfolio import storage
from finfolio.models import DISCLAIMER

CANONICAL_VERDICTS = ["True", "Partially supported", "Unverified", "False"]
ReportWriter = Callable[..., None]
DigestWriter = Callable[..., None]


@pytest.fixture
def api_storage(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Point the storage module at an empty temporary storage tree."""
    root = tmp_path / "storage"
    videos = root / "reports" / "videos"
    monthly = root / "reports" / "monthly"
    videos.mkdir(parents=True)
    monthly.mkdir(parents=True)
    monkeypatch.setattr(storage, "STORAGE_DIR", root)
    monkeypatch.setattr(storage, "REPORTS_DIR", videos)
    monkeypatch.setattr(storage, "DIGESTS_DIR", monthly)
    return root


@pytest.fixture
def write_report(api_storage: Path) -> ReportWriter:
    """Write a stored per-video report. verdicts is the list of verdict names, one per claim."""

    def _write(
        video_id: str,
        *,
        channel_name: str = "Channel A",
        channel_url: str = "https://www.youtube.com/@channel-a",
        fact_checked_at: str = "2026-09-10T12:00:00.000000Z",
        verdicts: list[str] | tuple[str, ...] = ("True",),
    ) -> None:
        report: dict[str, Any] = {
            "video_id": video_id,
            "title": f"Title {video_id}",
            "channel_name": channel_name,
            "channel_url": channel_url,
            "source_url": f"https://www.youtube.com/watch?v={video_id}",
            "transcript_source": "youtube-captions",
            "fact_checked_at": fact_checked_at,
            "fact_check_duration_seconds": 1.5,
            "search_provider": "Tavily",
            "llm_model": "claude-haiku-4-5-20251001",
            "cost": {"search_usd": 0.0, "llm_usd": 0.01, "total_usd": 0.01},
            "summary": {"metadata": {"publication_date": "2026-09-01"}},
            "verdicts": [
                {
                    "claim_id": f"claim_{i}",
                    "claim_text": f"Claim {i}",
                    "verdict": name,
                    "note": "note",
                    "source_url": "https://example.com/source",
                    "source_title": "Source",
                    "source_date": "2026-09-01",
                }
                for i, name in enumerate(verdicts)
            ],
            "claim_count": len(verdicts),
            "verdict_count": len(verdicts),
            "verdict_breakdown": {name: list(verdicts).count(name) for name in CANONICAL_VERDICTS},
            "disclaimer": DISCLAIMER,
        }
        path = api_storage / "reports" / "videos" / f"{video_id}.json"
        path.write_text(json.dumps(report), encoding="utf-8")

    return _write


@pytest.fixture
def write_digest(api_storage: Path) -> DigestWriter:
    """Write a stored monthly digest for a YYYY-MM month."""

    def _write(
        month: str, *, report_count: int = 0, verdict_breakdown: dict[str, int] | None = None
    ) -> None:
        digest: dict[str, Any] = {
            "month": month,
            "generated_at": f"{month}-28T23:00:00.000000Z",
            "report_count": report_count,
            "verdict_breakdown": verdict_breakdown or dict.fromkeys(CANONICAL_VERDICTS, 0),
            "per_channel_breakdown": [
                {
                    "channel_name": "Channel A",
                    "channel_url": "https://www.youtube.com/@channel-a",
                    "video_count": report_count,
                    "verdict_breakdown": {},
                }
            ],
            "monetization_summary": [
                {"channel_name": "Channel A", "disclosure": "Promotes a course"}
            ],
            "disclaimer": DISCLAIMER,
        }
        path = api_storage / "reports" / "monthly" / f"{month}.json"
        path.write_text(json.dumps(digest), encoding="utf-8")

    return _write


@pytest.fixture
def make_client(api_storage: Path) -> Iterator[Callable[[], Any]]:
    """Return a factory that starts the app (building the index) and yields a TestClient."""
    from fastapi.testclient import TestClient

    from finfolio.api.app import app

    started: list[Any] = []

    def _make() -> Any:
        client = TestClient(app)
        client.__enter__()
        started.append(client)
        return client

    yield _make
    for client in started:
        client.__exit__(None, None, None)
