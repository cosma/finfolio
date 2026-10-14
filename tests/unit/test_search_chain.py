"""Search chain: DuckDuckGo first, Tavily when DuckDuckGo is not a confident answer. Tavily failure stops."""

import json
from unittest.mock import MagicMock, patch

import pytest

from finfolio.fact_checker import FactChecker
from finfolio.models import ClaimModel
from finfolio.search.errors import SearchError

DDG_HIT = [{"title": "Source", "url": "https://a.example", "content": "fact"}]


def make_checker(monkeypatch, llm_fields: dict | None = None, llm_text: str | None = None):
    monkeypatch.setenv("TAVILY_API_KEY", "test-dummy-key")
    config = MagicMock(
        tavily_api_key="test-dummy-key",
        search_timeout_seconds=10.0,
        llm_model="claude-haiku-4-5-20251001",
        anthropic_api_key=None,
    )
    fields = llm_fields or {}
    llm = MagicMock()
    llm.invoke.return_value = MagicMock(
        content=llm_text
        if llm_text is not None
        else json.dumps(
            {
                "verdict": "True",
                "note": "Stated in source.",
                "source_url": "https://a.example",
                "source_title": "Source",
                "source_date": "2026-09-01",
                "confidence": 0.95,
                **fields,
            }
        )
    )
    with patch.object(FactChecker, "_get_llm", return_value=llm):
        checker = FactChecker(config)
    checker.ddg_client = MagicMock()
    checker.search_client = MagicMock()
    return checker, llm


def claim() -> ClaimModel:
    return ClaimModel(
        id="c0",
        text="Revenue doubled",
        quote="q",
        type="number",
        confidence=0.9,
        timestamp="00:01",
        is_opinion=False,
        is_forecast=False,
    )


def test_confident_duckduckgo_verdict_is_accepted_without_tavily(monkeypatch):
    checker, _ = make_checker(monkeypatch)
    checker.ddg_client.search.return_value = DDG_HIT

    verdict = checker.verify_claim(claim())

    assert verdict.verified_by == "duckduckgo"
    assert verdict.confidence == 0.95
    checker.search_client.search.assert_not_called()


@pytest.mark.parametrize(
    "fields", [{"confidence": 0.5}, {"verdict": "Unverified", "confidence": 0.95}]
)
def test_unconfident_or_unverified_duckduckgo_falls_back_to_tavily(monkeypatch, fields):
    checker, _ = make_checker(monkeypatch, llm_fields=fields)
    checker.ddg_client.search.return_value = DDG_HIT
    checker.search_client.search.return_value = DDG_HIT

    verdict = checker.verify_claim(claim())

    assert verdict.verified_by == "tavily"
    checker.search_client.search.assert_called_once()


def test_empty_duckduckgo_goes_straight_to_tavily(monkeypatch):
    checker, llm = make_checker(monkeypatch)
    checker.ddg_client.search.return_value = []
    checker.search_client.search.return_value = DDG_HIT

    verdict = checker.verify_claim(claim())

    assert verdict.verified_by == "tavily"
    assert llm.invoke.call_count == 1


def test_duckduckgo_failure_falls_back_to_tavily(monkeypatch):
    checker, _ = make_checker(monkeypatch)
    checker.ddg_client.search.side_effect = RuntimeError("rate limited")
    checker.search_client.search.return_value = DDG_HIT

    assert checker.verify_claim(claim()).verified_by == "tavily"


def test_tavily_failure_raises_and_records_no_verdict(monkeypatch):
    checker, _ = make_checker(monkeypatch)
    checker.ddg_client.search.return_value = []
    checker.search_client.search.side_effect = SearchError("Tavily search timed out")

    with pytest.raises(SearchError):
        checker.verify_claim(claim())


def test_unparseable_llm_output_is_not_a_final_verdict(monkeypatch):
    """A parse failure becomes Unverified with no verified_by, so it is checked again next run."""
    checker, _ = make_checker(monkeypatch, llm_text="not json at all")
    checker.ddg_client.search.return_value = DDG_HIT
    checker.search_client.search.return_value = DDG_HIT

    verdict = checker.verify_claim(claim())

    assert verdict.verdict == "Unverified"
    assert verdict.verified_by is None
    checker.search_client.search.assert_called_once()


def test_confidence_is_clamped_to_unit_interval(monkeypatch):
    checker, _ = make_checker(monkeypatch, llm_fields={"confidence": 1.7})
    checker.ddg_client.search.return_value = DDG_HIT

    assert checker.verify_claim(claim()).confidence == 1.0
