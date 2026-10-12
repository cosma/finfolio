#!/usr/bin/env python3
"""Migrate transcripts from .txt to .json format with publication_timestamp field."""

import json
import sys
from pathlib import Path

TRANSCRIPTS_DIR = Path("storage/transcripts")


def migrate_transcripts() -> None:
    """Convert all .txt transcripts to .json format with publication_timestamp: null."""
    if not TRANSCRIPTS_DIR.exists():
        print(f"Error: {TRANSCRIPTS_DIR} does not exist")
        sys.exit(1)

    txt_files = list(TRANSCRIPTS_DIR.glob("*.txt"))

    if not txt_files:
        print("No .txt transcript files found")
        return

    print(f"Found {len(txt_files)} .txt files to migrate")

    migrated = 0
    errors = 0

    for txt_file in txt_files:
        try:
            video_id = txt_file.stem
            json_file = TRANSCRIPTS_DIR / f"{video_id}.json"

            # Skip if JSON already exists
            if json_file.exists():
                print(f"  ✓ {video_id} - already migrated (JSON exists)")
                continue

            # Read transcript content
            content = txt_file.read_text(encoding="utf-8")

            # Create JSON structure with null publication_timestamp
            transcript_data = {
                "publication_timestamp": None,
                "content": content
            }

            # Write as JSON
            json_file.write_text(json.dumps(transcript_data, indent=2), encoding="utf-8")
            print(f"  ✓ {video_id} - migrated")
            migrated += 1

        except Exception as e:
            print(f"  ✗ {video_id} - error: {e}")
            errors += 1

    print(f"\nMigration complete: {migrated} migrated, {errors} errors")

    if errors == 0:
        print("\nNote: Original .txt files remain. To clean up, run:")
        print("  find storage/transcripts -name '*.txt' -delete")


if __name__ == "__main__":
    migrate_transcripts()
