"""User Story 2: invalid input is rejected with a message that names the input (FR-013, SC-007)."""


def test_unknown_verdict_is_422_naming_the_value(write_report, make_client):
    write_report("aaaaaaaaaaa")
    client = make_client()

    response = client.get("/reports", params={"verdict": "Partly true"})

    assert response.status_code == 422
    assert "Partly true" in response.text


def test_start_after_end_is_422_naming_both_dates(write_report, make_client):
    write_report("aaaaaaaaaaa")
    client = make_client()

    response = client.get("/reports", params={"start": "2026-10-01", "end": "2026-09-01"})

    assert response.status_code == 422
    assert "2026-10-01" in response.json()["detail"]
    assert "2026-09-01" in response.json()["detail"]


def test_invalid_date_format_is_422(write_report, make_client):
    write_report("aaaaaaaaaaa")
    client = make_client()

    assert client.get("/reports", params={"start": "2026-13-01"}).status_code == 422


def test_page_past_last_returns_empty_items_with_real_total(write_report, make_client):
    write_report("aaaaaaaaaaa")
    write_report("bbbbbbbbbbb")
    client = make_client()

    body = client.get("/reports", params={"page": 5}).json()

    assert body["items"] == []
    assert body["total"] == 2


def test_page_size_bounds(write_report, make_client):
    write_report("aaaaaaaaaaa")
    client = make_client()

    assert client.get("/reports", params={"page_size": 201}).status_code == 422
    assert client.get("/reports", params={"page": 0}).status_code == 422
    assert client.get("/reports", params={"page_size": 200}).status_code == 200
