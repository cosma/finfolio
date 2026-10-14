"""Quota stop: when Tavily credits run out, the run stops. A quota error never becomes "Unverified"."""

from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from finfolio.cli import main
from finfolio.fact_checker import FactChecker
from finfolio.models import ClaimModel, VerdictModel
from finfolio.search.errors import SearchError, SearchQuotaError
from finfolio.search.tavily_client import TavilySearchClient

QUOTA_TEXT = "HTTPError('432 Client Error:  for url: https://api.tavily.com/search')"
VIDEO_ID = "zzzzzzzzzzz"


def make_search_client(monkeypatch) -> TavilySearchClient:
    monkeypatch.setenv("TAVILY_API_KEY", "test-dummy-key")
    client = TavilySearchClient(api_key="test-dummy-key")
    client.tool = MagicMock()
    return client


def test_quota_error_returned_as_text_raises(monkeypatch):
    client = make_search_client(monkeypatch)
    client.tool.invoke.return_value = QUOTA_TEXT

    with pytest.raises(SearchQuotaError):
        client.search("some claim")


def test_quota_exception_raises(monkeypatch):
    client = make_search_client(monkeypatch)
    client.tool.invoke.side_effect = Exception(QUOTA_TEXT)

    with pytest.raises(SearchQuotaError):
        client.search("some claim")


def test_usage_limit_message_raises(monkeypatch):
    client = make_search_client(monkeypatch)
    client.tool.invoke.side_effect = Exception("You have exceeded your usage limit")

    with pytest.raises(SearchQuotaError):
        client.search("some claim")


def test_other_error_raises_search_error(monkeypatch):
    client = make_search_client(monkeypatch)
    client.tool.invoke.side_effect = Exception("connection reset by peer")

    with pytest.raises(SearchError):
        client.search("some claim")


def test_valid_results_are_returned(monkeypatch):
    client = make_search_client(monkeypatch)
    client.tool.invoke.return_value = '[{"url": "https://a.example", "content": "x"}]'

    assert len(client.search("some claim")) == 1


def test_result_text_mentioning_quota_is_not_an_error(monkeypatch):
    """Only error text triggers the stop; a result whose content mentions quota is data."""
    client = make_search_client(monkeypatch)
    client.tool.invoke.return_value = (
        '[{"url": "https://a.example", "content": "the quota debate"}]'
    )

    assert len(client.search("some claim")) == 1


def make_claim(n: int) -> ClaimModel:
    return ClaimModel(
        id=f"c{n}",
        text=f"claim {n}",
        quote=f"quote {n}",
        type="number",
        confidence=0.9,
        timestamp="00:01",
        is_opinion=False,
        is_forecast=False,
    )


def make_verdict(claim_id: str) -> VerdictModel:
    return VerdictModel(
        claim_id=claim_id,
        claim_text="claim",
        verdict="True",
        note="Checked.",
        source_url="https://example.com/source",
        source_title="Source",
        source_date="2026-09-01",
        search_query="query",
        fact_checked_at="2026-10-14T12:00:00Z",
        llm_model="claude-haiku-4-5-20251001",
        reasoning_cost={"tokens_in": 1, "tokens_out": 1, "cost_usd": 0.0},
    )


def test_quota_stop_keeps_earlier_verdicts_and_adds_no_unverified(monkeypatch):
    monkeypatch.setenv("TAVILY_API_KEY", "test-dummy-key")
    config = MagicMock(
        tavily_api_key="test-dummy-key",
        search_timeout_seconds=10.0,
        llm_model="claude-haiku-4-5-20251001",
        anthropic_api_key=None,
    )
    claims = [make_claim(0), make_claim(1), make_claim(2)]

    with (
        patch.object(FactChecker, "_get_llm", return_value=MagicMock()),
        patch.object(FactChecker, "extract_claims_from_summary", return_value=claims),
        patch.object(
            FactChecker,
            "fact_check_claim",
            side_effect=lambda claim, results, **kwargs: make_verdict(claim.id),
        ),
        patch("finfolio.storage.load_summary", return_value={"video_id": VIDEO_ID}),
        patch("finfolio.storage.has_report", return_value=False),
        patch("finfolio.storage.save_report") as save,
    ):
        checker = FactChecker(config)
        checker.ddg_client.search = MagicMock(return_value=[])
        checker.search_client.search = MagicMock(
            side_effect=[
                [{"url": "https://a.example", "content": "x"}],
                SearchQuotaError(QUOTA_TEXT),
            ]
        )

        with pytest.raises(SearchQuotaError):
            checker.run_fact_check_single_video(VIDEO_ID)

    saved_report = save.call_args.args[1]
    assert [v["claim_id"] for v in saved_report["verdicts"]] == ["c0"]
    assert all(v["verdict"] != "Unverified" for v in saved_report["verdicts"])


def test_cli_stops_with_clear_message_and_exit_2():
    with patch("finfolio.cli.Config"), patch("finfolio.cli.FactChecker") as checker_cls:
        checker_cls.return_value.run_fact_check_single_video.side_effect = SearchQuotaError(
            QUOTA_TEXT
        )
        result = CliRunner().invoke(main, ["factcheck", "--video-id", VIDEO_ID])

    assert result.exit_code == 2
    assert "credits are used up" in result.output
