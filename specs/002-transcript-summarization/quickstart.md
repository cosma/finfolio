# Phase 1 Quickstart: Validation Scenarios

**Date**: 2026-09-25 | **Status**: Complete

This document describes end-to-end validation scenarios to verify the summarization module works correctly.

## Prerequisites

1. **Environment Setup**:
   ```bash
   cd /Users/cosmin/Projects/cosma/finfolio
   source venv/bin/activate
   pip install -e .                    # Install finfolio in editable mode
   pip install pytest pytest-cov       # Test tools
   ```

2. **Configuration**:
   ```bash
   # Set model and API key
   export FINFOLIO_LLM_MODEL=claude-haiku-4-5-20251001
   export ANTHROPIC_API_KEY=your-api-key-here
   ```

3. **Test Data**:
   - Create `storage/transcripts/test-video-1.txt` with sample finance content
   - Ensure `storage/summaries/` directory exists (code will create if missing)

---

## Scenario 1: Summarize New Transcript (Happy Path)

**Goal**: Verify that `finfolio summarize` processes an unsummarized transcript end-to-end.

**Setup**:
```bash
# Create a test transcript
cat > storage/transcripts/test-video-1.txt << 'EOF'
Welcome to the Finance Hour podcast. Today I'm discussing three investment themes.

First, semiconductor companies. Apple released the iPhone 15 Pro in September 2023. 
The S&P 500 closed at 5,432 today. I think we'll see strong demand for AI chips 
in 2024, but this is just my forecast, not a fact.

Second, energy stocks. Exxon Mobil's stock price is currently at $95. The company 
announced a $50 billion acquisition of Pioneer Natural Resources in 2023.

Third, I'm bullish on fintech. Square's Cash App had record transactions.

[Advertisement: This episode is brought to you by Masterclass. Use code FINANCE for $100 off.]

That's it for today. Thanks for listening.
EOF
```

**Run**:
```bash
finfolio summarize
```

**Expected Output**:
- Command prints structured JSON logs to stdout:
  ```json
  {"timestamp":"2026-09-25T14:30:00Z","event":"summarization_start","status":"success"}
  {"timestamp":"2026-09-25T14:30:02Z","event":"transcript_processed","status":"success","video_id":"test-video-1","claims_count":4,"cost_usd":0.034}
  {"timestamp":"2026-09-25T14:30:02Z","event":"summarization_complete","status":"success","total_processed":1,"total_errors":0,"total_cost_usd":0.034}
  ```

- File created at `storage/summaries/test-video-1.json` with:
  - `summary`: plain-language summary (~200 words) capturing semiconductor, energy, fintech themes
  - `claims[]`: list of 3-4 factual claims (numbers, dates, company acquisitions)
  - `metadata`: token counts, model, cost, timestamp
  - **Sponsored content filtered**: "Masterclass" ad section NOT in summary or claims

**Verification Commands**:
```bash
# Check file exists
ls -la storage/summaries/test-video-1.json

# Validate JSON schema
python3 -c "
import json, jsonschema
with open('storage/summaries/test-video-1.json') as f:
    data = json.load(f)
schema = json.load(open('specs/002-transcript-summarization/contracts/summary-output.schema.json'))
jsonschema.validate(data, schema)
print('✓ Schema valid')
"

# Inspect content
cat storage/summaries/test-video-1.json | python3 -m json.tool
```

**Acceptance Criteria**:
- ✅ File created with valid JSON structure
- ✅ Claims include iPhone 15 Pro date (September 2023), S&P 500 number (5,432), Exxon acquisition ($50B, 2023)
- ✅ Claims do NOT include opinions: "bullish on fintech" or "I think" statements excluded
- ✅ Sponsored content (Masterclass) NOT in summary or claims
- ✅ Metadata includes cost_usd > 0

---

## Scenario 2: Idempotency (Re-run, Skip Existing)

**Goal**: Verify that running `finfolio summarize` again skips the existing summary.

**Setup**: Use the same test data from Scenario 1.

**Run**:
```bash
# First run (already done above)
# finfolio summarize

# Second run
finfolio summarize
```

**Expected Output**:
- Command prints logs indicating no new transcripts processed:
  ```json
  {"timestamp":"...","event":"summarization_complete","status":"success","total_processed":0,"total_errors":0,"total_cost_usd":0}
  ```

- File `storage/summaries/test-video-1.json` is NOT modified (same timestamp, same content)

**Verification Commands**:
```bash
# Compare file timestamps
ls -la storage/summaries/test-video-1.json
# (timestamps should match from first run)

# Verify file unchanged
md5 storage/summaries/test-video-1.json
# (should be identical to first run)
```

**Acceptance Criteria**:
- ✅ No new processing occurs
- ✅ File not modified (immutability preserved)
- ✅ Report shows 0 transcripts processed

