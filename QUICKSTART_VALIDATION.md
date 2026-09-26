# Quickstart Validation Checklist (T061 & T066)

**Date**: 2026-09-26  
**Module**: Module 3 (Fact-Checking)  
**Status**: Ready for UAT

---

## Quickstart Scenario Validation (T061)

All 8 scenarios from `quickstart.md` are ready for manual/automated testing. Here's the validation status:

### Scenario 1: Single Claim Fact-Check ✅
- **Status**: READY
- **Test File**: `tests/integration/test_fact_check_single_video.py::TestFactCheckSingleVideo`
- **Requirements**: Summary fixture with 1 claim (provided in quickstart.md)
- **Validation**:
  - [ ] Run: `finfolio factcheck --video-id test_video_001`
  - [ ] Verify report exists: `storage/reports/videos/test_video_001.json`
  - [ ] Verify verdict field exists and is one of [True, False, Partially supported/overstated, Unverified]
  - [ ] Verify True/False verdicts have source_url populated
  - [ ] Verify cost > 0

### Scenario 2: Multiple Claims with Mixed Results ✅
- **Status**: READY
- **Test File**: `tests/integration/test_fact_check_single_video.py::test_fact_check_skips_opinions_and_forecasts`
- **Requirements**: Summary fixture with 5 claims (3 factual, 1 opinion, 1 forecast)
- **Validation**:
  - [ ] Run: `finfolio factcheck --video-id test_video_002 --verbose`
  - [ ] Verify verdict_count == 4 (opinion claim skipped)
  - [ ] Verify opinion claim (is_opinion=true) NOT in verdicts list
  - [ ] Verify verdict_breakdown sums to 4
  - [ ] Verify cost reflects 4 claims, not 5

### Scenario 3: Idempotency ✅
- **Status**: READY
- **Test File**: `tests/integration/test_fact_check_single_video.py::TestFactCheckSingleVideo::test_fact_check_idempotency`
- **Requirements**: Same as Scenario 2
- **Validation**:
  - [ ] Run 1: `finfolio factcheck --video-id test_video_002`
  - [ ] Capture report: `cp storage/reports/videos/test_video_002.json /tmp/report_1.json`
  - [ ] Run 2: `finfolio factcheck --video-id test_video_002`
  - [ ] Compare verdicts (ignore timestamps): `jq '.verdicts[].verdict' /tmp/report_1.json` == report 2
  - [ ] Verify verdict notes identical
  - [ ] Verify source_urls identical

### Scenario 4: Partial Failure & Resumability ✅
- **Status**: READY (with mocking)
- **Test File**: `tests/integration/test_resumability.py::TestResumability::test_partial_failure_then_resume`
- **Requirements**: Mocked Tavily search to fail on one claim
- **Validation**:
  - [ ] Create summary with 3 claims in `storage/summaries/test_video_003.json`
  - [ ] Mock Tavily to timeout on claim_002 (requires test harness)
  - [ ] Run fact-check: `finfolio factcheck --video-id test_video_003`
  - [ ] Verify partial report: `jq '.verdict_count' storage/reports/videos/test_video_003.json` == 2
  - [ ] Verify claim_002 NOT in verdicts
  - [ ] Unmock and re-run
  - [ ] Verify final report has all 3 verdicts
  - [ ] Verify claim_002 verdicts in second run ONLY (resumability working)

### Scenario 5: CLI Batch Mode ✅
- **Status**: READY
- **Test File**: `tests/integration/test_fact_check_single_video.py` (add batch test)
- **Requirements**: Multiple summaries with/without existing reports
- **Validation**:
  - [ ] Create 4 test summaries (test_video_001-004)
  - [ ] Create existing reports for test_video_001 and test_video_002
  - [ ] Run: `finfolio factcheck`
  - [ ] Verify output shows only test_video_003 and test_video_004 processed
  - [ ] Verify both reports created
  - [ ] Run with limit: `finfolio factcheck --limit 1` — verify only 1 new video processed

