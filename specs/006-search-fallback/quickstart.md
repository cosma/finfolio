# Quickstart: Search Fallback and Claim Re-check

## Prerequisites
- Virtualenv active with dependencies installed (`ddgs` included).
- For real runs only: `ANTHROPIC_API_KEY` and `TAVILY_API_KEY` set in `.env`. Tests do not need them.

## 1. Run the test suite (no network, no credits)

```bash
./venv/bin/python -m pytest tests/unit/test_search_chain.py tests/unit/test_recheck.py tests/unit/test_search_quota.py tests/unit/test_cleanup_verdicts.py -q -p no:cacheprovider --no-cov
```

Expected: all pass.

## 2. Check the threshold setting

```bash
FINFOLIO_SEARCH_MIN_CONFIDENCE=0.9 ./venv/bin/python -c "from finfolio.config import Config; print(Config().search_min_confidence)"
```

Expected: `0.9`. Without the variable, the output is `0.8`.

## 3. Dry-run the cleanup (writes nothing)

```bash
./venv/bin/python scripts/cleanup_claim_verdicts.py
```

Expected: reports how many Unverified verdicts would be removed and how many would be marked `tavily`. Once applied, a second dry run reports 0 changes.

## 4. Run the fact-check (costs credits)

```bash
./venv/bin/finfolio factcheck --limit 1 --verbose
```

Expected: each claim logs `verified_by` (duckduckgo or tavily). Exit code 0 on success, or 2 with the message in contracts/cli-factcheck.md if a search failed.

## 5. Confirm the stored record

```bash
python3 -c "import json,sys; d=json.load(open('storage/reports/videos/<VIDEO_ID>.json')); print([(v['claim_id'], v['verdict'], v.get('verified_by'), v.get('confidence')) for v in d['verdicts']]); print('search_provider' in d)"
```

Expected: every verdict has `verified_by`; the last value is `False` for new reports.
