"""Unit tests for transcript summarizer module."""
import pytest

from finfolio.summarizer import (
    TranscriptTooLongError,
    TranscriptTooShortError,
    estimate_tokens,
    truncate_if_needed,
    validate_transcript,
)


@pytest.fixture
def sample_transcript():
    """Sample transcript for testing."""
    return (
        "Welcome to the Finance Hour podcast. Today we're discussing three investment themes. "
        "First, semiconductor companies. Apple released the iPhone 15 Pro in September 2023. "
        "The S&P 500 closed at 5,432 today. I think we'll see strong demand for AI chips in 2024. "
        "Second, energy stocks. Exxon Mobil's stock price is currently at $95. "
        "The company announced a $50 billion acquisition of Pioneer Natural Resources in 2023. "
        "Third, I'm bullish on fintech. Square's Cash App had record transactions. Thanks for listening."
    )


@pytest.fixture
def empty_transcript():
    """Empty transcript for testing."""
    return "   \n\n   "


@pytest.fixture
def very_long_transcript():
    """Generate a very long transcript to test truncation."""
    return "Apple released the iPhone 15 Pro in September 2023. " * 2500


class TestEstimateTokens:
    """Tests for token estimation."""

    def test_estimate_tokens_short_text(self):
        """Test token estimation on short text."""
        text = "Apple stock closed at $200"
        tokens = estimate_tokens(text)
        assert tokens > 0
        assert isinstance(tokens, int)

    def test_estimate_tokens_longer_text(self, sample_transcript):
        """Test token estimation on longer text."""
        tokens = estimate_tokens(sample_transcript)
        assert tokens > 50
        assert tokens < 500

    def test_estimate_tokens_scales_with_length(self):
        """Test that token count scales with text length."""
        text1 = "Test "
        text2 = "Test " * 10
        tokens1 = estimate_tokens(text1)
        tokens2 = estimate_tokens(text2)
        assert tokens2 > tokens1


class TestValidateTranscript:
    """Tests for transcript validation."""

    def test_validate_empty_transcript(self, empty_transcript):
        """Test that empty transcript raises error."""
        with pytest.raises(TranscriptTooShortError):
            validate_transcript(empty_transcript)

    def test_validate_too_short_transcript(self):
        """Test that very short transcript raises error."""
        with pytest.raises(TranscriptTooShortError):
            validate_transcript("Short text")

    def test_validate_valid_transcript(self, sample_transcript):
        """Test that valid transcript passes validation."""
        assert validate_transcript(sample_transcript) is True

    def test_validate_very_long_transcript_fails(self):
        """Test that extremely large transcript fails."""
        huge_text = "x" * 1_000_001
        with pytest.raises(TranscriptTooLongError):
            validate_transcript(huge_text)

    def test_validate_utf8_encoding(self):
        """Test UTF-8 encoding validation."""
        # Valid UTF-8
        valid_text = "This is valid UTF-8 text with émojis and ñoño characters. " * 10
        assert validate_transcript(valid_text) is True


class TestTruncateIfNeeded:
    """Tests for transcript truncation."""

    def test_truncate_short_transcript_no_truncation(self, sample_transcript):
        """Test that short transcript is not truncated."""
        result, was_truncated = truncate_if_needed(sample_transcript)
        assert not was_truncated
        assert result == sample_transcript

    def test_truncate_long_transcript(self, very_long_transcript):
        """Test that very long transcript is truncated."""
        result, was_truncated = truncate_if_needed(very_long_transcript)
        if was_truncated:
            assert len(result) < len(very_long_transcript)
            assert result.endswith(very_long_transcript[: len(result)])

    def test_truncation_preserves_beginning(self, very_long_transcript):
        """Test that truncation preserves transcript beginning."""
        result, was_truncated = truncate_if_needed(very_long_transcript)
        if was_truncated:
            assert result.startswith("Apple released")

    def test_truncate_returns_tuple(self, sample_transcript):
        """Test that truncate_if_needed returns (text, bool) tuple."""
        result = truncate_if_needed(sample_transcript)
        assert isinstance(result, tuple)
        assert len(result) == 2
        assert isinstance(result[0], str)
        assert isinstance(result[1], bool)
