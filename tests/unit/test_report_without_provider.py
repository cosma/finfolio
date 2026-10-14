"""T024: reports no longer carry a top-level search_provider field (FR-014)."""

from unittest.mock import MagicMock, patch

from finfolio.fact_checker import FactChecker
from finfolio.models import ReportModel


def test_report_model_has_no_search_provider_field():
    assert "search_provider" not in ReportModel.model_fields


def test_built_report_has_no_search_provider(monkeypatch):
    monkeypatch.setenv("TAVILY_API_KEY", "test-dummy-key")
    config = MagicMock(
        tavily_api_key="test-dummy-key",
        search_timeout_seconds=10.0,
        llm_model="claude-haiku-4-5-20251001",
        anthropic_api_key=None,
        search_min_confidence=0.8,
    )
    with patch.object(FactChecker, "_get_llm", return_value=MagicMock()):
        checker = FactChecker(config)

    report = checker.build_report("vidnoprov01", {}, [])

    assert "search_provider" not in report