---

## Scenario 3: Error Handling (Malformed Transcript)

**Goal**: Verify that invalid transcripts are skipped with error logging, and batch continues.

**Setup**:
```bash
# Create an empty transcript
touch storage/transcripts/empty-video.txt

# Create another valid transcript for comparison
cat > storage/transcripts/valid-video.txt << 'EOF'
This is a valid finance podcast about Tesla stock. Tesla's market cap was $800 billion 
in Q3 2023. The company delivered 1.8 million vehicles in 2023.
EOF
```

**Run**:
```bash
finfolio summarize
```

**Expected Output**:
- Command processes both transcripts:
  ```json
  {"timestamp":"...","event":"transcript_validation_failed","status":"failed","video_id":"empty-video","error":"Empty transcript"}
  {"timestamp":"...","event":"transcript_processed","status":"success","video_id":"valid-video","claims_count":2,"cost_usd":0.025}
  {"timestamp":"...","event":"summarization_complete","status":"success","total_processed":1,"total_errors":1,"total_cost_usd":0.025}
  ```

- File created at `storage/summaries/valid-video.json`
- NO file created for `storage/summaries/empty-video.json` (error case)

**Verification Commands**:
```bash
# Check valid file exists
ls storage/summaries/valid-video.json

# Check invalid file does NOT exist
ls storage/summaries/empty-video.json
# (should fail: no such file)
```

**Acceptance Criteria**:
- ✅ Empty transcript marked as error, not crash
- ✅ Batch continues processing other transcripts
- ✅ Error count incremented (total_errors: 1)
- ✅ Only valid transcript written to summaries/

---

## Scenario 4: Cost Monitoring & Logging

**Goal**: Verify that cost per transcript is accurately logged.

**Setup**: Use test transcripts from previous scenarios.

**Run**:
```bash
# Clear existing summaries to force re-processing
rm -f storage/summaries/*.json

# Run and capture logs
finfolio summarize > /tmp/finfolio-logs.json
```

**Verification Commands**:
```bash
# Extract and sum costs
python3 << 'EOF'
import json
total_cost = 0
with open('/tmp/finfolio-logs.json') as f:
    for line in f:
        entry = json.loads(line)
        if entry.get('event') == 'transcript_processed':
            cost = entry.get('cost_usd', 0)
            total_cost += cost
            print(f"{entry['video_id']}: ${cost:.4f}")

print(f"\nTotal cost: ${total_cost:.4f}")
# Should be $0.03-0.10 depending on transcript length
EOF

# Check metadata in generated summary
cat storage/summaries/test-video-1.json | python3 -c "
import json, sys
data = json.load(sys.stdin)
meta = data['metadata']
print(f\"Model: {meta['model']}\")
print(f\"Temperature: {meta['temperature']}\")
print(f\"Input tokens: {meta['input_tokens']}\")
print(f\"Output tokens: {meta['output_tokens']}\")
print(f\"Cost: \${meta.get('cost_usd', 0):.4f}\")
"
```

**Acceptance Criteria**:
- ✅ Cost logged to stdout in each transcript_processed event
- ✅ Cost is positive and realistic (~$0.01-0.05 per transcript)
- ✅ Metadata in JSON includes input_tokens, output_tokens, cost_usd
- ✅ Total cost matches sum of individual transcripts

---

## Scenario 5: Large Transcript Truncation

**Goal**: Verify that transcripts exceeding context window are truncated intelligently with warning.

**Setup**:
```bash
# Generate a very long transcript (simulated)
python3 << 'EOF'
# Create a transcript with ~100+ repeated sentences to exceed 85k token threshold
content = "Apple released the iPhone 15 Pro in September 2023. " * 2000
with open('storage/transcripts/long-video.txt', 'w') as f:
    f.write(content)
print(f"Created long-video.txt with {len(content)} characters")
EOF
```

**Run**:
```bash
finfolio summarize
```

**Expected Output**:
- Command logs warning about truncation:
  ```json
  {"timestamp":"...","event":"transcript_truncated","status":"warning","video_id":"long-video","original_tokens":95000,"truncated_tokens":70000}
  {"timestamp":"...","event":"transcript_processed","status":"success","video_id":"long-video","claims_count":1,"cost_usd":0.018}
  ```

- Summary still generated (partial, from first 75% of transcript)
- `metadata.transcript_truncated: true` in output JSON

**Verification Commands**:
```bash
# Check truncation flag
cat storage/summaries/long-video.json | python3 -c "
import json, sys
data = json.load(sys.stdin)
print(f\"Truncated: {data['metadata'].get('transcript_truncated', False)}\")
"
```

**Acceptance Criteria**:
- ✅ Truncation warning logged
- ✅ Summary still generated (no crash/rejection)
- ✅ Output JSON includes `transcript_truncated: true`
- ✅ Claims extracted from available (truncated) content

