"""LangChain callback handler for cost tracking and monitoring."""

import json
import logging
from datetime import UTC, datetime
from typing import Any

logger = logging.getLogger(__name__)


class CostTrackingCallback:
    """Callback handler to track LLM costs and token usage.

    Logs structured JSON with timestamp, model, token counts, and cost.
    """

    def __init__(self):
        """Initialize cost tracker."""
        self.total_tokens_in = 0
        self.total_tokens_out = 0
        self.total_cost_usd = 0.0
        self.calls = []

    def on_llm_end(self, response: Any, **kwargs: Any) -> None:
        """Called when LLM call completes. Records the call; see record()."""
        self.record(response)

    def record(self, response: Any) -> dict[str, Any]:
        """Record one LLM call's tokens and cost, and return them.

        Reads LangChain's usage_metadata (input_tokens, output_tokens). A reply without
        usage counts as zero tokens, so every call is still logged.
        """
        try:
            usage = getattr(response, "usage_metadata", None)
            if isinstance(usage, dict):
                tokens_in = int(usage.get("input_tokens", 0))
                tokens_out = int(usage.get("output_tokens", 0))
            else:
                tokens_in = 0
                tokens_out = 0

            # Calculate cost (Haiku pricing: input $0.80/MTok, output $4.00/MTok)
            # Prices in $/1000 tokens
            cost_per_mtok_in = 0.80 / 1000
            cost_per_mtok_out = 4.00 / 1000
            call_cost = (tokens_in * cost_per_mtok_in) + (tokens_out * cost_per_mtok_out)

            # Track totals
            self.total_tokens_in += tokens_in
            self.total_tokens_out += tokens_out
            self.total_cost_usd += call_cost

            # Log call
            call_record = {
                "timestamp": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
                "tokens_in": tokens_in,
                "tokens_out": tokens_out,
                "cost_usd": round(call_cost, 6),
            }
            self.calls.append(call_record)

            # Log structured event
            log_entry = {
                "timestamp": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
                "event": "llm_call",
                "status": "success",
                "tokens_in": tokens_in,
                "tokens_out": tokens_out,
                "cost_usd": round(call_cost, 6),
            }
            logger.info(json.dumps(log_entry, default=str))
            return {
                "tokens_in": tokens_in,
                "tokens_out": tokens_out,
                "cost_usd": round(call_cost, 6),
            }

        except Exception as e:
            logger.error(f"Error tracking LLM cost: {str(e)}")
            return {"tokens_in": 0, "tokens_out": 0, "cost_usd": 0.0}

    def get_summary(self) -> dict[str, Any]:
        """Get cost tracking summary.

        Returns:
            Dict with total_tokens_in, total_tokens_out, total_cost_usd
        """
        return {
            "total_tokens_in": self.total_tokens_in,
            "total_tokens_out": self.total_tokens_out,
            "total_cost_usd": round(self.total_cost_usd, 6),
            "calls": self.calls,
        }

    def reset(self) -> None:
        """Reset tracking state."""
        self.total_tokens_in = 0
        self.total_tokens_out = 0
        self.total_cost_usd = 0.0
        self.calls = []
