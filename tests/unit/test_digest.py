"""Unit tests for monthly digest output (FR-015: disclaimer carried by digests)."""

from finfolio.digest import MonthlyDigest
from finfolio.models import DISCLAIMER


def test_digest_dict_carries_disclaimer():
    """A generated digest includes the shared disclaimer text."""
    digest = MonthlyDigest(2026, 9)
    data = digest.to_dict()

    assert data["disclaimer"] == DISCLAIMER


def test_digest_disclaimer_is_the_report_disclaimer():
    """Digest and report disclaimers come from one constant, so they cannot drift apart."""
    assert DISCLAIMER == "FinFolio reports facts and their accuracy. This is not financial advice."
