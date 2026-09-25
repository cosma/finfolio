"""Configuration loading for finfolio."""
import json
import logging
import os
import sys
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
        **kwargs
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
        load_dotenv(env_file)
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