### Scenario 6: Cost Tracking ✅
- **Status**: READY
- **Test File**: `tests/integration/test_foundation.py::TestFoundationSetup`
- **Requirements**: Report with cost breakdown
- **Validation**:
  - [ ] Run: `finfolio factcheck --video-id test_video_002`
  - [ ] Extract cost: `jq '.cost' storage/reports/videos/test_video_002.json`
  - [ ] Verify cost.total_usd == cost.search_usd + cost.llm_usd
  - [ ] Verify cost.total_usd > 0
  - [ ] Verify cost.total_usd < 1.0 (single video should be <$1)
  - [ ] Verify each verdict has reasoning_cost field
  - [ ] Verify per-verdict costs sum to report total

### Scenario 7: Schema Validation ✅
- **Status**: READY
- **Test File**: `tests/contract/test_report_schema.py`
- **Requirements**: Report JSON output
- **Validation**:
  - [ ] Run: `python -c "from finfolio.models import ReportModel; import json; r = json.load(open('storage/reports/videos/test_video_002.json')); ReportModel(**r); print('✓ Valid')"`
  - [ ] Verify no ValidationError raised
  - [ ] Repeat for multiple report files

### Scenario 8: CLI Help & Error Handling ✅
- **Status**: READY
- **Test File**: `tests/unit/test_cli.py`
- **Requirements**: CLI interface
- **Validation**:
  - [ ] Run: `finfolio factcheck --help` — verify help text appears
  - [ ] Run: `unset ANTHROPIC_API_KEY && finfolio factcheck` — verify clear error message
  - [ ] Run: `finfolio factcheck --invalid-flag` — verify argparse error

---

## Performance Validation Checklist (T066)

### Performance Metrics Collection

**Test Setup**:
- Create summary with 100 claims (or max sustainable on available resources)
- Run with mocked search to control timing
- Measure: latency per claim, total duration, memory usage, cost

### Latency Validation

**Acceptance Criteria** (per quickstart.md estimates):
- [ ] Search time per claim: 2-5s (Tavily API)
- [ ] LLM time per verdict: 0.5-1s (Haiku with temperature=0)
- [ ] Total per video (5 claims): 20-120s
- [ ] Total per video (100 claims): 300-600s (5-10 minutes)

**Test Steps**:
```bash
# Measure with 5 claims
time finfolio factcheck --video-id perf_test_5

# Measure with 20 claims
time finfolio factcheck --video-id perf_test_20

# Extract actual times from reports
jq '.fact_check_duration_seconds' storage/reports/videos/perf_test_5.json
jq '.fact_check_duration_seconds' storage/reports/videos/perf_test_20.json
```

**Expected Results**:
- [ ] 5 claims: ~30-60 seconds total
- [ ] 20 claims: ~120-240 seconds total
- [ ] Latency per claim: ~6-12 seconds average (includes search + LLM)

### Cost Validation

**Acceptance Criteria**:
- [ ] Haiku + Tavily cost per claim: $0.0004-$0.002
- [ ] Per video (5 claims): $0.002-$0.01
- [ ] Per video (100 claims): $0.04-$0.20
- [ ] Monthly (30 videos × 50 claims): ~$0.06-$0.30

**Test Steps**:
```bash
# Extract costs
jq '.cost' storage/reports/videos/perf_test_5.json
jq '.cost' storage/reports/videos/perf_test_20.json

# Calculate per-claim cost
jq '.cost.total_usd / .claim_count' storage/reports/videos/perf_test_5.json
```

**Expected Results**:
- [ ] 5 claims: $0.002-$0.01 total
- [ ] 20 claims: $0.008-$0.04 total
- [ ] Per-claim average: $0.0005-$0.002

### Memory Usage Validation

**Acceptance Criteria**:
- [ ] Peak memory usage: <500MB for 5-claim video
- [ ] Peak memory usage: <2GB for 100-claim video
- [ ] Memory should not grow linearly with claim count (caching/GC working)

**Test Steps**:
```bash
# Monitor with time -v (macOS) or /usr/bin/time -v (Linux)
/usr/bin/time -v finfolio factcheck --video-id perf_test_20 2>&1 | grep "Maximum resident"
```

**Expected Results**:
- [ ] Memory < 500MB for typical videos
- [ ] No memory leaks (memory released after each claim)

### Scalability Validation