---

## Scenario 6: Facts vs. Opinions Separation

**Goal**: Verify that factual claims are correctly separated from opinions/forecasts.

**Setup**:
```bash
cat > storage/transcripts/opinion-test.txt << 'EOF'
Today's market analysis. The S&P 500 closed at 5,432 today. 
I think stocks will double in 2025, but that's just my forecast.
Apple released the iPhone 15 Pro in September 2023.
I'm bullish on fintech companies.
Tesla's market cap is $800 billion.
In my opinion, tech stocks are overvalued.
The Fed raised interest rates by 25 basis points in March 2023.
I forecast a recession in 2024.
EOF
```

**Run**:
```bash
finfolio summarize
```

**Verification Commands**:
```bash
# Extract claims and verify they are factual, not opinions
python3 << 'EOF'
import json
with open('storage/summaries/opinion-test.json') as f:
    data = json.load(f)

print("Extracted claims:")
for claim in data['claims']:
    print(f"  - {claim['claim']}")

# Check that opinion statements are NOT in claims
claims_text = ' '.join([c['claim'] for c in data['claims']])
bad_phrases = ['I think', 'I forecast', 'In my opinion', 'bullish', 'overvalued']
for phrase in bad_phrases:
    if phrase.lower() in claims_text.lower():
        print(f"ERROR: Found opinion phrase '{phrase}' in claims!")
    else:
        print(f"✓ Opinion phrase '{phrase}' correctly excluded from claims")
EOF
```

**Acceptance Criteria**:
- ✅ Claims include only verifiable facts: S&P 500 number (5,432), iPhone date (Sept 2023), Tesla cap ($800B), Fed rate hike (25 bps, March 2023)
- ✅ Claims do NOT include: "I think stocks will double", "bullish on fintech", "overvalued", "forecast a recession"
- ✅ Summary mentions opinions but claims list remains fact-only

---

## Scenario 7: CLI Command Integration

**Goal**: Verify the CLI command works end-to-end and integrates with existing finfolio CLI.

**Setup**: Existing test data.

**Run**:
```bash
# Verify help text
finfolio summarize --help

# Run with default settings
finfolio summarize

# Verify command exit code
finfolio summarize
echo $?  # Should be 0 on success
```

**Expected Output**:
- Help text shows command description and usage
- Command returns exit code 0 on success
- Logs printed to stdout

**Acceptance Criteria**:
- ✅ `finfolio summarize --help` displays usage
- ✅ Command integrates into existing `finfolio` CLI
- ✅ Exit code 0 on success

---

## Unit Test Coverage

**Key Test Functions** (in `tests/test_summarizer.py`, `tests/test_summary_storage.py`):

| Test | Verifies |
|------|----------|
| `test_extract_summary_from_transcript()` | LangChain chain produces valid Summary |
| `test_claims_separation_facts_vs_opinions()` | Facts extracted, opinions excluded |
| `test_sponsored_content_filtered()` | Ad sections excluded from output |
| `test_empty_transcript_rejected()` | Validation catches empty input |
| `test_truncation_for_long_transcript()` | Large transcripts truncated, warning logged |
| `test_output_schema_validation()` | Pydantic validation catches malformed output |
| `test_save_summary_atomic()` | Atomic .tmp → .json rename pattern |
| `test_has_summary_idempotency()` | Skip check prevents re-processing |
| `test_cost_logging_accuracy()` | Cost metadata logged correctly |
| `test_summarize_cli_command()` | CLI integration works end-to-end |

---

## Integration Test: End-to-End Batch Run

```bash
# Clean slate
rm -rf storage/summaries/*.json

# Create 3 test transcripts
for i in 1 2 3; do
  cat > storage/transcripts/batch-test-$i.txt << EOF
This is test transcript $i. 
Apple stock closed at \$200 on September 25, 2024. 
The S&P 500 index is at 5500 points today.
EOF
done

# Run batch summarization
finfolio summarize

# Verify results
python3 << 'EOF'
import json
from pathlib import Path

summaries_dir = Path('storage/summaries')
files = list(summaries_dir.glob('batch-test-*.json'))
print(f"Generated {len(files)} summary files")

total_cost = 0
for file in sorted(files):
    with open(file) as f:
        data = json.load(f)
    cost = data['metadata'].get('cost_usd', 0)
    total_cost += cost
    print(f"  {file.name}: {len(data['claims'])} claims, ${cost:.4f}")

print(f"\nTotal cost: ${total_cost:.4f}")
EOF
```

---

## Cleanup

```bash
# Remove test data
rm -rf storage/transcripts/test-*.txt storage/transcripts/batch-test-*.txt storage/transcripts/long-video.txt
rm -rf storage/summaries/test-*.json storage/summaries/batch-test-*.json
```

