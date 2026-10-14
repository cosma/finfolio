"""T012: the free-source confidence threshold is a setting (FR-012), default 0.8, validated to [0, 1]."""

import pytest

from finfolio.config import Config

SETTING = "FINFOLIO_SEARCH_MIN_CONFIDENCE"


def test_default_threshold_is_0_8(monkeypatch):
    monkeypatch.delenv(SETTING, raising=False)

    assert Config().search_min_confidence == 0.8


def test_setting_overrides_default(monkeypatch):
    monkeypatch.setenv(SETTING, "0.9")

    assert Config().search_min_confidence == 0.9


@pytest.mark.parametrize("value", ["1.5", "-0.1"])
def test_out_of_range_value_is_rejected_at_validation(monkeypatch, value):
    monkeypatch.setenv(SETTING, value)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-dummy-key")
    monkeypatch.setenv("TAVILY_API_KEY", "test-dummy-key")

    with pytest.raises(ValueError, match=SETTING):
        Config().validate()


def test_non_numeric_value_is_rejected(monkeypatch):
    monkeypatch.setenv(SETTING, "high")

    with pytest.raises(ValueError, match=SETTING):
        Config()


def test_threshold_decides_whether_free_verdict_is_accepted(monkeypatch):
    from tests.unit.test_search_chain import DDG_HIT, claim, make_checker

    strict, _ = make_checker(monkeypatch, llm_fields={"confidence": 0.85}, threshold=0.9)
    strict.ddg_client.search.return_value = DDG_HIT
    strict.search_client.search.return_value = DDG_HIT
    assert strict.verify_claim(claim()).verified_by == "tavily"

    lenient, _ = make_checker(monkeypatch, llm_fields={"confidence": 0.85}, threshold=0.8)
    lenient.ddg_client.search.return_value = DDG_HIT
    assert lenient.verify_claim(claim()).verified_by == "duckduckgo"
