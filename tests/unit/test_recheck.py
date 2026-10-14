"""Verdicts without verified_by (old Unverified results, failed parses) are checked again, and replaced."""

import json
from unittest.mock import MagicMock, patch

from finfolio import storage
from finfolio.fact_checker import FactChecker, extract_completed_claim_ids
from finfolio.models import ClaimModel, verdict_needs_recheck

LEGACY_UNVERIFIED = {"claim_id": "c0", "verdict": "Unverified", "note": "No search results"}
NEW_UNVERIFIED = {
    "claim_id": "c1",
    "verdict": "Unverified",
    "note": "Searched",
    "verified_by": "tavily",
}
TRUE_VERDICT = {"claim_id": "c2", "verdict": "True", "note": "x", "source_url": "https://a.example"}


def test_recheck_rule():
    assert verdict_needs_recheck(LEGACY_UNVERIFIED)
    assert not verdict_needs_recheck(NEW_UNVERIFIED)
    assert not verdict_needs_recheck(TRUE_VERDICT)


def test_legacy_unverified_is_not_treated_as_completed():
    report = {"verdicts": [LEGACY_UNVERIFIED, NEW_UNVERIFIED, TRUE_VERDICT]}

    assert extract_completed_claim_ids(report) == {"c1", "c2"}


def test_pending_list_includes_report_with_legacy_unverified(tmp_path, monkeypatch):
    summaries, reports = tmp_path / "summaries", tmp_path / "videos"
    summaries.mkdir()
    reports.mkdir()
    for vid in ("aaaaaaaaaaa", "bbbbbbbbbbb"):
        (summaries / f"{vid}.json").write_text("{}", encoding="utf-8")
    (reports / "aaaaaaaaaaa.json").write_text(json.dumps({"verdicts": [LEGACY_UNVERIFIED]}))
    (reports / "bbbbbbbbbbb.json").write_text(json.dumps({"verdicts": [TRUE_VERDICT]}))
    monkeypatch.setattr(storage, "SUMMARIES_DIR", summaries)
    monkeypatch.setattr(storage, "REPORTS_DIR", reports)

    assert storage.list_pending_videos() == ["aaaaaaaaaaa"]


def test_rerun_replaces_legacy_verdict_with_checked_one(tmp_path, monkeypatch):
    monkeypatch.setenv("TAVILY_API_KEY", "test-dummy-key")
    reports = tmp_path / "videos"
    reports.mkdir()
    (reports / "zzzzzzzzzzz.json").write_text(json.dumps({"verdicts": [LEGACY_UNVERIFIED]}))
    config = MagicMock(
        tavily_api_key="test-dummy-key",
        search_timeout_seconds=10.0,
        llm_model="claude-haiku-4-5-20251001",
        anthropic_api_key=None,
    )
    claim = ClaimModel(
        id="c0",
        text="Revenue doubled",
        quote="q",
        type="number",
        confidence=0.9,
        timestamp="00:01",
        is_opinion=False,
        is_forecast=False,
    )
    llm = MagicMock()
    llm.invoke.return_value = MagicMock(
        content=json.dumps(
            {
                "verdict": "True",
                "note": "Stated.",
                "source_url": "https://a.example",
                "source_title": "A",
                "source_date": "2026-09-01",
                "confidence": 0.95,
            }
        )
    )

    with (
        patch.object(FactChecker, "_get_llm", return_value=llm),
        patch.object(FactChecker, "extract_claims_from_summary", return_value=[claim]),
        patch("finfolio.storage.load_summary", return_value={"video_id": "zzzzzzzzzzz"}),
        patch("finfolio.storage.REPORTS_DIR", reports),
        patch("finfolio.storage.save_report") as save,
    ):
        checker = FactChecker(config)
        checker.ddg_client = MagicMock()
        checker.ddg_client.search.return_value = [
            {"title": "A", "url": "https://a.example", "content": "x"}
        ]
        checker.run_fact_check_single_video("zzzzzzzzzzz")

    verdicts = save.call_args.args[1]["verdicts"]
    assert [(v["claim_id"], v["verdict"], v["verified_by"]) for v in verdicts] == [
        ("c0", "True", "duckduckgo")
    ]
