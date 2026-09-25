"""Unit tests for config module."""
import os
from unittest.mock import patch

import pytest

from finfolio import config


@pytest.mark.unit
class TestLoadApiKey:
    """Test YouTube API key loading."""

    def test_load_api_key_from_environment(self):
        """Test loading API key from YOUTUBE_API_KEY environment variable."""
        with patch.dict(os.environ, {"YOUTUBE_API_KEY": "test-key-123"}):
            key = config.load_api_key()
            assert key == "test-key-123"

    def test_load_api_key_raises_when_missing(self):
        """Test error raised when API key not set."""
        with patch.dict(os.environ, {}, clear=True):
            # Mock pathlib.Path.exists to return False so .env is not found
            with patch("finfolio.config.Path.exists", return_value=False):
                with pytest.raises(ValueError, match="YOUTUBE_API_KEY"):
                    config.load_api_key()


@pytest.mark.unit
class TestLoadConfig:
    """Test channels.yaml configuration loading."""

    def test_load_config_valid_yaml(self, tmp_path):
        """Test loading valid channels.yaml configuration."""
        config_file = tmp_path / "channels.yaml"
        config_file.write_text("""
channels:
  - channel_id: "UC7_ZLN2t-U-tZ7CgzQ0OoXw"
    display_name: "Graham Stephan"
  - channel_id: "UC_x5XG1OV2P6uZZ5FSM9Ttw"
    display_name: "Two Cents"
""")

        channels = config.load_config(str(config_file))
        assert len(channels) == 2
        assert channels[0]["channel_id"] == "UC7_ZLN2t-U-tZ7CgzQ0OoXw"

    def test_load_config_missing_file_raises_error(self, tmp_path):
        """Test error when channels.yaml file doesn't exist."""
        config_file = tmp_path / "nonexistent.yaml"

        with pytest.raises(FileNotFoundError):
            config.load_config(str(config_file))

    def test_load_config_malformed_yaml(self, tmp_path):
        """Test error when YAML syntax is invalid."""
        config_file = tmp_path / "channels.yaml"
        config_file.write_text("channels:\n  - channel_id: \"UC7_ZLN2t-U-tZ7CgzQ0OoXw\n    display_name: Test\n")

        with pytest.raises(ValueError, match="Invalid YAML"):
            config.load_config(str(config_file))
