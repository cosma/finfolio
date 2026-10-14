"""One-time migration of stored data to the canonical verdict name (FR-016) and digest disclaimer (FR-015).

Rewrites in place:
- storage/reports/videos/*.json: every "Partially supported/overstated" string value and
  dict key becomes "Partially supported".
- storage/reports/monthly/*.json: adds the shared disclaimer when missing.

Dry-run by default. Pass --apply to write files. Each file is written to a temp file
and then replaced, so an interrupted run never leaves a half-written file.

Usage:
    python scripts/migrate_verdict_names.py            # dry run, lists what would change
    python scripts/migrate_verdict_names.py --apply    # write the changes
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from finfolio.models import DISCLAIMER

LEGACY_VERDICT = "Partially supported/overstated"
CANONICAL_VERDICT = "Partially supported"
STORAGE_DIR = Path("storage")
REPORTS_DIR = STORAGE_DIR / "reports" / "videos"
DIGESTS_DIR = STORAGE_DIR / "reports" / "monthly"


def rename_verdicts(node: Any) -> tuple[Any, int]:
    """Return a copy of node with legacy verdict strings and keys renamed, plus the change count."""
    if isinstance(node, dict):
        changes = 0
        out: dict[str, Any] = {}
        for key, value in node.items():
            new_key = CANONICAL_VERDICT if key == LEGACY_VERDICT else key
            if new_key != key:
                changes += 1
            new_value, child_changes = rename_verdicts(value)
            out[new_key] = new_value
            changes += child_changes
        return out, changes
    if isinstance(node, list):
        changes = 0
        out_list = []
        for item in node:
            new_item, child_changes = rename_verdicts(item)
            out_list.append(new_item)
            changes += child_changes
        return out_list, changes
    if node == LEGACY_VERDICT:
        return CANONICAL_VERDICT, 1
    return node, 0


def migrate_report(path: Path) -> int:
    """Return the number of legacy verdict occurrences in a report file."""
    data = json.loads(path.read_text(encoding="utf-8"))
    new_data, changes = rename_verdicts(data)
    if changes:
        write_json(path, new_data)
    return changes


def backfill_digest(path: Path) -> int:
    """Return 1 if the digest was missing the disclaimer and is updated, else 0."""
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("disclaimer") == DISCLAIMER:
        return 0
    data["disclaimer"] = DISCLAIMER
    write_json(path, data)
    return 1


def write_json(path: Path, data: Any) -> None:
    """Write JSON atomically: temp file, then replace."""
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    tmp.replace(path)


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--apply", action="store_true", help="write changes (default: dry run)")
    args = parser.parse_args()

    mode = "APPLY" if args.apply else "DRY RUN"
    print(f"[{mode}] verdict-name and disclaimer migration")

    report_files = sorted(REPORTS_DIR.glob("*.json")) if REPORTS_DIR.exists() else []
    digest_files = sorted(DIGESTS_DIR.glob("*.json")) if DIGESTS_DIR.exists() else []

    reports_changed = 0
    verdict_occurrences = 0
    for path in report_files:
        found = _count_only(path, rename_verdicts) if not args.apply else migrate_report(path)
        if found:
            reports_changed += 1
            verdict_occurrences += found

    digests_changed = 0
    for path in digest_files:
        if not args.apply:
            data = json.loads(path.read_text(encoding="utf-8"))
            if data.get("disclaimer") != DISCLAIMER:
                digests_changed += 1
        else:
            digests_changed += backfill_digest(path)

    print(
        f"reports scanned: {len(report_files)}, to change: {reports_changed}, verdict occurrences: {verdict_occurrences}"
    )
    print(f"digests scanned: {len(digest_files)}, to change: {digests_changed}")
    if not args.apply:
        print("No files written. Re-run with --apply to make these changes.")
    return 0


def _count_only(path: Path, transform: Any) -> int:
    """Count legacy occurrences without writing (dry run)."""
    data = json.loads(path.read_text(encoding="utf-8"))
    _, changes = transform(data)
    return changes


if __name__ == "__main__":
    sys.exit(main())
