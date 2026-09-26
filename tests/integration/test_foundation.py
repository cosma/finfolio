"""Integration test for fact-checking module foundation (Phase 2).

Verifies that Config, LangChain, Tavily, and logging can be instantiated.
No API calls are made; focuses on initialization and structure.
"""

import pytest

from finfolio.config import Config
from finfolio.logging_utils import configure_logging
from finfolio.models import ClaimModel, CostModel, ReportModel, VerdictModel


@pytest.mark.integration
class TestFoundationSetup:
    """Test foundation infrastructure setup."""

    def test_config_loads_from_env(self, monkeypatch):
        """Test that Config loads values from environment."""
        monkeypatch.setenv("FINFOLIO_LLM_MODEL", "claude-haiku-4-5-20251001")
        monkeypatch.setenv("FINFOLIO_STORAGE_DIR", "/tmp/test-storage")
        monkeypatch.setenv("FINFOLIO_SEARCH_TIMEOUT", "15.0")
        monkeypatch.setenv("FINFOLIO_LOG_LEVEL", "DEBUG")

        config = Config()
        assert config.llm_model == "claude-haiku-4-5-20251001"
        assert config.storage_dir == "/tmp/test-storage"
        assert config.search_timeout_seconds == 15.0
        assert config.log_level == "DEBUG"

    def test_config_has_defaults(self):
        """Test that Config provides sensible defaults."""
        config = Config()
        assert config.llm_model == "claude-haiku-4-5-20251001"
        assert config.log_level == "INFO"
        assert config.search_timeout_seconds == 10.0
        assert config.storage_dir == "storage"

    def test_config_validate_missing_keys(self, monkeypatch):
        """Test that Config.validate() fails when API keys are missing."""
        # Clear API keys
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        monkeypatch.delenv("TAVILY_API_KEY", raising=False)

        config = Config()
        with pytest.raises(ValueError) as exc_info:
            config.validate()
        assert "ANTHROPIC_API_KEY" in str(exc_info.value)

    def test_config_validate_succeeds_with_keys(self, monkeypatch):
        """Test that Config.validate() succeeds when API keys are set."""
        monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key-123")
        monkeypatch.setenv("TAVILY_API_KEY", "test-tavily-key-456")

        config = Config()
        config.validate()  # Should not raise

    def test_logging_configures_without_error(self):
        """Test that logging can be configured."""
        logger = configure_logging(level="INFO")
        assert logger is not None
        assert logger.name == "finfolio"
        assert len(logger.handlers) > 0

    def test_logging_different_levels(self):
        """Test logging configuration with different levels."""
        for level in ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]:
            logger = configure_logging(level=level)
            assert logger is not None

    def test_models_can_be_instantiated(self):
        """Test that Pydantic models can be created."""
        # ClaimModel
        claim = ClaimModel(
            id="test_001",
            text="Test claim",
            quote="test",
            type="number",
            confidence=0.9,
            timestamp="12:34",
        )
        assert claim.id == "test_001"

        # CostModel
        cost = CostModel(search_usd=0.01, llm_usd=0.01, total_usd=0.02)
        assert cost.total_usd == 0.02

        # VerdictModel
        verdict = VerdictModel(
            claim_id="test_001",
            claim_text="Test claim",
            verdict="True",
            note="Verified",
            source_url="https://example.com",
            source_title="Example",
            source_date="2026-09-25",
            search_query="test",
            fact_checked_at="2026-09-25T15:30:00Z",
            llm_model="claude-haiku-4-5-20251001",
            reasoning_cost={"tokens_in": 100, "tokens_out": 50, "cost_usd": 0.00005},
        )
        assert verdict.verdict == "True"

        # ReportModel
        report = ReportModel(
            video_id="test_vid",
            title="Test",
            channel_name="Test Channel",
            channel_url="https://example.com",
            source_url="https://youtube.com/watch?v=test",
            transcript_source="YouTube API",
            fact_checked_at="2026-09-25T15:30:00Z",
            fact_check_duration_seconds=10.0,
            search_provider="Tavily",
            llm_model="claude-haiku-4-5-20251001",
            cost={"search_usd": 0.0, "llm_usd": 0.0, "total_usd": 0.0},
            summary={},
            verdicts=[],
            claim_count=0,
            verdict_count=0,
            verdict_breakdown={
                "True": 0,
                "Partially supported/overstated": 0,
                "Unverified": 0,
                "False": 0,
            },
            disclaimer="FinFolio reports facts and their accuracy. This is not financial advice.",
        )
        assert report.video_id == "test_vid"

    def test_tavily_client_initialization(self):
        """Test that TavilySearchClient can be initialized."""
        from finfolio.search.tavily_client import TavilySearchClient

        client = TavilySearchClient(api_key="test-key", timeout_seconds=10.0)
        assert client.api_key == "test-key"
        assert client.timeout_seconds == 10.0

    def test_cost_tracking_callback_initialization(self):
        """Test that CostTrackingCallback can be initialized."""
        from finfolio.llm.cost_tracking import CostTrackingCallback

        callback = CostTrackingCallback()
        summary = callback.get_summary()
        assert summary["total_tokens_in"] == 0
        assert summary["total_tokens_out"] == 0
        assert summary["total_cost_usd"] == 0.0

    def test_prompts_available(self):
        """Test that prompt templates are available."""
        from finfolio.llm.prompts import get_verdict_prompt

        prompt = get_verdict_prompt(claim_text="Test claim", search_results="Test results")
        assert "Test claim" in prompt
        assert "Test results" in prompt
        assert "verdict" in prompt.lower()
