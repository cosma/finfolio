"""Monthly Digest Module (Module 4) - Aggregation logic for fact-checking reports."""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field, field_validator

from finfolio.models import DISCLAIMER

logger = logging.getLogger(__name__)


class VerdictBreakdown(BaseModel):
    """Counts of each verdict type."""

    true: int = Field(ge=0, alias="True")
    partially_supported: int = Field(ge=0, alias="Partially supported")
    unverified: int = Field(ge=0, alias="Unverified")
    false: int = Field(ge=0, alias="False")

    model_config = {"populate_by_name": True}


class ChannelDigest(BaseModel):
    """Aggregated verdict statistics for a single channel."""

    channel_name: str = Field(min_length=1, max_length=100)
    channel_url: str = Field(pattern="^https://")
    video_count: int = Field(ge=1)
    verdict_breakdown: VerdictBreakdown


class MonetizationEntry(BaseModel):
    """One unique monetization disclosure in the month."""

    channel_name: str = Field(min_length=1)
    disclosure: str = Field(min_length=1)


class Digest(BaseModel):
    """Aggregated monthly fact-checking statistics."""

    month: str = Field(pattern=r"^\d{4}-\d{2}$")
    generated_at: str
    report_count: int = Field(ge=0)
    verdict_breakdown: VerdictBreakdown
    per_channel_breakdown: list[ChannelDigest] = Field(default_factory=list)
    monetization_summary: list[MonetizationEntry] = Field(default_factory=list)

    @field_validator("month")
    @classmethod
    def validate_month(cls, v):
        year, month = v.split("-")
        if not (1 <= int(month) <= 12):
            raise ValueError(f"Month must be 01-12, got {month}")
        return v


class MonthlyDigest:
    """Aggregates fact-checking reports from a given month."""

    def __init__(self, year: int, month: int):
        """Initialize digest for a specific month.

        Args:
            year: 4-digit year (e.g., 2026)
            month: Month number 1-12

        Raises:
            ValueError: If month is not 1-12
        """
        validate_month(year, month)
        self.year = year
        self.month = month
        self.month_str = f"{year:04d}-{month:02d}"
        self.reports: list[dict[str, Any]] = []
        self.overall_verdicts: dict[str, int] = {
            "True": 0,
            "Partially supported": 0,
            "Unverified": 0,
            "False": 0,
        }
        self.channel_stats: dict[str, dict[str, Any]] = {}
        self.monetization_entries: dict[tuple, str] = {}

    def aggregate(self, report_paths: list[Path]) -> None:
        """Aggregate reports for this month.

        Args:
            report_paths: List of report file paths to aggregate
        """
        for report_path in report_paths:
            report = load_report(report_path)
            if report is None:
                continue

            self.reports.append(report)

            # Aggregate verdicts
            verdicts = report.get("verdict_breakdown", {})
            for verdict_type, count in verdicts.items():
                if verdict_type in self.overall_verdicts:
                    self.overall_verdicts[verdict_type] += count

            # Aggregate by channel
            channel_name = report.get("summary", {}).get("metadata", {}).get("channel_name")
            channel_url = report.get("summary", {}).get("metadata", {}).get("channel_url")

            if channel_name and channel_url:
                if channel_name not in self.channel_stats:
                    self.channel_stats[channel_name] = {
                        "channel_url": channel_url,
                        "videos": 0,
                        "verdicts": {
                            "True": 0,
                            "Partially supported": 0,
                            "Unverified": 0,
                            "False": 0,
                        },
                    }

                self.channel_stats[channel_name]["videos"] += 1
                for verdict_type, count in verdicts.items():
                    if verdict_type in self.channel_stats[channel_name]["verdicts"]:
                        self.channel_stats[channel_name]["verdicts"][verdict_type] += count

            # Collect monetization disclosures
            disclosure = report.get("monetization_disclosure")
            if disclosure and channel_name:
                key = (channel_name, disclosure)
                self.monetization_entries[key] = disclosure

    def to_dict(self) -> dict[str, Any]:
        """Serialize digest to dictionary matching schema."""
        per_channel_list = []
        for channel_name in sorted(self.channel_stats.keys()):
            stats = self.channel_stats[channel_name]
            per_channel_list.append(
                {
                    "channel_name": channel_name,
                    "channel_url": stats["channel_url"],
                    "video_count": stats["videos"],
                    "verdict_breakdown": stats["verdicts"],
                }
            )

        monetization_list = []
        for channel_name, disclosure in sorted(self.monetization_entries.keys()):
            monetization_list.append(
                {
                    "channel_name": channel_name,
                    "disclosure": disclosure,
                }
            )

        return {
            "month": self.month_str,
            "generated_at": datetime.utcnow().isoformat() + "Z",
            "report_count": len(self.reports),
            "verdict_breakdown": self.overall_verdicts,
            "per_channel_breakdown": per_channel_list,
            "monetization_summary": monetization_list,
            "disclaimer": DISCLAIMER,
        }


def validate_month(year: int, month: int) -> None:
    """Validate year and month values.

    Args:
        year: 4-digit year
        month: Month number (1-12)

    Raises:
        ValueError: If month is not 1-12 or year is invalid
    """
    if not (1 <= month <= 12):
        raise ValueError(f"Month must be 1-12, got {month}")
    if not (1900 <= year <= 2100):
        raise ValueError(f"Year must be 1900-2100, got {year}")


def load_report(report_path: Path) -> dict[str, Any] | None:
    """Safely load a report JSON file.

    Args:
        report_path: Path to report JSON file

    Returns:
        Parsed report dict, or None if file is malformed
    """
    try:
        with open(report_path) as f:
            report: dict[str, Any] = json.load(f)
            return report
    except (OSError, json.JSONDecodeError) as e:
        logger.error(f"Failed to load report {report_path.name}: {e}")
        return None
