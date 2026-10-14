"""FR-011: the API never writes, modifies, or deletes stored data."""

from pathlib import Path


def _snapshot(storage_root: Path) -> dict[str, tuple[bytes, int]]:
    """Bytes and mtime of every stored file. The derived index file is excluded (it is not stored data)."""
    return {
        str(p.relative_to(storage_root)): (p.read_bytes(), p.stat().st_mtime_ns)
        for p in storage_root.rglob("*")
        if p.is_file() and not p.name.startswith(".finfolio-api-index")
    }


def test_requests_and_refresh_leave_stored_data_untouched(
    api_storage, write_report, write_digest, make_client
):
    write_report("aaaaaaaaaaa", verdicts=["True"])
    write_report("bbbbbbbbbbb", verdicts=["False"])
    write_digest("2026-09")
    client = make_client()
    before = _snapshot(api_storage)

    client.get("/reports")
    client.get("/reports/aaaaaaaaaaa")
    client.get("/digests")
    client.get("/digests/2026/9")
    client.post("/index/refresh")

    assert _snapshot(api_storage) == before
