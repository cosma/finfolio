# Quickstart: Monthly Digest Module

**Purpose**: End-to-end validation guide for the Monthly Digest feature

**Updated**: 2026-09-27 (per /speckit-clarify Clarification Q3 - JSON schema)

**Prerequisites**: 
- FinFolio environment set up (venv activated, dependencies installed)
- Module 1 (transcript fetch), Module 2 (summarization), and Module 3 (fact-checking) working
- At least one fact-checking report in `storage/reports/videos/` with a publication date in a known month
- Reports must have `summary.metadata.publication_date` field for month assignment

---

## Setup for Testing

### 1. Prepare Test Data

Before running the digest command, ensure you have at least one fact-checking report. If not, generate one using Module 3:

```bash
# Run fact-checking to generate test reports
finfolio factcheck
```

Verify reports exist:

```bash
ls -la storage/reports/videos/ | head -5
# Expected output: several JSON files like 'dQw4w9WgXcQ.json'
```

### 2. Check Report Structure

Pick a recent report and verify it has the expected fields (used by digest aggregation):

```bash
# View a sample report's structure
python3 -c "
import json
from pathlib import Path

report = next(Path('storage/reports/videos').glob('*.json'))
with open(report) as f:
    data = json.load(f)
    
# Check required fields
required = ['video_id', 'channel_name', 'channel_url', 'verdict_breakdown', 'monetization_disclosure', 'summary']
for field in required:
    print(f'{field}: {field in data}')
    
print(f'Summary has publication_date: {\"publication_date\" in data.get(\"summary\", {})}')
"
```

---

## Test Scenarios

### Scenario 1: Generate Digest for Current Month

**Goal**: Generate a digest for the current month and verify output format

```bash
# Generate digest for current month (e.g., 2026-09)
finfolio report --month 2026-09

# Expected output: JSON log with success status
# {
#   "timestamp": "2026-09-26T15:30:45Z",
#   "event": "digest_generated",
#   "status": "success",
#   "month": "2026-09",
#   "digest_path": "storage/reports/monthly/2026-09.json"
# }

# Verify digest file was created
ls -lh storage/reports/monthly/2026-09.json

# View digest structure (per Clarification Q3 schema)
python3 -c "
import json
with open('storage/reports/monthly/2026-09.json') as f:
    digest = json.load(f)
    print(f'Month: {digest[\"month\"]}')
    print(f'Report count: {digest[\"report_count\"]}')
    print(f'Generated at: {digest[\"generated_at\"]}')
    print(f'Verdict breakdown: {digest[\"verdict_breakdown\"]}')
    print(f'Channels: {len(digest[\"per_channel_breakdown\"])}')
    print(f'Monetization entries: {len(digest[\"monetization_summary\"])}')
"
```

### Scenario 2: Default to Current Month

**Goal**: Verify that `--month` flag defaults to current month if omitted

```bash
# Run without --month flag
finfolio report

# Expected: Digest generated for current month (2026-09 if today is Sept 26)
# Check that the same file was generated
cat storage/reports/monthly/2026-09.json | jq '.month'
# Expected output: "2026-09"
```

### Scenario 3: Empty Month Handling

**Goal**: Generate digest for a month with no reports

```bash
# Request digest for a month far in the past (no reports)
finfolio report --month 2020-01

# Expected output: success (even with zero reports)
# Verify digest was created with zero counts
cat storage/reports/monthly/2020-01.json | jq '.report_count'
# Expected output: 0

cat storage/reports/monthly/2020-01.json | jq '.verdict_breakdown'
# Expected output (per Clarification Q3):
# {
#   "True": 0,
#   "Partially supported": 0,
#   "Unverified": 0,
#   "False": 0
# }
```

### Scenario 4: Idempotent Operation

**Goal**: Verify that running the command twice produces identical results

```bash
# Generate digest
finfolio report --month 2026-09
HASH1=$(md5sum storage/reports/monthly/2026-09.json | cut -d' ' -f1)

# Wait a moment
sleep 2

# Generate again
finfolio report --month 2026-09
HASH2=$(md5sum storage/reports/monthly/2026-09.json | cut -d' ' -f1)

# Verify hashes match (content is identical)
if [ "$HASH1" = "$HASH2" ]; then
    echo "✓ Idempotent: both runs produced identical digests"
else
    echo "✗ NOT idempotent: digests differ"
fi
```

### Scenario 5: Per-Channel Breakdown

**Goal**: Verify that per-channel breakdown is computed correctly

