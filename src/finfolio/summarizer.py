"""LangChain-based transcript summarization pipeline."""

import json
import logging
import os
import sys
import time
from datetime import UTC, datetime
from typing import Any

import anthropic
import tiktoken
from langchain_anthropic import ChatAnthropic
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import PromptTemplate
from pydantic import ValidationError

from finfolio import storage
from finfolio.models import ClaimModel
from finfolio.summarizer_schema import Claim, SummaryMetadata, SummaryOutput

logger = logging.getLogger(__name__)


def _log_operation(event: str, status: str, **kwargs: Any) -> None:
    """Log structured JSON operation to stdout."""
    log_entry = {
        "timestamp": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "event": event,
        "status": status,
        **kwargs,
    }
    print(json.dumps(log_entry, default=str))
    sys.stdout.flush()


class TranscriptTooShortError(Exception):
    """Raised when transcript is too short or empty."""

    pass


class TranscriptTooLongError(Exception):
    """Raised when transcript exceeds context window after truncation."""

    pass


class LLMAPIError(Exception):
    """Raised when LLM API call fails after retries."""

    pass


class InvalidOutputError(Exception):
    """Raised when LLM output fails schema validation."""

    pass


def estimate_tokens(text: str) -> int:
    """Estimate token count of text using tiktoken."""
    try:
        encoding = tiktoken.get_encoding("cl100k_base")  # Haiku uses same encoding
        tokens = encoding.encode(text)
        return len(tokens)
    except Exception as e:
        _log_operation("token_estimation_failed", "failed", error=str(e))
        return len(text) // 4  # Conservative fallback (4 chars ≈ 1 token)


def validate_transcript(transcript_text: str) -> bool:
    """Validate transcript is non-empty and reasonable."""
    if not transcript_text or not transcript_text.strip():
        raise TranscriptTooShortError("Transcript is empty or whitespace-only")

    if len(transcript_text) < 50:
        raise TranscriptTooShortError("Transcript is too short (minimum 50 characters)")

    if len(transcript_text) > 1_000_000:
        raise TranscriptTooLongError("Transcript exceeds 1MB")

    try:
        transcript_text.encode("utf-8")
    except UnicodeEncodeError as e:
        raise TranscriptTooShortError(f"Transcript has invalid UTF-8 encoding: {e}") from e

    return True


def truncate_if_needed(transcript_text: str) -> tuple[str, bool]:
    """Truncate transcript if it exceeds 85% of context window."""
    token_count = estimate_tokens(transcript_text)
    truncation_threshold = int(100_000 * 0.85)

    if token_count > truncation_threshold:
        truncation_ratio = truncation_threshold / token_count
        char_count = len(transcript_text)
        truncate_at = int(char_count * truncation_ratio * 0.75)
        truncated = transcript_text[:truncate_at]

        new_token_count = estimate_tokens(truncated)
        _log_operation(
            "transcript_truncated",
            "warning",
            original_tokens=token_count,
            truncated_tokens=new_token_count,
        )
        return truncated, True

    return transcript_text, False


def _get_llm_model() -> str:
    """Get LLM model for summarization from environment or use default."""
    return os.getenv(
        "FINFOLIO_LLM_MODEL_SUMMARIZATION", "claude-haiku-4-5-20251001"
    )


def get_llm_model_factcheck() -> str:
    """Get LLM model for fact-checking from environment or use default.

    Used by Module 3 (Fact-Checking) for more accurate verification.
    """
    return os.getenv(
        "FINFOLIO_LLM_MODEL_FACTCHECK", "claude-3-5-sonnet-20241022"
    )


def _get_api_key() -> str:
    """Get Anthropic API key from environment."""
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise LLMAPIError("ANTHROPIC_API_KEY environment variable not set")
    return api_key


