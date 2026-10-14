"""User Story 3: one per-video report by video ID (FR-008, FR-013)."""


def test_known_id_returns_full_report(write_report, make_client):
    write_report("aaaaaaaaaaa", verdicts=["True", "False"])
    client = make_client()

    body = client.get("/reports/aaaaaaaaaaa").json()

    assert body["video_id"] == "aaaaaaaaaaa"
    assert len(body["verdicts"]) == 2
    assert "summary" in body and "cost" in body and "disclaimer" in body


def test_unknown_id_is_404_naming_the_id(make_client):
    client = make_client()

    response = client.get("/reports/zzzzzzzzzzz")

    assert response.status_code == 404
    assert "zzzzzzzzzzz" in response.json()["detail"]


def test_malformed_id_is_422(make_client):
    client = make_client()

    assert client.get("/reports/a.b").status_code == 422
    assert client.get("/reports/" + "a" * 65).status_code == 422


def test_unreadable_file_is_500_naming_the_file(api_storage, make_client):
    (api_storage / "reports" / "videos" / "cccccccccc1.json").write_text(
        "{broken", encoding="utf-8"
    )
    client = make_client()

    response = client.get("/reports/cccccccccc1")

    assert response.status_code == 500
    assert "cccccccccc1" in response.json()["detail"]