```bash
# Generate digest and inspect per-channel data
python3 << 'EOF'
import json
from collections import defaultdict

with open('storage/reports/monthly/2026-09.json') as f:
    digest = json.load(f)

# Print per-channel stats (per Clarification Q3 schema)
for channel in digest['per_channel_breakdown']:
    print(f"\nChannel: {channel['channel_name']}")
    print(f"  URL: {channel['channel_url']}")
    print(f"  Videos: {channel['video_count']}")
    print(f"  Verdicts: {channel['verdict_breakdown']}")

# Verify: sum of all channel verdicts = overall verdicts
overall = digest['verdict_breakdown']
channel_sum = defaultdict(int)
for channel in digest['per_channel_breakdown']:
    for verdict_type, count in channel['verdict_breakdown'].items():
        channel_sum[verdict_type] += count

print("\n✓ Verification: per-channel sums match overall breakdown")
for verdict_type in overall:
    if overall[verdict_type] == channel_sum.get(verdict_type, 0):
        print(f"  {verdict_type}: ✓")
    else:
        print(f"  {verdict_type}: ✗ (overall={overall[verdict_type]}, sum={channel_sum[verdict_type]})")
EOF
```

### Scenario 6: Monetization Summary

**Goal**: Verify that monetization disclosures are aggregated correctly (per Clarification Q3)

```bash
# Generate digest and inspect monetization summary
python3 << 'EOF'
import json

with open('storage/reports/monthly/2026-09.json') as f:
    digest = json.load(f)

summary = digest['monetization_summary']
print(f"Total monetization entries: {len(summary)}")

if len(summary) > 0:
    for entry in summary:
        print(f"\nChannel: {entry['channel_name']}")
        print(f"  Disclosure: {entry['disclosure']}")
else:
    print("No monetization disclosures found in month")
EOF
```

### Scenario 7: Invalid Month Format

**Goal**: Verify error handling for invalid input

```bash
# Test invalid month formats
finfolio report --month 2026-13  # Invalid month (13)
# Expected: error message, no file created

finfolio report --month "09-2026"  # Wrong format
# Expected: error message, no file created

finfolio report --month "2026"  # Missing month
# Expected: error message, no file created

finfolio report --month "2026-09-01"  # Too precise
# Expected: error message, no file created
```

---

## Contract Validation

### Digest JSON Schema Validation

Verify that generated digest files conform to the schema defined in [contracts/digest-schema.md](contracts/digest-schema.md):

```bash
# Run schema validation test (part of test suite)
pytest tests/contract/test_digest_schema.py -v

# Expected: all tests pass
```

---

## Performance Baseline

### Test Digest Generation Speed

```bash
# Time digest generation for a month with multiple reports
time finfolio report --month 2026-09

# Expected: completes in under 2 seconds for 50 videos
# Output should show:
# real    0m0.XXs
# user    0m0.XXs
# sys     0m0.XXs
```

---

## Failure Scenarios

### Scenario A: Corrupted Report File

**Goal**: Verify graceful handling of malformed JSON

1. Create a corrupted report:
```bash
echo "invalid json {" > storage/reports/videos/corrupted.json
```

2. Generate digest:
```bash
finfolio report --month 2026-09
```

3. Expected behavior:
   - Log: corrupted file is skipped with error message
   - Digest: still generated from valid reports
   - Exit code: 0 (success with warnings logged)

4. Cleanup:
```bash
rm storage/reports/videos/corrupted.json
```

### Scenario B: Missing Required Fields

**Goal**: Verify handling of reports with missing verdict_breakdown

1. Load a report and remove verdict_breakdown:
```bash
python3 << 'EOF'
import json
from pathlib import Path

# Find first report
report_file = next(Path('storage/reports/videos').glob('*.json'))
with open(report_file) as f:
    data = json.load(f)

# Remove required field
del data['verdict_breakdown']

with open(report_file, 'w') as f:
    json.dump(data, f)

print(f"Removed verdict_breakdown from {report_file.name}")
EOF
```

2. Generate digest:
```bash
finfolio report --month 2026-09
```

3. Expected behavior:
   - Log: report with missing field is skipped
   - Digest: generated from other valid reports
   - Exit: success

4. Restore the report (from git):
```bash
git checkout storage/reports/videos/
```

---

## Manual Inspection Checklist

- [ ] Digest file exists at `storage/reports/monthly/{year}-{month}.json`
- [ ] JSON is valid (parses with `jq` or Python `json` module)
- [ ] `month` field matches requested month (YYYY-MM format, e.g. 2026-09)
- [ ] `generated_at` is recent (within last minute, ISO 8601 UTC format)
- [ ] `report_count` >= 0
- [ ] `verdict_breakdown` object exists with all 4 verdict types (True, Partially supported, Unverified, False)
- [ ] Sum of verdict_breakdown counts >= 0
- [ ] `per_channel_breakdown` is array (may be empty if report_count = 0)
- [ ] Each channel in breakdown has `video_count` >= 1
- [ ] Channel verdict counts sum to overall verdict_breakdown counts
- [ ] `monetization_summary` is array (may be empty)
- [ ] Each entry in monetization_summary has `channel_name` and `disclosure` fields
- [ ] No duplicate (channel_name, disclosure) pairs in monetization_summary
- [ ] Verdict field names are canonical: "True", "Partially supported", "Unverified", "False" (not "overstated")

---

## Next Steps

After manual validation:
1. Run full test suite: `pytest tests/ -v`
2. Run linting: `ruff check src/finfolio/`
3. Run type checking: `mypy src/finfolio/`
4. Create PR with implementation
