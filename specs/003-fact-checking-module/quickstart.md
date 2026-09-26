# Phase 1: Quickstart & Validation

**Date**: 2026-09-25 | **Branch**: `003-fact-checking-module`

This document describes runnable validation scenarios to verify the fact-checking module works end-to-end. It is a testing guide, not implementation code.

---

## Prerequisites

1. Python 3.10+ with venv activated
2. Dependencies installed: `pip install -r requirements.txt`
3. Environment variables set:
   ```bash
   export ANTHROPIC_API_KEY="sk-ant-..."
   export TAVILY_API_KEY="tvly-..."
   export FINFOLIO_STORAGE_DIR="./storage"
   ```
4. A test summary file ready in `storage/summaries/test_video_001.json` (fixture provided below)

---

## Validation Scenario 1: Single Claim Fact-Check

**Goal**: Verify that a single claim can be fact-checked and a verdict assigned.

**Prerequisite**: Summary fixture with 1 claim

**Setup**:
```json
// File: storage/summaries/test_video_001.json
{
  "video_id": "test_video_001",
  "title": "Simple Test",
  "channel_name": "TestChannel",
  "source_url": "https://youtube.com/watch?v=test_video_001",
  "transcript_source": "YouTube API",
  "summary": "Test summary with one claim.",
  "claims": [
    {
      "id": "claim_001",
      "text": "Apple stock closed at $190 on Sept 23, 2026",
      "quote": "apple stock was at one ninety",
      "type": "number",
      "confidence": 0.85,
      "timestamp": "05:30",
      "is_opinion": false,
      "is_forecast": false
    }
  ]
}
```

**Test Steps**:
1. Run: `python -m finfolio.cli fact_check --video-id test_video_001`
2. Verify report created: `ls -la storage/reports/videos/test_video_001.json`
3. Verify report structure:
   ```bash
   python -c "
   import json
   with open('storage/reports/videos/test_video_001.json') as f:
       report = json.load(f)
   assert report['video_id'] == 'test_video_001'
   assert len(report['verdicts']) == 1
   assert report['verdicts'][0]['verdict'] in ['True', 'False', 'Unverified', 'Partially supported/overstated']
   assert report['verdicts'][0]['source_url'] or report['verdicts'][0]['verdict'] == 'Unverified'
   print('✓ Report structure valid')
   "
   ```

**Expected Outcome**: Report exists, contains 1 verdict, verdict is one of the four categories, true/false verdicts have source URLs.

---

## Validation Scenario 2: Multiple Claims with Mixed Results

**Goal**: Verify batch processing of 5 claims with varied outcomes (True, False, Partially supported, Unverified).

**Setup**:
```json
// File: storage/summaries/test_video_002.json
{
  "video_id": "test_video_002",
  "title": "Multi-Claim Test",
  "channel_name": "TestChannel",
  "source_url": "https://youtube.com/watch?v=test_video_002",
  "transcript_source": "YouTube API",
  "summary": "...",
  "claims": [
    {"id": "claim_001", "text": "Tesla delivered 1.8M vehicles in 2023", "type": "number", "timestamp": "01:00", "is_opinion": false, "is_forecast": false, "quote": "..."},
    {"id": "claim_002", "text": "Bitcoin price is $150,000 today", "type": "number", "timestamp": "02:00", "is_opinion": false, "is_forecast": false, "quote": "..."},
    {"id": "claim_003", "text": "Apple will revolutionize AI in 2025", "type": "product-fact", "timestamp": "03:00", "is_opinion": true, "is_forecast": false, "quote": "..."},
    {"id": "claim_004", "text": "Fed raised rates by 0.25% in Sept 2026", "type": "number", "timestamp": "04:00", "is_opinion": false, "is_forecast": false, "quote": "..."},
    {"id": "claim_005", "text": "Amazon is headquartered in Seattle", "type": "company-fact", "timestamp": "05:00", "is_opinion": false, "is_forecast": false, "quote": "..."}
  ]
}
```

**Test Steps**:
1. Run: `python -m finfolio.cli fact_check --video-id test_video_002 --verbose`
2. Inspect report:
   ```bash
   python -c "
   import json
   with open('storage/reports/videos/test_video_002.json') as f:
       report = json.load(f)
   
   # Should have 4 verdicts (claim_003 is opinion, skipped)
   assert report['verdict_count'] == 4, f'Expected 4 verdicts, got {report[\"verdict_count\"]}'
   
   # Verify opinion claim not fact-checked
   opinions = [v for v in report['verdicts'] if v['claim_id'] == 'claim_003']
   assert len(opinions) == 0, 'Opinion claim should not be fact-checked'
   
   # Verify verdict breakdown
   breakdown = report['verdict_breakdown']
   assert breakdown['True'] + breakdown['False'] + breakdown['Partially supported/overstated'] + breakdown['Unverified'] == 4
   
   print('✓ Batch processing correct')
   print(f\"  Verdicts: {json.dumps(breakdown, indent=2)}\")
   "
   ```

