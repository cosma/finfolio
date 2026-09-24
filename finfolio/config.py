"""Configuration loading for finfolio."""
import json
import logging
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

import yaml

logger = logging.getLogger(__name__)


def _log_config(event: str, status: str, **kwargs: Any) -> None:
    """Log configuration event as JSON."""
    log_entry = {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "event": event,
        "status": status,
        **kwargs
    }
    print(json.dumps(log_entry, default=str))
    sys.stdout.flush()


def load_api_key() -> str:
    """Load YouTube API key from environment or .env file.

    Returns:
        YouTube API key

    Raises:
        ValueError: If API key not found in environment or .env file
    """
    # Try environment variable first
    api_key = os.environ.get("YOUTUBE_API_KEY")
    if api_key:
        _log_config("load_api_key", "success", source="environment")
        return api_key

    # Try .env file
    if Path(".env").exists():
        from dotenv import load_dotenv
        load_dotenv()
        api_key = os.environ.get("YOUTUBE_API_KEY")
        if api_key:
            _log_config("load_api_key", "success", source=".env_file")
            return api_key

    _log_config("load_api_key", "failed", error="API_KEY_NOT_FOUND")
    raise ValueError("YOUTUBE_API_KEY not found in environment or .env file")


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
