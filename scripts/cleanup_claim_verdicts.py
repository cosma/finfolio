"""One-time cleanup of stored verdicts before the search fallback runs.

- Removes "Unverified" verdicts. They came from empty search results after the Tavily
  credits ran out, so they are not real findings. Removed claims are checked again by
  `finfolio factcheck`, which searches DuckDuckGo first and then Tavily.
- Marks every remaining verdict verified_by "tavily": Tavily was the only search source
  when these were produced.
- Recomputes verdict_count and verdict_breakdown in each report.

Dry-run by default. Pass --apply to write. Each file is written via a temp file and replace.
Digests are not changed; regenerate them with `finfolio report` afterwards.

Usage:
    python scripts/cleanup_claim_verdicts.py           # dry run
    python scripts/cleanup_claim_verdicts.py --apply   # write the changes
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Any

CANONICAL = ("True", "Partially supported", "Unverified", "False")
REPORTS_DIR = Path("storage") / "reports" / "videos"


def clean_report(report: dict[str, Any]) -> tuple[dict[str, Any], int, int]:
    """Return the cleaned report, the number of verdicts removed, and the number marked tavily."""
    kept = []
    removed = 0
    marked = 0
    for verdict in report.get("verdicts", []):
        # Only Unverified verdicts with no verified_by are empty-search leftovers. Those with
        # verified_by were recorded as final (FR-013) and are kept.
        if verdict.get("verdict") == "Unverified" and not verdict.get("verified_by"):
            removed += 1
            continue
        if not verdict.get("verified_by"):
            verdict = {**verdict, "verified_by": "tavily"}
            marked += 1
        kept.append(verdict)

    breakdown = dict.fromkeys(CANONICAL, 0)
    for verdict in kept:
        breakdown[verdict["verdict"]] += 1

    # The report-level search_provider field is removed (FR-014) from stored reports too.
    rest = {k: v for k, v in report.items() if k != "search_provider"}
    cleaned = {
        **rest,
        "verdicts": kept,
        "verdict_count": len(kept),
        "verdict_breakdown": breakdown,
    }
    return cleaned, removed, marked


def write_json(path: Path, data: dict[str, Any]) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    tmp.replace(path)


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--apply", action="store_true", help="write changes (default: dry run)")
    args = parser.parse_args()

    files = sorted(REPORTS_DIR.glob("*.json")) if REPORTS_DIR.exists() else []
    total_removed = total_marked = changed_files = 0
    for path in files:
        report = json.loads(path.read_text(encoding="utf-8"))
        cleaned, removed, marked = clean_report(report)
        dropped_provider = "search_provider" in report
        if removed or marked or dropped_provider:
            changed_files += 1
            total_removed += removed
            total_marked += marked
            if args.apply:
                write_json(path, cleaned)

    mode = "APPLY" if args.apply else "DRY RUN"
    print(f"[{mode}] reports scanned: {len(files)}, changed: {changed_files}")
    print(
        f"unverified verdicts removed: {total_removed}, verdicts marked verified_by=tavily: {total_marked}"
    )
    if not args.apply:
        print("No files written. Re-run with --apply to make these changes.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
