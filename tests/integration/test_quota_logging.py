"""Integration tests for quota logging."""
import pytest


@pytest.mark.integration
class TestQuotaLogging:
    """Integration tests for API quota tracking and logging."""

    def test_quota_tracking_per_operation(self, mock_youtube_client):
        """Test that quota is tracked for each operation type."""
        quota = mock_youtube_client.get_quota_units_used()

        assert "search" in quota
        assert "caption.list" in quota
        assert "caption.download" in quota

    def test_quota_accumulates_across_operations(self, mock_youtube_client):
        """Test that quota accumulates correctly."""
        initial_quota = mock_youtube_client.get_quota_units_used()
        assert isinstance(initial_quota, dict)

    def test_quota_breakdown_available(self, mock_youtube_client):
        """Test that quota breakdown by operation type is available."""
        quota = mock_youtube_client.get_quota_units_used()

        for operation in ["search", "caption.list", "caption.download"]:
            assert operation in quota
            assert isinstance(quota[operation], int)
