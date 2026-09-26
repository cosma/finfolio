"""Configuration management for fact-checking module."""

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass
class Config:
    """Configuration for fact-checking pipeline.

    Reads from environment variables with sensible defaults.
    Model selection is configuration-only (never hardcoded).
    """

    # Storage location
    storage_dir: str = os.getenv("FINFOLIO_STORAGE_DIR", "storage")

    # LLM configuration
    llm_model: str = os.getenv("FINFOLIO_LLM_MODEL", "claude-haiku-4-5-20251001")

    # API keys (required for runtime, can be None for testing)
    anthropic_api_key: str | None = os.getenv("ANTHROPIC_API_KEY")
    tavily_api_key: str | None = os.getenv("TAVILY_API_KEY")

    # Search configuration
    search_timeout_seconds: float = float(os.getenv("FINFOLIO_SEARCH_TIMEOUT", "10"))

    # Logging configuration
    log_level: str = os.getenv("FINFOLIO_LOG_LEVEL", "INFO")

    def validate(self) -> None:
        """Validate that required configuration is set.

        Raises ValueError if critical configuration is missing.
        """
        if not self.anthropic_api_key:
            raise ValueError("ANTHROPIC_API_KEY environment variable is not set")
        if not self.tavily_api_key:
            raise ValueError("TAVILY_API_KEY environment variable is not set")

    @property
    def storage_path(self) -> Path:
        """Get storage directory as Path object."""
        return Path(self.storage_dir)
