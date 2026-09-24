"""Configuration loading for finfolio."""
import json
import logging
import os
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml
from google.auth.service_account import Credentials
from google.oauth2 import service_account

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


def load_credentials() -> Credentials:
    """Load service account credentials from GOOGLE_APPLICATION_CREDENTIALS env var.

    Returns:
        Service account credentials for YouTube Data API v3

    Raises:
        ValueError: If GOOGLE_APPLICATION_CREDENTIALS is not set or invalid
    """
    creds_path = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")

    if not creds_path:
        _log_config("load_credentials", "failed", error="GOOGLE_APPLICATION_CREDENTIALS_NOT_SET")
        raise ValueError(
            "GOOGLE_APPLICATION_CREDENTIALS environment variable not set. "
            "See docs/SERVICE_ACCOUNT_SETUP.md for setup instructions."
        )

    if not Path(creds_path).exists():
        _log_config("load_credentials", "failed", error="CREDENTIALS_FILE_NOT_FOUND", path=creds_path)
        raise ValueError(f"Credentials file not found at {creds_path}")

    try:
        credentials = service_account.Credentials.from_service_account_file(
            creds_path,
            scopes=["https://www.googleapis.com/auth/youtube.readonly"]
        )
        _log_config("load_credentials", "success", source="service_account_file")
        return credentials
    except (ValueError, KeyError) as e:
        _log_config("load_credentials", "failed", error=f"INVALID_CREDENTIALS: {str(e)}")
        raise ValueError(f"Invalid service account credentials file at {creds_path}: {e}") from e


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
