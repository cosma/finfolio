"""Stored disclaimer, transcript source, summary, and cost are returned unchanged (FR-015)."""

import json


def test_report_fields_match_stored_file(api_storage, write_report, make_client):
    write_report("aaaaaaaaaaa")
    client = make_client()

    stored = json.loads((api_storage / "reports" / "videos" / "aaaaaaaaaaa.json").read_text())
    body = client.get("/reports/aaaaaaaaaaa").json()

    for field in ("disclaimer", "transcript_source", "summary", "cost"):
        assert body[field] == stored[field], field


def test_digest_fields_match_stored_file(api_storage, write_digest, make_client):
    write_digest("2026-08")
    client = make_client()

    stored = json.loads((api_storage / "reports" / "monthly" / "2026-08.json").read_text())
    body = client.get("/digests/2026/8").json()

    for field in ("disclaimer", "monetization_summary", "per_channel_breakdown"):
        assert body[field] == stored[field], field
