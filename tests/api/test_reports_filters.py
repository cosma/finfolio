"""User Story 2: filtered per-video reports (SC-003: exact match sets for every filter combination)."""

import pytest


@pytest.fixture
def archive(write_report, make_client):
    write_report(
        "aaaaaaaaaaa",
        channel_name="Channel A",
        channel_url="https://www.youtube.com/@channel-a",
        fact_checked_at="2026-09-10T12:00:00.000000Z",
        verdicts=["True"],
    )
    write_report(
        "bbbbbbbbbbb",
        channel_name="Channel B",
        channel_url="https://www.youtube.com/@channel-b",
        fact_checked_at="2026-09-01T00:00:00.000000Z",
        verdicts=["False", "Unverified"],
    )
    write_report(
        "ccccccccccc",
        channel_name="Channel A",
        channel_url="https://www.youtube.com/@channel-a",
        fact_checked_at="2026-10-05T23:59:59.000000Z",
        verdicts=["Partially supported"],
    )
    write_report(
        "ddddddddddd",
        channel_name="Channel C",
        channel_url="https://www.youtube.com/@channel-c",
        fact_checked_at="2026-08-31T23:59:59.000000Z",
        verdicts=[],
    )
    return make_client()


def ids(client, **params):
    response = client.get("/reports", params=params)
    assert response.status_code == 200, response.text
    return {item["video_id"] for item in response.json()["items"]}


def test_no_filters_returns_all_newest_first(archive):
    body = archive.get("/reports").json()

    assert body["total"] == 4
    assert [i["video_id"] for i in body["items"]] == [
        "ccccccccccc",
        "aaaaaaaaaaa",
        "bbbbbbbbbbb",
        "ddddddddddd",
    ]


def test_channel_filter_by_name_and_by_url(archive):
    assert ids(archive, channel="Channel A") == {"aaaaaaaaaaa", "ccccccccccc"}
    assert ids(archive, channel="https://www.youtube.com/@channel-b") == {"bbbbbbbbbbb"}


def test_date_range_is_inclusive_at_both_ends(archive):
    assert ids(archive, start="2026-09-01", end="2026-09-10") == {"aaaaaaaaaaa", "bbbbbbbbbbb"}


def test_open_bounds(archive):
    assert ids(archive, start="2026-10-01") == {"ccccccccccc"}
    assert ids(archive, end="2026-08-31") == {"ddddddddddd"}


def test_verdict_filter_matches_any_claim(archive):
    assert ids(archive, verdict="False") == {"bbbbbbbbbbb"}
    assert ids(archive, verdict="Partially supported") == {"ccccccccccc"}


def test_zero_claim_report_excluded_from_verdict_filter_only(archive):
    assert ids(archive, verdict="True") == {"aaaaaaaaaaa"}
    assert "ddddddddddd" in ids(archive)


def test_combined_filters_use_and(archive):
    assert ids(archive, channel="Channel A", verdict="Partially supported") == {"ccccccccccc"}
    assert ids(archive, channel="Channel B", verdict="True") == set()


def test_no_match_is_empty_not_error(archive):
    response = archive.get("/reports", params={"channel": "Nobody"})

    assert response.status_code == 200
    assert response.json()["items"] == []
    assert response.json()["total"] == 0


def test_pagination_pages_through_all_matches(archive):
    first = archive.get("/reports", params={"page_size": 3}).json()
    second = archive.get("/reports", params={"page_size": 3, "page": 2}).json()

    assert first["total"] == second["total"] == 4
    assert len(first["items"]) == 3
    assert len(second["items"]) == 1
