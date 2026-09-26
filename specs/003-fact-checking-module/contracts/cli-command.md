# Contract: CLI Command `finfolio factcheck`

**Scope**: User-facing command for batch fact-checking of pending summaries.

---

## Command Signature

```bash
finfolio factcheck [OPTIONS]
```

---

## Options

### `--limit N`
**Type**: Integer  
**Default**: None (process all)  
**Description**: Process at most N videos. Useful for testing and gradual rollouts.  
**Example**: `finfolio factcheck --limit 5`

### `--video-id ID`
**Type**: String  
**Default**: None (batch mode)  
**Description**: Process a single video by ID. Useful for debugging or re-checking one video.  
**Example**: `finfolio factcheck --video-id dQw4w9WgXcQ`

### `--verbose`
**Type**: Flag  
**Default**: False  
**Description**: Enable detailed logging (search queries, LLM prompts, token counts).  
**Example**: `finfolio factcheck --verbose`

### `--help`
**Type**: Flag  
**Description**: Print help message and exit.

---

## Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Success (all videos processed, may have errors on individual claims) |
| 1 | Fatal error (no videos to process, config missing, API auth failed) |
| 2 | Command-line parsing error (invalid arguments) |

---

## Output

### Standard Output (stdout)

**Format**: Human-readable progress report

```
Processing pending summaries...
[1/3] dQw4w9WgXcQ: "Apple Q3 Earnings Review"
  Claims: 15 | Verdicts: 15 | Errors: 0 | Cost: $0.03 | Duration: 45.2s
[2/3] xyzABCdef123: "Tesla Battery Tech"
  Claims: 12 | Verdicts: 10 | Errors: 2 (retryable) | Cost: $0.02 | Duration: 38.1s
[3/3] abc123XYZ: "skipped (report exists)"

Summary:
  Videos processed: 2
  Total claims verified: 25
  Total errors: 2 (will retry on next run)
  Total cost: $0.05 USD
  Total duration: 83.3s

Done.
```

### Structured Logging (stderr / log file)

**Format**: JSON-per-line (JSONL) for parsing

```json
{"timestamp":"2026-09-25T15:30:00Z","level":"INFO","message":"Start fact-checking","videos_pending":3}
{"timestamp":"2026-09-25T15:30:01Z","level":"INFO","message":"Processing video","video_id":"dQw4w9WgXcQ","summary_loaded":true,"claims_count":15}
{"timestamp":"2026-09-25T15:30:05Z","level":"DEBUG","message":"Search query","claim_id":"claim_001","query":"Apple AAPL stock price Sept 23 2026"}
{"timestamp":"2026-09-25T15:30:10Z","level":"DEBUG","message":"LLM verdict","claim_id":"claim_001","verdict":"True","tokens_in":450,"tokens_out":85,"cost_usd":0.0001}
{"timestamp":"2026-09-25T15:30:46Z","level":"INFO","message":"Video complete","video_id":"dQw4w9WgXcQ","claim_count":15,"verdict_count":15,"error_count":0,"cost_usd":0.03,"duration_seconds":45.2}
{"timestamp":"2026-09-25T15:31:15Z","level":"ERROR","message":"Search timeout","video_id":"xyzABCdef123","claim_id":"claim_008","query":"...","retry":"next_run"}
{"timestamp":"2026-09-25T15:32:00Z","level":"INFO","message":"Batch complete","videos_processed":2,"claims_verified":25,"errors":2,"cost_usd":0.05,"duration_seconds":83.3}
```

**Environment Variable**: `FINFOLIO_LOG_LEVEL` controls verbosity (DEBUG, INFO, WARNING, ERROR)

---

## Behavior

### Successful Run

1. Discover all videos with summaries but no reports
2. For each video (up to `--limit`):
   a. Load summary from `storage/summaries/{video_id}.json`
   b. Extract claims
   c. For each claim not yet in report (resumability):
      - Query Tavily for claim verification
      - Use LLM to assign verdict
      - Incrementally save verdict to report file
   d. Log video results to stdout and JSONL
3. Print summary (total processed, cost, errors)
4. Exit with code 0

### Partial Failure

- If fact-checking fails on claim #6 of 10:
  - Claims 1-5 are saved in report
  - Claims 6-10 are not in report
  - Next run skips 1-5, retries 6-10
  - Error logged with "retryable" flag

### Idempotency

- If run twice with same video set:
  - First run: processes all pending videos
  - Second run: all reports exist, skips all videos, reports "0 processed"
  - No duplicate verdicts or corrupted reports

### Single Video Mode

```bash
finfolio factcheck --video-id dQw4w9WgXcQ
```

- Process one video regardless of whether report exists
- Useful for re-checking or debugging
- Output same format as batch mode

---

## Configuration

**Environment Variables**:
- `FINFOLIO_STORAGE_DIR`: Base storage directory (default: `./storage`)
- `FINFOLIO_LLM_MODEL`: LLM model name (default: `claude-haiku-4-5-20251001`)
- `ANTHROPIC_API_KEY`: Claude API key (required)
- `TAVILY_API_KEY`: Tavily search API key (required)
- `FINFOLIO_LOG_LEVEL`: Logging level (default: `INFO`)

**Config File** (optional): `~/.finfolio/config.yaml`
```yaml
storage_dir: ./storage
llm_model: claude-haiku-4-5-20251001
log_level: INFO
search_timeout_seconds: 10
max_concurrent_searches: 3  # future: for async processing
```

---

## Error Scenarios

### Missing Config
```
ERROR: ANTHROPIC_API_KEY not set. Set it and retry.
Exit: 1
```

### No Pending Videos
```
INFO: No pending videos to process.
Exit: 0
```

### API Quota Exhausted
```
[1/3] dQw4w9WgXcQ: Claims 1-5 processed, Claims 6-15 marked "Unverified" (quota exhausted)
  Partial report saved. Retry on next run after quota reset.
Exit: 0
```

### Network Error Mid-Run
```
[2/3] xyzABCdef123: ERROR during fact-checking
  (Connection timeout on claim #8)
  Partial report saved with claims 1-7. Claims 8+ will retry on next run.
Exit: 0
```

---

## Constraints

- **Max Claims per Video**: No hard limit; typical 10-30 claims per video
- **Max Videos per Run**: Configurable via `--limit`; default unlimited
- **Timeout per Claim**: 10 seconds (search + LLM reasoning)
- **Cost Reporting**: Always reported per video and in aggregate

---

## Testing

**Unit Tests**:
- `test_cli_help()`: `--help` prints usage
- `test_cli_missing_api_key()`: Exits 1 if ANTHROPIC_API_KEY missing
- `test_cli_no_pending_videos()`: Exits 0, outputs "No pending videos"

**Integration Tests**:
- `test_cli_single_video()`: Processes one video, creates report
- `test_cli_batch_mode()`: Processes 3 videos, correct output format
- `test_cli_idempotency()`: Second run reports 0 processed

**E2E Tests** (with real API):
- `test_cli_end_to_end()`: Fetch real summary, run fact-checking, verify report exists

---

**Contract Version**: 1.0 | **Status**: Final
