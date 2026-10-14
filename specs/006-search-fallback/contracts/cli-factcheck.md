# Contract: `finfolio factcheck`

| Exit code | Meaning | Output (stdout / log) |
|---|---|---|
| 0 | All pending videos processed, or none pending. | Summary: videos processed, claims verified, errors, duration. |
| 1 | Configuration error or unexpected failure before processing. | Error message. |
| 2 | A search failed. The run stopped; partial verdicts are saved. | `Search failed at video X: <cause>` or `Tavily search credits are used up at video X`, then `Stopped. Partial verdicts are saved; re-run after fixing the cause.` |

**Resume behavior**: re-running the command continues with claims that have no verdict and with verdicts that need a re-check. Verdicts already final are not searched again.

**Options**: `--limit N`, `--video-id ID`, `--verbose` (unchanged).