def _transform_claims_for_factcheck(claims: list[Claim], video_id: str) -> list[dict[str, Any]]:
    """Transform summarizer claims to fact-checker ClaimModel format.

    Maps field names and generates IDs for compatibility with Module 3 (Fact-Checking).

    Args:
        claims: Claims from summarizer in old format
        video_id: Video ID for generating unique claim IDs

    Returns:
        List of claim dicts compatible with ClaimModel
    """
    transformed = []
    for i, claim in enumerate(claims, 1):
        # Generate unique claim ID based on video and index
        claim_id = f"{video_id}_claim_{i:03d}"

        # Transform field names and add missing fields
        transformed_claim = {
            "id": claim_id,
            "text": claim.claim,  # Map 'claim' to 'text'
            "quote": claim.quote,
            "type": str(claim.type),
            "confidence": claim.confidence_score or 0.5,  # Default to 0.5 if None
            "timestamp": claim.source_timestamp or "00:00",  # Default to 00:00 if None
            "is_opinion": False,  # Claims extracted as factual by default
            "is_forecast": False,
        }

        # Validate the transformed claim against ClaimModel
        try:
            ClaimModel(**transformed_claim)
            transformed.append(transformed_claim)
        except ValidationError as e:
            logger.warning(f"Skipping invalid claim {claim_id}: {str(e)}")
            continue

    return transformed


