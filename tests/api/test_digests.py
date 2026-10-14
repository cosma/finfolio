"""User Story 1: browse monthly digests (spec US1 acceptance scenarios 1-4)."""


def test_list_returns_all_months_newest_first(write_digest, make_client):
    write_digest("2026-07", report_count=1)
    write_digest("2026-09", report_count=3)
    write_digest("2026-08", report_count=2)
    client = make_client()

    items = client.get("/digests").json()["items"]

    assert [d["month"] for d in items] == ["2026-09", "2026-08", "2026-07"]
    assert items[0]["report_count"] == 3
    assert set(items[0]) == {"month", "generated_at", "report_count", "verdict_breakdown"}


def test_single_digest_returns_full_content(write_digest, make_client):
    write_digest("2026-08", report_count=2)
    client = make_client()

    body = client.get("/digests/2026/8").json()

    assert body["month"] == "2026-08"
    assert body["per_channel_breakdown"][0]["channel_name"] == "Channel A"
    assert body["monetization_summary"][0]["disclosure"] == "Promotes a course"
    assert "disclaimer" in body


def test_missing_month_is_404_not_500(write_digest, make_client):
    write_digest("2026-08")
    client = make_client()

    response = client.get("/digests/2026/7")

    assert response.status_code == 404
    assert "2026-07" in response.json()["detail"]


def test_empty_storage_returns_empty_list(make_client):
    client = make_client()

    response = client.get("/digests")

    assert response.status_code == 200
    assert response.json() == {"items": []}


def test_invalid_month_and_year_are_422(make_client):
    client = make_client()

    assert client.get("/digests/2026/13").status_code == 422
    assert client.get("/digests/99/8").status_code == 422