**Expected Outcome**: 4 verdicts (not 5; opinion skipped), verdicts correctly classified, report includes cost breakdown.

---

## Validation Scenario 3: Idempotency

**Goal**: Verify that running `finfolio factcheck` twice produces identical results.

**Setup**: Use summary from Scenario 2.

**Test Steps**:
1. Run 1: `python -m finfolio.cli fact_check --video-id test_video_002`
2. Capture first report: `cp storage/reports/videos/test_video_002.json /tmp/report_1.json`
3. Run 2: `python -m finfolio.cli fact_check --video-id test_video_002`
4. Compare reports:
   ```bash
   python -c "
   import json
   with open('/tmp/report_1.json') as f1, open('storage/reports/videos/test_video_002.json') as f2:
       r1 = json.load(f1)
       r2 = json.load(f2)
   
   # Ignore timestamps (will differ by seconds)
   r1_verdicts = r1['verdicts']
   r2_verdicts = r2['verdicts']
   
   for v1, v2 in zip(r1_verdicts, r2_verdicts):
       assert v1['verdict'] == v2['verdict'], f'Verdict mismatch for {v1[\"claim_id\"]}'
       assert v1['note'] == v2['note'], f'Note mismatch for {v1[\"claim_id\"]}'
       assert v1['source_url'] == v2['source_url'], f'Source URL mismatch for {v1[\"claim_id\"]}'
   
   print('✓ Idempotency verified (verdicts unchanged)')
   "
   ```

**Expected Outcome**: Both runs produce identical verdicts and notes (timestamps may differ, cost may vary slightly).

---

## Validation Scenario 4: Partial Failure & Resumability

**Goal**: Verify that if fact-checking fails on one claim, the report is saved and next run resumes from the failed claim.

**Setup**: Summary with 3 claims, mocked to fail on claim #2.

**Test Steps** (requires test harness):
1. Create summary with 3 claims in `storage/summaries/test_video_003.json`
2. Mock Tavily search to timeout on claim_002:
   ```python
   # In test, inject failure:
   def mock_tavily_search(query):
       if "claim_002" in query:
           raise TimeoutError("Simulated search timeout")
       return [{"title": "...", "url": "...", "content": "..."}]
   ```
3. Run fact-check: `python -m finfolio.cli fact_check --video-id test_video_003`
4. Verify partial report:
   ```bash
   python -c "
   import json
   with open('storage/reports/videos/test_video_003.json') as f:
       report = json.load(f)
   assert report['verdict_count'] == 2  # Only claims 1 and 3
   assert any(v['claim_id'] == 'claim_001' for v in report['verdicts'])
   assert not any(v['claim_id'] == 'claim_002' for v in report['verdicts'])
   assert any(v['claim_id'] == 'claim_003' for v in report['verdicts'])
   print('✓ Partial report saved')
   "
   ```
5. Unmock Tavily and run again:
   ```python
   def mock_tavily_search(query):
       return [{"title": "...", "url": "...", "content": "..."}]
   ```
6. Run fact-check again: `python -m finfolio.cli fact_check --video-id test_video_003`
7. Verify full report:
   ```bash
   python -c "
   import json
   with open('storage/reports/videos/test_video_003.json') as f:
       report = json.load(f)
   assert report['verdict_count'] == 3  # All claims now
   print('✓ Resumability verified; all claims now processed')
   "
   ```

**Expected Outcome**: First run saves claims 1 and 3, skips 2. Second run skips 1 and 3, processes 2. Final report has all 3 verdicts.

---

## Validation Scenario 5: CLI Batch Mode

**Goal**: Verify CLI processes all pending summaries and reports progress.

**Setup**:
- `storage/summaries/test_video_001.json` (has report)
- `storage/summaries/test_video_002.json` (has report)
- `storage/summaries/test_video_004.json` (no report)
- `storage/summaries/test_video_005.json` (no report)

**Test Steps**:
1. Run batch: `python -m finfolio.cli fact_check`
2. Verify stdout output:
   ```bash
   python -m finfolio.cli fact_check 2>&1 | grep -E "Processing|processed|cost"
   ```
   Expected output:
   ```
   Processing pending summaries...
   [1/2] test_video_004: 12 claims → 12 verdicts...
   [2/2] test_video_005: 8 claims → 8 verdicts...
   Total: 2 processed, 20 claims verified
   ```
