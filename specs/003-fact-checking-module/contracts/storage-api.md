# Contract: Storage API (finfolio.storage module)

**Module**: `finfolio.storage`

**Scope**: Persistent storage operations for fact-checking module. Extends Module 2 storage API with report persistence.

---

## Functions

### `has_report(video_id: str) -> bool`

**Purpose**: Check whether a fact-checking report exists for a video.

**Parameters**:
- `video_id`: Video identifier (e.g., `dQw4w9WgXcQ`)

**Returns**: `True` if report exists at `storage/reports/videos/{video_id}.json`, `False` otherwise

**Behavior**:
- Returns `False` if directory does not exist
- Does not throw if storage unavailable; logs warning and returns `False`

**Error Handling**:
- If filesystem is unavailable, log and return `False` (safe for caller to retry)
- Do not raise exceptions for missing files

**Example**:
```python
if not has_report("dQw4w9WgXcQ"):
    # Process video
```

---

### `save_report(video_id: str, report_data: dict) -> None`

**Purpose**: Atomically persist a fact-checking report to disk.

**Parameters**:
- `video_id`: Video identifier
- `report_data`: Report dictionary (validated against ReportModel schema)

**Returns**: None

**Behavior**:
- Write to temporary file first: `storage/reports/videos/{video_id}.json.tmp`
- Rename to final location atomically (POSIX rename is atomic)
- Overwrite existing report if present (idempotent)
- Create `storage/reports/videos/` directory if it does not exist

**Validation**:
- `report_data` must pass Pydantic ReportModel validation before write
- Raises `ValueError` if validation fails (caller must handle)

**Error Handling**:
- Raises `IOError` if directory cannot be created or file cannot be written
- Raises `ValueError` if report_data is invalid
- On error, .tmp file is left in place for debugging (not cleaned up automatically)

**Atomicity**:
- POSIX rename operation is atomic (even with concurrent access)
- Second caller attempting concurrent write will overwrite first's .tmp file
- Final result is last completed write (last-write-wins semantics)

**Example**:
```python
report = {
    "video_id": "dQw4w9WgXcQ",
    "verdicts": [...],
    ...
}
save_report("dQw4w9WgXcQ", report)  # Atomic write
```

---

### `load_summary(video_id: str) -> dict | None`

**Purpose**: Load summary data from Module 2 (used as input for fact-checking).

**Parameters**:
- `video_id`: Video identifier

**Returns**: Summary dict if file exists, `None` otherwise

**Behavior**:
- Read from `storage/summaries/{video_id}.json`
- Return parsed JSON with all fields intact

**Error Handling**:
- Raises `ValueError` if JSON is malformed
- Returns `None` if file does not exist

**Example**:
```python
summary = load_summary("dQw4w9WgXcQ")
if summary is None:
    logger.warning(f"No summary for {video_id}")
    return

claims = summary["claims"]
```

---

### `list_pending_videos() -> list[str]`

**Purpose**: Discover all videos with summaries but no reports (pending fact-checking).

**Returns**: List of video IDs

**Behavior**:
- Scan `storage/summaries/` directory for .json files
- For each summary, check if corresponding report exists in `storage/reports/videos/`
- Return only video IDs without reports

**Error Handling**:
- If directories do not exist, return empty list (log warning)
- Skip files that are invalid JSON (log error, continue)

**Performance**:
- O(n) scan of summaries directory; acceptable for 10-100 videos

**Example**:
```python
for video_id in list_pending_videos():
    summary = load_summary(video_id)
    # Process fact-checking
```

---

## Invariants

1. **Atomicity**: `save_report()` is atomic; partial writes do not occur
2. **Idempotence**: `save_report(video_id, report1)` followed by `save_report(video_id, report2)` leaves report2 in place
3. **No Partial State**: Report file either does not exist or is valid JSON (never in .tmp state after successful return)
4. **Directory Safety**: `save_report()` creates `storage/reports/videos/` if missing

---

## Implementation Notes

- Use Python's `pathlib.Path` for cross-platform path handling
- Validate `report_data` with Pydantic before atomic write
- Use `json.dump()` with `ensure_ascii=False` to preserve Unicode in claims/notes
- Catch and log exceptions separately for debugging (do not swallow)

---

## Testing

**Unit Tests** (with fixtures):
- `test_has_report_missing()`: Returns `False` for non-existent report
- `test_save_report_creates_dir()`: Creates directory if missing
- `test_save_report_atomic()`: Atomic write via .tmp pattern
- `test_load_summary_missing()`: Returns `None` for non-existent summary
- `test_list_pending_videos()`: Correctly identifies videos without reports

**Integration Tests**:
- `test_save_and_load_report()`: Write then read back; verify data integrity
- `test_save_report_concurrent()`: Concurrent saves (last-write-wins)

---

**Contract Version**: 1.0 | **Status**: Final
