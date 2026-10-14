"""Configuration management for finfolio."""

import json
import logging
import os
import sys
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv

logger = logging.getLogger(__name__)


def _log_config(event: str, status: str, **kwargs: Any) -> None:
    """Log configuration event as JSON."""
    log_entry = {
        "timestamp": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "event": event,
        "status": status,
        **kwargs,
    }
    print(json.dumps(log_entry, default=str))
    sys.stdout.flush()


def load_api_key() -> str:
    """Load YouTube Data API key from .env file or YOUTUBE_API_KEY environment variable.

    Tries in order:
    1. YOUTUBE_API_KEY environment variable
    2. .env file in current directory
    3. Raises error if not found

    Returns:
        YouTube Data API key string

    Raises:
        ValueError: If YOUTUBE_API_KEY is not found
    """
    # Try to load from .env file first
    env_file = Path(".env")
    if env_file.exists():
        load_dotenv(env_file, override=True)
        _log_config("load_api_key", "success", source=".env file")

    # Check environment variable (either from .env or system)
    api_key = os.environ.get("YOUTUBE_API_KEY")

    if not api_key:
        _log_config("load_api_key", "failed", error="YOUTUBE_API_KEY_NOT_SET")
        raise ValueError(
            "YOUTUBE_API_KEY not found. Set it in .env file or as environment variable."
        )

    _log_config("load_api_key", "success")
    return api_key


def load_config(config_path: str) -> list[dict[str, Any]]:
    """Load channel configuration from YAML file.

    Args:
        config_path: Path to channels.yaml configuration file

    Returns:
        List of channel dictionaries with channel_id and display_name

    Raises:
        FileNotFoundError: If config file doesn't exist
        ValueError: If YAML is malformed
    """
    try:
        with open(config_path) as f:
            config = yaml.safe_load(f)

        if not config or "channels" not in config:
            _log_config("load_config", "success", path=config_path, channels_count=0)
            return []

        channels = config["channels"]
        _log_config("load_config", "success", path=config_path, channels_count=len(channels))
        return channels
    except FileNotFoundError as e:
        _log_config("load_config", "failed", path=config_path, error="FILE_NOT_FOUND")
        raise FileNotFoundError(f"Config file not found: {config_path}") from e
    except yaml.YAMLError as e:
        _log_config("load_config", "failed", path=config_path, error=f"INVALID_YAML: {str(e)}")
        raise ValueError(f"Invalid YAML in {config_path}: {e}") from e


@dataclass
class Config:
    """Configuration for fact-checking pipeline.

    Reads from environment variables with sensible defaults.
    Model selection is configuration-only (never hardcoded).
    """

    # Storage location
    storage_dir: str = ""

    # LLM configuration
    llm_model: str = ""

    # API keys (required for runtime, can be None for testing)
    anthropic_api_key: str | None = None
    tavily_api_key: str | None = None

    # Search configuration
    search_timeout_seconds: float = 0.0
    # Minimum confidence for accepting a free-source (DuckDuckGo) verdict. Negative = read from env.
    search_min_confidence: float = -1.0

    # Logging configuration
    log_level: str = ""

    def __post_init__(self) -> None:
        """Load environment variables after dataclass initialization."""
        # Only set from env if not already provided
        if not self.storage_dir:
            self.storage_dir = os.getenv("FINFOLIO_STORAGE_DIR", "storage")
        if not self.llm_model:
            self.llm_model = os.getenv("FINFOLIO_LLM_MODEL", "claude-haiku-4-5-20251001")
        if not self.anthropic_api_key:
            self.anthropic_api_key = os.getenv("ANTHROPIC_API_KEY")
        if not self.tavily_api_key:
            self.tavily_api_key = os.getenv("TAVILY_API_KEY")
        if self.search_min_confidence < 0:
            raw = os.getenv("FINFOLIO_SEARCH_MIN_CONFIDENCE", "0.8")
            try:
                self.search_min_confidence = float(raw)
            except ValueError as e:
                raise ValueError(
                    f"FINFOLIO_SEARCH_MIN_CONFIDENCE must be a number between 0 and 1, got {raw!r}"
                ) from e
        if self.search_timeout_seconds == 0.0:
            self.search_timeout_seconds = float(os.getenv("FINFOLIO_SEARCH_TIMEOUT", "10"))
        if not self.log_level:
            self.log_level = os.getenv("FINFOLIO_LOG_LEVEL", "INFO")

    def validate(self) -> None:
        """Validate that required configuration is set.

        Raises ValueError if critical configuration is missing.
        """
        if not self.anthropic_api_key:
            raise ValueError("ANTHROPIC_API_KEY environment variable is not set")
        if not self.tavily_api_key:
            raise ValueError("TAVILY_API_KEY environment variable is not set")
        if not 0.0 <= self.search_min_confidence <= 1.0:
            raise ValueError(
                f"FINFOLIO_SEARCH_MIN_CONFIDENCE must be between 0 and 1, got {self.search_min_confidence}"
            )

    @property
    def storage_path(self) -> Path:
        """Get storage directory as Path object."""
        return Path(self.storage_dir)