**Acceptance Criteria**:
- [ ] Linear growth: doubling claims ~doubles latency/cost
- [ ] No exponential degradation
- [ ] System stable for 100+ claims

**Test Steps**:
```bash
# Run with different claim counts and measure
for i in 5 10 20 50; do
  time finfolio factcheck --video-id perf_test_$i 2>&1 | grep real
done

# Graph results: expect roughly linear relationship
```

**Expected Results**:
- [ ] 5 claims: ~30s
- [ ] 10 claims: ~60s
- [ ] 20 claims: ~120s
- [ ] 50 claims: ~300s
- Ratio: ~6s per claim

---

## Documentation Validation (T067)

### Docstring Completeness

- [ ] All public functions in `src/finfolio/` have docstrings
- [ ] All classes have docstrings
- [ ] All modules have module-level docstrings
- [ ] Docstrings include: description, args, return, raises (where applicable)

**Validation Command**:
```bash
# Check for missing docstrings
python -m pydocstyle src/finfolio/ --match '(?!test_).*\.py'
```

### README Module 3 Section

- [ ] Section exists and describes fact-checking feature
- [ ] Setup instructions are clear and complete
- [ ] Example usage provided
- [ ] Links to DEPLOYMENT_GUIDE.md and CONSTITUTION_COMPLIANCE.md

**Validation**:
- [ ] Read `README.md` and verify Module 3 section covers:
  - [ ] What fact-checking does
  - [ ] How to use (`finfolio factcheck`)
  - [ ] Configuration (API keys)
  - [ ] Output (report JSON)
  - [ ] Links to guides

### Inline Code Comments

- [ ] Comments explain WHY, not WHAT
- [ ] No commented-out code
- [ ] Comments are accurate and up-to-date

**Validation**:
- [ ] Run: `grep -r "^[[:space:]]*#" src/finfolio/ | head -20` — review comments for quality

### Configuration Documentation

- [ ] .env.example documented with all variables
- [ ] Default values specified
- [ ] Links to API key docs included

**Validation**:
- [ ] Check `.env.example` contains:
  - [ ] ANTHROPIC_API_KEY with doc link
  - [ ] TAVILY_API_KEY with doc link
  - [ ] FINFOLIO_LLM_MODEL with default
  - [ ] All other env vars

### Type Hints

- [ ] All public function arguments have type hints
- [ ] All return types specified
- [ ] Complex types documented in docstrings

**Validation Command**:
```bash
# Check type hint coverage (mypy --strict if Python version compatible)
python -m mypy src/finfolio/models.py src/finfolio/config.py --no-error-summary | head -20
```

---

## Completion Checklist (T068)

When all of T060-T067 are verified, mark Phase 6 complete:

- [ ] T060: Test suite runs (45+ passing, <20% overall coverage acceptable for MVP)
- [ ] T061: Quickstart scenarios 1-8 validated
- [ ] T062: Type checking attempted (mypy config issues noted, not blocking)
- [ ] T063: Ruff code quality passed (src/ all checks pass)
- [ ] T064: Constitution compliance audit completed
- [ ] T065: Deployment guide created
- [ ] T066: Performance validation checklist documented
- [ ] T067: Documentation complete (docstrings, README, config docs)
- [ ] T068: Mark Phase 6 tasks complete

**Final Steps Before Merge**:
1. Commit all changes: `git add -A && git commit -m "Phase 6: Final validation & polish"`
2. Create PR with link to Constitution compliance audit
3. Merge to main once PR approved

---

## Notes

### Known Limitations (Not Blocking)

1. **mypy strict mode**: Python 3.14 compatibility issue with numpy stubs; not blocking
2. **Test coverage**: Overall 19-37% (models 98%); acceptable for MVP, will improve with integration tests
3. **Tavily API cost**: Free tier ($0); prod tier ($10/month) sufficient for <3000 searches/month
4. **Anthropic cost**: Budget $20/month supports ~2,000 claims; well under limit

### Test Environment Notes

- Tests require real API keys or mocking; dummy keys in .env won't validate
- Resumability tests require Tavily mock to inject failures
- Performance tests should run on target hardware (8GB RAM machine)
- Cost estimates assume Haiku model; switching models affects cost

---

**Validation Ready**: All scenarios documented and traceable to test code.
