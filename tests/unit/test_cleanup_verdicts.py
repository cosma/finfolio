"""Cleanup rules for stored verdicts, and the pending check for claims that lost their verdict."""

import importlib.util
import json
from pathlib import Path

from finfolio import storage

SCRIPT = Path(__file__).parents[2] / "scripts" / "cleanup_claim_verdicts.py"
spec = importlib.util.spec_from_file_location("cleanup_claim_verdicts", SCRIPT)
cleanup = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cleanup)


def test_clean_report_removes_unverified_and_marks_tavily():
    report = {
        "verdicts": [
            {"claim_id": "c0", "verdict": "Unverified"},
            {"claim_id": "c1", "verdict": "True"},
            {"claim_id": "c2", "verdict": "False", "verified_by": "duckduckgo"},
        ],
        "verdict_count": 3,
        "verdict_breakdown": {"True": 1, "Partially supported": 0, "Unverified": 1, "False": 1},
    }

    cleaned, removed, marked = cleanup.clean_report(report)

    assert [v["claim_id"] for v in cleaned["verdicts"]] == ["c1", "c2"]
    assert cleaned["verdicts"][0]["verified_by"] == "tavily"
    assert cleaned["verdicts"][1]["verified_by"] == "duckduckgo"
    assert (removed, marked) == (1, 1)
    assert cleaned["verdict_count"] == 2
    assert cleaned["verdict_breakdown"] == {
        "True": 1,
        "Partially supported": 0,
        "Unverified": 0,
        "False": 1,
    }


def test_pending_when_checkable_claim_lost_its_verdict(tmp_path, monkeypatch):
    summaries, reports = tmp_path / "summaries", tmp_path / "videos"
    summaries.mkdir()
    reports.mkdir()
    summary = {
        "claims": [
            {"id": "c0", "is_opinion": False, "is_forecast": False},
            {"id": "c1", "is_opinion": False, "is_forecast": False},
            {"id": "c2", "is_opinion": True, "is_forecast": False},
        ]
    }
    (summaries / "aaaaaaaaaaa.json").write_text(json.dumps(summary), encoding="utf-8")
    (reports / "aaaaaaaaaaa.json").write_text(
        json.dumps({"verdicts": [{"claim_id": "c0", "verdict": "True", "verified_by": "tavily"}]}),
        encoding="utf-8",
    )
    monkeypatch.setattr(storage, "SUMMARIES_DIR", summaries)
    monkeypatch.setattr(storage, "REPORTS_DIR", reports)

    assert storage.list_pending_videos() == ["aaaaaaaaaaa"]


def test_not_pending_when_only_opinion_claims_lack_verdicts(tmp_path, monkeypatch):
    summaries, reports = tmp_path / "summaries", tmp_path / "videos"
    summaries.mkdir()
    reports.mkdir()
    summary = {
        "claims": [
            {"id": "c0", "is_opinion": False, "is_forecast": False},
            {"id": "c1", "is_opinion": True, "is_forecast": False},
        ]
    }
    (summaries / "bbbbbbbbbbb.json").write_text(json.dumps(summary), encoding="utf-8")
    (reports / "bbbbbbbbbbb.json").write_text(
        json.dumps({"verdicts": [{"claim_id": "c0", "verdict": "True", "verified_by": "tavily"}]}),
        encoding="utf-8",
    )
    monkeypatch.setattr(storage, "SUMMARIES_DIR", summaries)
    monkeypatch.setattr(storage, "REPORTS_DIR", reports)

    assert storage.list_pending_videos() == []


def test_clean_report_drops_top_level_search_provider():
    report = {"verdicts": [], "search_provider": "Tavily"}

    cleaned, _, _ = cleanup.clean_report(report)

    assert "search_provider" not in cleaned


def test_final_unverified_verdict_with_verified_by_is_kept():
    """An Unverified verdict recorded as final (verified_by set, FR-013) is not removed."""
    report = {"verdicts": [{"claim_id": "c0", "verdict": "Unverified", "verified_by": "tavily"}]}

    cleaned, removed, _ = cleanup.clean_report(report)

    assert [v["claim_id"] for v in cleaned["verdicts"]] == ["c0"]
    assert removed == 0
