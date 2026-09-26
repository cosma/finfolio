"""Unit tests for fact-checking verdict assignment logic (US1).

Test-first approach: These tests define the contract for FactChecker.
They will fail initially, then pass once FactChecker is implemented.
"""

from unittest.mock import MagicMock, patch

import pytest

from finfolio.models import ClaimModel, VerdictModel


@pytest.mark.unit
class TestVerdictAssignment:
    """Test fact_check_claim verdict assignment logic."""

    def test_fact_check_claim_returns_verdict_model(self):
        """Test that fact_check_claim returns a VerdictModel instance."""
        from finfolio.config import Config
        from finfolio.fact_checker import FactChecker

        # Mock config
        mock_config = MagicMock(spec=Config)
        mock_config.llm_model = "claude-haiku-4-5-20251001"

        # Create claim
        claim = ClaimModel(
            id="claim_001",
            text="Apple stock closed at $195.42 on Sept 23",
            quote="the stock was trading at one ninety five",
            type="number",
            confidence=0.92,
            timestamp="12:34",
        )

        # Mock search results
        search_results = [
            {
                "title": "Apple Stock Price",
                "url": "https://finance.yahoo.com/quote/AAPL",
                "content": "Apple (AAPL) closed at $195.42 on September 23",
            }
        ]

        # Test
        with patch.object(FactChecker, "_get_llm") as mock_llm:
            mock_llm_instance = MagicMock()
            mock_llm.return_value = mock_llm_instance

            # Mock LLM response
            mock_response = MagicMock()
            mock_response.content = '{"verdict": "True", "note": "Verified against official source", "source_url": "https://finance.yahoo.com/quote/AAPL", "source_title": "Yahoo Finance", "source_date": "2026-09-23"}'
            mock_llm_instance.invoke.return_value = mock_response

            checker = FactChecker(mock_config)
            result = checker.fact_check_claim(claim, search_results)

            assert isinstance(result, VerdictModel)
            assert result.claim_id == "claim_001"
            assert result.verdict in (
                "True",
                "False",
                "Partially supported/overstated",
                "Unverified",
            )

    def test_fact_check_claim_true_verdict(self):
        """Test verdict assignment for True verdict."""
        from finfolio.config import Config
        from finfolio.fact_checker import FactChecker

        mock_config = MagicMock(spec=Config)
        mock_config.llm_model = "claude-haiku-4-5-20251001"

        claim = ClaimModel(
            id="claim_true",
            text="Test true claim",
            quote="test",
            type="number",
            confidence=0.9,
            timestamp="12:34",
        )

        search_results = [{"content": "Verified information"}]

        with patch.object(FactChecker, "_get_llm"):
            checker = FactChecker(mock_config)
            with patch.object(checker, "llm") as mock_llm:
                mock_response = MagicMock()
                mock_response.content = '{"verdict": "True", "note": "Verified", "source_url": "https://example.com", "source_title": "Source", "source_date": "2026-09-25"}'
                mock_llm.invoke.return_value = mock_response

                result = checker.fact_check_claim(claim, search_results)
                assert result.verdict == "True"
                assert result.source_url is not None

    def test_fact_check_claim_false_verdict(self):
        """Test verdict assignment for False verdict."""
        from finfolio.config import Config
        from finfolio.fact_checker import FactChecker

        mock_config = MagicMock(spec=Config)
        mock_config.llm_model = "claude-haiku-4-5-20251001"

        claim = ClaimModel(
            id="claim_false",
            text="Test false claim",
            quote="test",
            type="number",
            confidence=0.9,
            timestamp="12:34",
        )

        search_results = [{"content": "Contradicting information"}]

        with patch.object(FactChecker, "_get_llm"):
            checker = FactChecker(mock_config)
            with patch.object(checker, "llm") as mock_llm:
                mock_response = MagicMock()
                mock_response.content = '{"verdict": "False", "note": "Contradicts sources", "source_url": "https://example.com", "source_title": "Source", "source_date": "2026-09-25"}'
                mock_llm.invoke.return_value = mock_response

                result = checker.fact_check_claim(claim, search_results)
                assert result.verdict == "False"

    def test_fact_check_claim_unverified_verdict(self):
        """Test verdict assignment for Unverified verdict."""
        from finfolio.config import Config
        from finfolio.fact_checker import FactChecker

        mock_config = MagicMock(spec=Config)
        mock_config.llm_model = "claude-haiku-4-5-20251001"

        claim = ClaimModel(
            id="claim_unverified",
            text="Test unverified claim",
            quote="test",
            type="number",
            confidence=0.9,
            timestamp="12:34",
        )

        search_results = []  # No search results

        with patch.object(FactChecker, "_get_llm"):
            checker = FactChecker(mock_config)
            with patch.object(checker, "llm") as mock_llm:
                mock_response = MagicMock()
                mock_response.content = '{"verdict": "Unverified", "note": "No sources found", "source_url": null, "source_title": null, "source_date": null}'
                mock_llm.invoke.return_value = mock_response

                result = checker.fact_check_claim(claim, search_results)
                assert result.verdict == "Unverified"
                assert result.source_url is None

    def test_fact_check_claim_empty_search_results(self):
        """Test that empty search results yield Unverified verdict."""
        from finfolio.config import Config
        from finfolio.fact_checker import FactChecker

        mock_config = MagicMock(spec=Config)
        mock_config.llm_model = "claude-haiku-4-5-20251001"

        claim = ClaimModel(
            id="claim_no_results",
            text="Obscure claim",
            quote="test",
            type="other",
            confidence=0.5,
            timestamp="12:34",
        )

        with patch.object(FactChecker, "_get_llm"):
            checker = FactChecker(mock_config)
            with patch.object(checker, "llm") as mock_llm:
                mock_response = MagicMock()
                mock_response.content = '{"verdict": "Unverified", "note": "No search results available", "source_url": null, "source_title": null, "source_date": null}'
                mock_llm.invoke.return_value = mock_response

                result = checker.fact_check_claim(claim, [])
                assert result.verdict == "Unverified"

    def test_fact_check_claim_note_not_empty(self):
        """Test that verdict note is never empty."""
        from finfolio.config import Config
        from finfolio.fact_checker import FactChecker

        mock_config = MagicMock(spec=Config)
        mock_config.llm_model = "claude-haiku-4-5-20251001"

        claim = ClaimModel(
            id="claim_note",
            text="Test claim",
            quote="test",
            type="number",
            confidence=0.9,
            timestamp="12:34",
        )

        with patch.object(FactChecker, "_get_llm"):
            checker = FactChecker(mock_config)
            with patch.object(checker, "llm") as mock_llm:
                mock_response = MagicMock()
                mock_response.content = '{"verdict": "True", "note": "Verified claim", "source_url": "https://example.com", "source_title": "Source", "source_date": "2026-09-25"}'
                mock_llm.invoke.return_value = mock_response

                result = checker.fact_check_claim(claim, [{"content": "test"}])
                assert result.note != ""
                assert len(result.note) <= 250

    def test_fact_check_claim_partially_supported_verdict(self):
        """Test verdict assignment for Partially supported verdict."""
        from finfolio.config import Config
        from finfolio.fact_checker import FactChecker

        mock_config = MagicMock(spec=Config)
        mock_config.llm_model = "claude-haiku-4-5-20251001"

        claim = ClaimModel(
            id="claim_partial",
            text="Test partially supported claim",
            quote="test",
            type="number",
            confidence=0.9,
            timestamp="12:34",
        )

        with patch.object(FactChecker, "_get_llm"):
            checker = FactChecker(mock_config)
            with patch.object(checker, "llm") as mock_llm:
                mock_response = MagicMock()
                mock_response.content = '{"verdict": "Partially supported/overstated", "note": "Partially accurate", "source_url": "https://example.com", "source_title": "Source", "source_date": "2026-09-25"}'
                mock_llm.invoke.return_value = mock_response

                result = checker.fact_check_claim(claim, [{"content": "partial"}])
                assert result.verdict == "Partially supported/overstated"
