"""SC-001, SC-002, SC-004: timing targets on a realistic archive. Times are measured on this machine."""

import time


def test_targets_on_5000_reports_and_24_digests(
    api_storage, write_report, write_digest, make_client
):
    for n in range(5000):
        verdict = ["True", "False", "Unverified", "Partially supported"][n % 4]
        write_report(
            f"v{n:010d}",
            channel_name=f"Channel {n % 20}",
            channel_url=f"https://www.youtube.com/@c{n % 20}",
            fact_checked_at=f"2026-{(n % 12) + 1:02d}-{(n % 27) + 1:02d}T12:00:00.000000Z",
            verdicts=[verdict],
        )
    for m in range(1, 13):
        write_digest(f"2025-{m:02d}")
        write_digest(f"2026-{m:02d}")

    start = time.perf_counter()
    client = make_client()
    startup = time.perf_counter() - start
    assert startup < 10, f"startup took {startup:.2f}s (SC-004 target: under 10s)"

    start = time.perf_counter()
    response = client.get("/reports", params={"channel": "Channel 3", "verdict": "False"})
    filtered = time.perf_counter() - start
    assert response.status_code == 200
    assert filtered < 1, f"filtered list took {filtered:.3f}s (SC-002 target: under 1s)"

    start = time.perf_counter()
    client.get("/digests")
    digest_list = time.perf_counter() - start
    assert digest_list < 1, f"digest list took {digest_list:.3f}s (SC-001 target: under 1s)"

    start = time.perf_counter()
    client.get("/digests/2026/6")
    digest_detail = time.perf_counter() - start
    assert digest_detail < 1, f"digest detail took {digest_detail:.3f}s (SC-001 target: under 1s)"