def summarize_transcript(transcript_text: str, video_id: str) -> SummaryOutput:
    """
    Summarize a transcript using LangChain + Claude.

    Args:
        transcript_text: Full transcript text
        video_id: Video identifier for logging

    Returns:
        SummaryOutput with summary, claims, and metadata

    Raises:
        TranscriptTooShortError: If transcript is empty
        TranscriptTooLongError: If transcript exceeds limits
        LLMAPIError: If LLM call fails after retries
        InvalidOutputError: If output fails schema validation
    """
    validate_transcript(transcript_text)

    transcript_text, was_truncated = truncate_if_needed(transcript_text)
    transcript_tokens = estimate_tokens(transcript_text)

    model = _get_llm_model()
    api_key = _get_api_key()

    prompt_template = PromptTemplate(
        input_variables=["transcript"],
        template="""You are a financial content analyzer. Extract a summary and discrete factual claims from the transcript below.

CRITICAL INSTRUCTIONS:
1. Extract ONLY verifiable factual statements into the claims list
2. Exclude opinions, forecasts, predictions ("I think", "I believe", "I forecast", "bullish", "bearish", etc.)
3. Each claim must be factually verifiable from the transcript
4. Exclude all sponsored content (sections with "brought to you by", "sponsored by", "partner", "affiliate")
5. Each claim must include: type (number, date, deal, company-fact, product-fact), claim text, exact quote from transcript
6. Try to include optional source timestamp in MM:SS format if possible
7. Include optional confidence_score (0-1) for how certain this is a factual claim

Return ONLY valid JSON in this exact format (no markdown, no extra text):
{{
  "summary": "1-2 paragraph plain-language summary (150-400 words) of key investment insights",
  "claims": [
    {{
      "type": "number|date|deal|company-fact|product-fact",
      "claim": "The factual statement",
      "quote": "Exact text from transcript",
      "source_timestamp": "MM:SS" or null,
      "confidence_score": 0.0-1.0 or null
    }}
  ]
}}

TRANSCRIPT:
{transcript}
""",
    )

    parser = JsonOutputParser()

    llm = ChatAnthropic(
        model=model,
        api_key=api_key,
        temperature=0.3,
    )

    chain = prompt_template | llm | parser

    max_retries = 3
    retry_delay = 1

    for attempt in range(max_retries):
        try:
            output = chain.invoke({"transcript": transcript_text})

            if not isinstance(output, dict):
                raise InvalidOutputError("LLM did not return a dictionary")

            if "summary" not in output or "claims" not in output:
                raise InvalidOutputError("Missing 'summary' or 'claims' in LLM output")

            summary_str = output["summary"]
            claims_data = output["claims"]

            claims = []
            if isinstance(claims_data, list):
                for claim_dict in claims_data:
                    if isinstance(claim_dict, dict):
                        claims.append(Claim(**claim_dict))

            timestamp = datetime.now(UTC)

            input_tokens = transcript_tokens
            output_tokens = len(summary_str.split()) + len(str(claims))
            cost_usd = (input_tokens * 0.80 + output_tokens * 2.40) / 1_000_000

            metadata = SummaryMetadata(
                transcript_tokens=transcript_tokens,
                model=model,
                temperature=0.3,
                timestamp=timestamp,
                cost_usd=cost_usd,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                transcript_truncated=was_truncated,
            )

            summary_output = SummaryOutput(summary=summary_str, claims=claims, metadata=metadata)

            _log_operation(
                "llm_call_complete",
                "success",
                video_id=video_id,
                claims_count=len(claims),
                cost_usd=round(cost_usd, 6),
            )

            return summary_output

        except anthropic.APIConnectionError as e:
            error_detail = f"Connection error: {str(e)}"
            _log_operation(
                "llm_retry",
                "warning",
                attempt=attempt + 1,
                error_type="APIConnectionError",
                error_detail=error_detail,
                video_id=video_id,
            )
            if attempt < max_retries - 1:
                time.sleep(retry_delay)
                retry_delay *= 2
            else:
                raise LLMAPIError(
                    f"LLM API connection failed after {max_retries} retries: {e}"
                ) from e

        except anthropic.AuthenticationError as e:
            error_detail = str(e)
            _log_operation(
                "llm_error",
                "failed",
                video_id=video_id,
                attempt=attempt + 1,
                error_type="AuthenticationError",
                error_detail=error_detail,
                suggestion="Check ANTHROPIC_API_KEY is set correctly (format: sk-ant-v4-...)",
            )
            if attempt < max_retries - 1:
                time.sleep(retry_delay)
                retry_delay *= 2
            else:
                raise LLMAPIError(
                    f"Authentication failed: {e}. Ensure ANTHROPIC_API_KEY is set correctly (should start with 'sk-ant-v4-')"
                ) from e

        except anthropic.RateLimitError as e:
            _log_operation(
                "llm_rate_limit",
                "warning",
                attempt=attempt + 1,
                error_type="RateLimitError",
                error_detail="API rate limit exceeded",
                video_id=video_id,
            )
            if attempt < max_retries - 1:
                time.sleep(retry_delay)
                retry_delay *= 2
            else:
                raise LLMAPIError(f"Rate limit exceeded after {max_retries} retries") from e

        except (ValidationError, InvalidOutputError) as e:
            error_detail = str(e)
            _log_operation(
                "llm_output_invalid",
                "failed",
                video_id=video_id,
                error_type=type(e).__name__,
                error_detail=error_detail,
                suggestion="LLM returned invalid JSON or schema mismatch",
            )
            raise InvalidOutputError(f"LLM output validation failed: {e}") from e

        except Exception as e:
            error_detail = str(e)
            _log_operation(
                "llm_error",
                "failed",
                video_id=video_id,
                attempt=attempt + 1,
                error_type=type(e).__name__,
                error_detail=error_detail,
            )
            if attempt < max_retries - 1:
                time.sleep(retry_delay)
                retry_delay *= 2
            else:
                raise LLMAPIError(f"LLM API failed after {max_retries} retries: {e}") from e

    raise LLMAPIError("Summarization failed unexpectedly")


def process_transcript_safe(video_id: str, transcript_text: str) -> SummaryOutput | None:
    """
    Process a transcript with idempotency check.

    Checks if summary exists; if yes, returns None (skip).
    Otherwise, validates, truncates, and summarizes.

    Args:
        video_id: Video identifier
        transcript_text: Full transcript text

    Returns:
        SummaryOutput if processed, None if skipped (already summarized)

    Raises:
        Exceptions propagated from summarize_transcript()
    """
    if storage.has_summary(video_id):
        _log_operation(
            "transcript_skipped", "success", video_id=video_id, reason="already_summarized"
        )
        return None

    summary_output = summarize_transcript(transcript_text, video_id)

    summary_dict = summary_output.model_dump(mode="json")

    # Transform claims to fact-checker format for Module 3 compatibility
    if "claims" in summary_dict:
        transformed_claims = _transform_claims_for_factcheck(summary_output.claims, video_id)
        summary_dict["claims"] = transformed_claims

    storage.save_summary(video_id, summary_dict)

    return summary_output
