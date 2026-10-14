"""Startup build, explicit refresh, and swap semantics (FR-010, SC-005)."""

import pytest

from finfolio import storage
from finfolio.api import index


def test_docs_are_served(make_client):
    client = make_client()
    assert client.get("/docs").status_code == 200
    assert client.get("/openapi.json").status_code == 200


def test_added_file_visible_only_after_refresh(write_report, make_client):
    write_report("aaaaaaaaaaa")
    client = make_client()
    write_report("bbbbbbbbbbb")

    assert client.get("/reports").json()["total"] == 1
    assert client.post("/index/refresh").json()["indexed"]["reports"] == 2
    assert client.get("/reports").json()["total"] == 2


def test_edited_file_reflected_after_refresh(write_report, make_client):
    write_report("aaaaaaaaaaa", verdicts=["True"])
    client = make_client()
    assert client.get("/reports", params={"verdict": "False"}).json()["total"] == 0

    write_report("aaaaaaaaaaa", verdicts=["False"])
    client.post("/index/refresh")

    assert client.get("/reports", params={"verdict": "False"}).json()["total"] == 1


def test_requests_during_refresh_see_previous_index(write_report, make_client, monkeypatch):
    write_report("aaaaaaaaaaa")
    make_client()
    write_report("bbbbbbbbbbb")
    seen_during_build: dict[str, int] = {}
    real_load = storage.load_report

    def spy(video_id):
        if "total" not in seen_during_build:
            with index.open_index() as conn:
                _, seen_during_build["total"] = index.query_reports(
                    conn, channel=None, start=None, end=None, verdict=None, page=1, page_size=50
                )
        return real_load(video_id)

    monkeypatch.setattr(storage, "load_report", spy)
    index.build_index()

    assert seen_during_build["total"] == 1


def test_failed_refresh_keeps_previous_index(api_storage, write_report, make_client, monkeypatch):
    write_report("aaaaaaaaaaa")
    client = make_client()
    write_report("bbbbbbbbbbb")
    real_load = storage.load_report

    def boom(video_id):
        raise RuntimeError("storage went away")

    monkeypatch.setattr(storage, "load_report", boom)
    with pytest.raises(RuntimeError):
        client.post("/index/refresh")
    monkeypatch.setattr(storage, "load_report", real_load)

    assert client.get("/reports").json()["total"] == 1
    assert not (api_storage / ".finfolio-api-index.sqlite.tmp").exists()


def test_removed_file_disappears_after_refresh(api_storage, write_report, make_client):
    """A report deleted from storage stays listed until a refresh, then is gone (spec Edge Cases)."""
    write_report("aaaaaaaaaaa")
    write_report("bbbbbbbbbbb")
    client = make_client()
    (api_storage / "reports" / "videos" / "bbbbbbbbbbb.json").unlink()

    assert client.get("/reports").json()["total"] == 2
    assert client.post("/index/refresh").json()["indexed"]["reports"] == 1
    assert [i["video_id"] for i in client.get("/reports").json()["items"]] == ["aaaaaaaaaaa"]
