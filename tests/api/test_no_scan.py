"""FR-009: list requests are served from the index, not by scanning stored files per request."""

from finfolio import storage


def _forbidden(*_args, **_kwargs):
    raise AssertionError("per-request scan of stored files")


def test_list_requests_do_not_scan_storage(write_report, write_digest, make_client, monkeypatch):
    write_report("aaaaaaaaaaa", verdicts=["False"])
    write_digest("2026-09")
    client = make_client()

    monkeypatch.setattr(storage, "list_report_ids", _forbidden)
    monkeypatch.setattr(storage, "list_digest_months", _forbidden)
    monkeypatch.setattr(storage, "load_report", _forbidden)

    assert client.get("/reports", params={"verdict": "False"}).status_code == 200
    assert client.get("/digests").status_code == 200


def test_single_item_read_touches_only_one_file(write_report, make_client, monkeypatch):
    write_report("aaaaaaaaaaa")
    client = make_client()
    calls: list[str] = []
    real_load = storage.load_report

    def counting(video_id):
        calls.append(video_id)
        return real_load(video_id)

    monkeypatch.setattr(storage, "load_report", counting)
    client.get("/reports/aaaaaaaaaaa")

    assert calls == ["aaaaaaaaaaa"]
