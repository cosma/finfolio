"""Configuration loading for finfolio."""
import json
import os
from pathlib import Path
from typing import Any

import yaml


def load_api_key() -> str:
    """Load YouTube API key from environment or .env file."""
    # Try environment variable first
    api_key = os.environ.get("YOUTUBE_API_KEY")
    if api_key:
        return api_key
    
    # Try .env file
    if Path(".env").exists():
        from dotenv import load_dotenv
        load_dotenv()
        api_key = os.environ.get("YOUTUBE_API_KEY")
        if api_key:
            return api_key
    
    raise ValueError("YOUTUBE_API_KEY not found in environment or .env file")


def load_config(config_path: str) -> list[dict[str, Any]]:
    """Load channel configuration from YAML file."""
    try:
        with open(config_path) as f:
            config = yaml.safe_load(f)
        if not config or "channels" not in config:
            return []
        return config["channels"]
    except yaml.YAMLError as e:
        raise ValueError(f"Invalid YAML in {config_path}: {e}")
    except FileNotFoundError:
        raise FileNotFoundError(f"Config file not found: {config_path}")