3. Verify reports created:
   ```bash
   ls -la storage/reports/videos/test_video_004.json storage/reports/videos/test_video_005.json
   ```

**Expected Outcome**: Batch processing completes, 2 videos processed, progress logged to stdout, reports created.

---

## Validation Scenario 6: Cost Tracking

**Goal**: Verify cost is logged per-video and in aggregate.

**Test Steps**:
1. Run: `python -m finfolio.cli fact_check --video-id test_video_002`
2. Check report for cost:
   ```bash
   python -c "
   import json
   with open('storage/reports/videos/test_video_002.json') as f:
       report = json.load(f)
   cost = report['cost']
   print(f\"Search cost: \${cost['search_usd']:.4f}\")
   print(f\"LLM cost: \${cost['llm_usd']:.4f}\")
   print(f\"Total: \${cost['total_usd']:.4f}\")
   assert cost['total_usd'] == cost['search_usd'] + cost['llm_usd']
   assert cost['total_usd'] > 0, 'Cost should be > 0'
   assert cost['total_usd'] < 1.0, 'Cost for 1 video should be < $1'
   "
   ```
3. Check per-verdict cost:
   ```bash
   python -c "
   import json
   with open('storage/reports/videos/test_video_002.json') as f:
       report = json.load(f)
   for v in report['verdicts']:
       assert 'reasoning_cost' in v
       assert v['reasoning_cost']['cost_usd'] > 0
       print(f\"  {v['claim_id']}: \${v['reasoning_cost']['cost_usd']:.6f}\")
   "
   ```

**Expected Outcome**: Report contains cost breakdown, per-verdict costs sum to report total, costs are reasonable ($0.0001-0.0005 per verdict).

---

## Validation Scenario 7: Schema Validation

**Goal**: Verify report JSON passes schema validation.

**Test Steps**:
```python
from pydantic import ValidationError
from finfolio.models import ReportModel
import json

with open('storage/reports/videos/test_video_002.json') as f:
    report_data = json.load(f)

try:
    report = ReportModel(**report_data)
    print('✓ Report schema valid')
except ValidationError as e:
    print(f'✗ Schema validation failed: {e}')
    raise
```

**Expected Outcome**: Report passes Pydantic schema validation, no errors.

---

## Validation Scenario 8: CLI Help & Error Handling

**Goal**: Verify CLI provides clear help and error messages.

**Test Steps**:
1. Help message: `python -m finfolio.cli fact_check --help`
   - Expect: Usage, options, examples
2. Missing API key:
   ```bash
   unset ANTHROPIC_API_KEY
   python -m finfolio.cli fact_check 2>&1 | grep -i "api_key"
   ```
   - Expect: Clear error message about missing API key

**Expected Outcome**: `--help` works, error messages are clear and actionable.

---

## Manual Testing Checklist

Run through these steps manually to verify the feature works end-to-end:

- [ ] **Setup**: Activate venv, set env vars, verify storage dir exists
- [ ] **Scenario 1**: Single claim fact-checked correctly
- [ ] **Scenario 2**: Multiple claims with mixed outcomes; opinions skipped
- [ ] **Scenario 3**: Running twice produces identical verdicts
- [ ] **Scenario 4**: Partial failure recovers on retry
- [ ] **Scenario 5**: Batch processing discovers and processes all pending videos
- [ ] **Scenario 6**: Cost tracked and reported per-video and in aggregate
- [ ] **Scenario 7**: Report JSON passes schema validation
- [ ] **Scenario 8**: CLI help and error messages are clear

---

## Integration with Test Suite

These scenarios should be automated in `tests/integration/test_fact_check.py`:

```python
def test_single_claim_fact_check(tmp_storage):
    """Scenario 1: Single claim fact-check."""
    summary = {
        "video_id": "test_001",
        "claims": [{"id": "c1", "text": "...", ...}]
    }
    save_summary("test_001", summary)
    
    from finfolio.cli import fact_check
    fact_check(video_id="test_001")
    
    report = load_report("test_001")
    assert report["verdict_count"] == 1
    # ... more assertions

def test_idempotency(tmp_storage):
    """Scenario 3: Idempotency."""
    # Run twice, compare verdicts
    # ... implementation

def test_resumability_after_failure(tmp_storage, mock_tavily):
    """Scenario 4: Resumability."""
    # Mock failure, run, verify partial; unmock, run, verify complete
    # ... implementation
```

---

**Quickstart Complete**: Ready for Phase 2 implementation and integration testing.
