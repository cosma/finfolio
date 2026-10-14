"""Index build: valid files are indexed, malformed or non-canonical files are skipped (FR-014, SC-006)."""


def test_build_indexes_valid_and_skips_bad_files(api_storage, write_report, make_client):
    write_report("aaaaaaaaaaa")
    write_report("bbbbbbbbbbb", verdicts=["Partially supported/overstated"])
    (api_storage / "reports" / "videos" / "ccccccccccc.json").write_text(
        "{not json", encoding="utf-8"
    )

    client = make_client()
    result = client.post("/index/refresh").json()

    assert result["indexed"]["reports"] == 1
    assert {s["item"] for s in result["skipped"]} == {
        "reports/bbbbbbbbbbb.json",
        "reports/ccccccccccc.json",
    }


def test_legacy_name_in_breakdown_alone_is_skipped(api_storage, write_report, make_client):
    """A report whose claims are canonical but whose breakdown still has the legacy key is not indexed."""
    write_report("ddddddddddd", verdicts=["True"])
    path = api_storage / "reports" / "videos" / "ddddddddddd.json"
    path.write_text(
        path.read_text(encoding="utf-8").replace(
            '"Partially supported"', '"Partially supported/overstated"'
        ),
        encoding="utf-8",
    )
    client = make_client()

    result = client.post("/index/refresh").json()

    assert result["indexed"]["reports"] == 0
    assert "verdict_breakdown" in result["skipped"][0]["reason"]


def test_skipped_reasons_are_named(api_storage, write_report, make_client):
    write_report("bbbbbbbbbbb", verdicts=["Partially supported/overstated"])
    client = make_client()
    skipped = client.post("/index/refresh").json()["skipped"]

    assert "Partially supported/overstated" in skipped[0]["reason"]


def test_malformed_digest_is_skipped_not_fatal(api_storage, write_digest, make_client):
    write_digest("2026-08")
    (api_storage / "reports" / "monthly" / "2026-07.json").write_text("nope", encoding="utf-8")
    client = make_client()

    listed = client.get("/digests").json()["items"]
    assert [d["month"] for d in listed] == ["2026-08"]
