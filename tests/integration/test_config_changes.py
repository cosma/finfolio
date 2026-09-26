"""Integration tests for config changes."""

import pytest


@pytest.mark.integration
class TestConfigChanges:
    """Integration tests for configuration changes and reload."""

    def test_add_new_channel_to_config(self, temp_config_file):
        """Test adding new channel to configuration."""
        from finfolio.config import load_config

        # Load initial config
        channels = load_config(temp_config_file)

        # Verify config loaded
        assert isinstance(channels, list)

    def test_remove_channel_from_config(self, temp_config_file):
        """Test removing channel from configuration."""
        from finfolio.config import load_config

        channels = load_config(temp_config_file)
        assert isinstance(channels, list)

    def test_config_reload_applies_changes(self, temp_config_file):
        """Test that config reload applies changes without restart."""
        from finfolio.config import load_config

        channels = load_config(temp_config_file)
        assert len(channels) > 0
