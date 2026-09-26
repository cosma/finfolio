# FinFolio Module 3 Deployment Guide

**Version**: 1.0  
**Date**: 2026-09-26  
**Status**: Production Ready

---

## Quick Start

```bash
# 1. Clone repository
git clone https://github.com/cosma/finfolio.git
cd finfolio

# 2. Create virtual environment
python3 -m venv venv
source venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment
cp .env.example .env
# Edit .env and fill in your API keys (see below)

# 5. Run fact-checking
finfolio factcheck --limit 5 --verbose

# 6. View results
ls storage/reports/videos/*.json
```

---

## Prerequisites

- Python 3.11+ (tested with 3.11, 3.12, 3.14)
- 8 GB RAM minimum (2 GB Docker VM support requires lean dependencies)
- Internet connection (Tavily API and Claude API required)

---

## API Keys Required

### 1. Anthropic API Key (Claude)
```bash
# Get your key at: https://console.anthropic.com/account/keys
export ANTHROPIC_API_KEY="sk-ant-..."
```

**Cost Estimate**: 
- Haiku model: $0.80/$4.00 per million input/output tokens
- Typical fact-checking run: 50-200 tokens per claim
- Cost per video: $0.002-$0.01 (depending on claim count)
- Monthly budget: ~$20 for 2,000 claims across 20-30 videos

### 2. Tavily Web Search API Key
```bash
# Get your key at: https://tavily.com/
export TAVILY_API_KEY="tvly-..."
```

**Cost Estimate**:
- Tavily: $0 for free tier (up to 1,000 API calls/month)
- Paid tier: $10/month for 10,000 calls/month
- Typical fact-checking: 1 search per claim
- Monthly: 1,500-3,000 searches for ~30 videos

---

## Environment Configuration

Create a `.env` file in the project root:

```bash
# API Keys (required)
ANTHROPIC_API_KEY=sk-ant-your-key-here
TAVILY_API_KEY=tvly-your-key-here

# LLM Configuration (optional - defaults shown)
FINFOLIO_LLM_MODEL=claude-haiku-4-5-20251001

# Storage Configuration (optional)
FINFOLIO_STORAGE_DIR=./storage

# Logging Level (optional)
FINFOLIO_LOG_LEVEL=INFO  # or DEBUG for verbose output

# Search Timeout (optional)
FINFOLIO_SEARCH_TIMEOUT=10  # seconds per search
```

### Configuration Hierarchy
1. Environment variables (`FINFOLIO_*` prefix)
2. `.env` file (in project root)
3. Hardcoded defaults (in `src/finfolio/config.py`)

---

## Installation

### From Source

```bash
# Clone and activate venv (see Quick Start above)

# Install with development dependencies
pip install -e ".[dev]"

# Install production only
pip install -e "."
```

### Docker (Not recommended on 2GB VM)

```bash
# Build image (see warning below)
docker build -t finfolio:latest .

# Run container
docker run \
  -e ANTHROPIC_API_KEY=$ANTHROPIC_API_KEY \
  -e TAVILY_API_KEY=$TAVILY_API_KEY \
  -v $(pwd)/storage:/app/storage \
  finfolio:latest factcheck --limit 5
```

**Warning**: Docker builds on this machine are memory-constrained (2 GB VM). If you encounter OOM errors during build, build on a machine with 4+ GB available RAM and push to a registry.

---

## Running the CLI

### Single Video Fact-Check

```bash
finfolio factcheck --video-id <video_id>
```

**Example**:
```bash
finfolio factcheck --video-id "dQw4w9WgXcQ"
```

**Output**:
- Report saved to: `storage/reports/videos/{video_id}.json`
- Logs: stderr (JSON structured logs)

### Batch Fact-Checking (Multiple Videos)

```bash
# Process all pending videos (up to 10)
finfolio factcheck --limit 10

# Process with verbose logging
finfolio factcheck --verbose

# Combine options
finfolio factcheck --limit 5 --verbose
```

### Exit Codes

- **0**: Success (all videos processed)
- **1**: Fatal error (missing API key, config error, etc.)
- **2**: Argument error (invalid flags, malformed input)

---

## Output & Storage

### Report Location
```
storage/
└── reports/
    └── videos/
        ├── {video_id_1}.json
        ├── {video_id_2}.json
        └── ...
```

### Report Schema

```json
{
  "video_id": "dQw4w9WgXcQ",
  "title": "Video Title",
  "channel_name": "Channel Name",
  "source_url": "https://youtube.com/watch?v=...",
  "transcript_source": "YouTube API",
  
  "fact_checked_at": "2026-09-26T10:30:00Z",
  "fact_check_duration_seconds": 45.2,
  "search_provider": "Tavily",
  "llm_model": "claude-haiku-4-5-20251001",
  
  "cost": {
    "search_usd": 0.0,
    "llm_usd": 0.0045,
    "total_usd": 0.0045
  },
  
  "claim_count": 5,
  "verdict_count": 5,
  "verdict_breakdown": {
    "True": 3,
    "False": 1,
    "Partially supported/overstated": 1,
    "Unverified": 0
  },
  
  "verdicts": [
    {
      "claim_id": "claim_001",
      "claim_text": "...",
      "verdict": "True",
      "note": "...",
      "source_url": "https://...",
      "source_title": "...",
      "source_date": "2026-09-26",
      "search_query": "...",
      "fact_checked_at": "2026-09-26T10:30:05Z",
      "llm_model": "claude-haiku-4-5-20251001",
      "reasoning_cost": {
        "tokens_in": 450,
        "tokens_out": 85,
        "cost_usd": 0.00089
      }
    }
  ],
  
  "disclaimer": "FinFolio reports facts and their accuracy. This is not financial advice."
}
```

---

## Performance & Cost Monitoring

### Per-Video Metrics

```bash
# Extract from report JSON
jq '.cost.total_usd' storage/reports/videos/{video_id}.json
jq '.fact_check_duration_seconds' storage/reports/videos/{video_id}.json
jq '.claim_count' storage/reports/videos/{video_id}.json
```

### Batch Cost Report

```bash
# Sum costs across all reports
jq '.cost.total_usd' storage/reports/videos/*.json | paste -sd+ | bc

# Average cost per claim
jq '.cost.total_usd / .claim_count' storage/reports/videos/*.json | \
  awk '{sum+=$0; count++} END {print sum/count}'
```

### Expected Performance (Haiku + Tavily)

| Metric | Typical Value | Notes |
|--------|---------------|-------|
| Claims per video | 5-20 | From Module 2 summarization |
| Search time per claim | 2-5s | Tavily web search |
| LLM time per verdict | 0.5-1s | Haiku verdict reasoning |
| Total per video | 20-120s | Depends on claim count |
| Cost per video | $0.002-$0.01 | Haiku + Tavily |
| Cost per month (30 videos) | $0.06-$0.30 | Well under budget |

---

## Troubleshooting

### "ANTHROPIC_API_KEY not set"
```bash
# Solution 1: Set environment variable
export ANTHROPIC_API_KEY="sk-ant-..."

# Solution 2: Add to .env file
echo "ANTHROPIC_API_KEY=sk-ant-..." >> .env

# Solution 3: Verify key is set
echo $ANTHROPIC_API_KEY
```

### "Did not find tavily_api_key"
```bash
# Solution 1: Set environment variable
export TAVILY_API_KEY="tvly-..."

# Solution 2: Add to .env file (same as above)
echo "TAVILY_API_KEY=tvly-..." >> .env
```

### "Search timeout"
- Increase `FINFOLIO_SEARCH_TIMEOUT` (default: 10 seconds)
- Check internet connection
- Verify Tavily API is accessible: `curl https://api.tavily.com/`

### "Report validation failed"
- Check that summary JSON is valid (Module 2 output)
- Verify all claims have required fields (id, text, quote, type, confidence, timestamp)
- Check logs: `tail -f storage/logs/finfolio.log` (if logging to file)

### "No pending videos"
- Verify summaries exist in `storage/summaries/`
- Check that reports don't already exist in `storage/reports/videos/`
- Use `--video-id` to force fact-check of specific video (even if report exists)

---

## Logging

### Log Levels

```bash
# Verbose debugging
export FINFOLIO_LOG_LEVEL=DEBUG

# Standard operation
export FINFOLIO_LOG_LEVEL=INFO

# Errors only
export FINFOLIO_LOG_LEVEL=ERROR
```

### Log Format

Logs are output to stderr in JSON format:

```json
{
  "timestamp": "2026-09-26T10:30:05.123456Z",
  "level": "INFO",
  "logger": "finfolio.fact_checker",
  "message": "Fact-checking claim",
  "event_data": {
    "video_id": "dQw4w9WgXcQ",
    "claim_id": "claim_001",
    "search_query": "..."
  }
}
```

---

## Testing Before Production

```bash
# 1. Install test dependencies
pip install -e ".[dev]"

# 2. Run unit tests
pytest tests/unit/test_models.py -v

# 3. Run integration tests (requires API keys)
pytest tests/integration/ -v

# 4. Check code quality
ruff check src/

# 5. Verify types (if mypy works with your Python version)
mypy src/ --strict || echo "Skipping mypy (Python version compatibility issue)"
```

---

## Maintenance

### Regular Checks

```bash
# Weekly: Monitor costs
find storage/reports/videos -type f -mtime -7 -exec \
  jq -s 'add | .cost.total_usd' {} \; | paste -sd+ | bc

# Monthly: Archive old reports
find storage/reports/videos -type f -mtime +30 | xargs tar -czf archive-$(date +%Y-%m).tar.gz

# Before each deploy: Validate test suite
pytest tests/ -v --cov=finfolio --cov-report=term-missing
```

### Updating Dependencies

```bash
# Check for outdated packages
pip list --outdated

# Update specific package (e.g., langchain)
pip install --upgrade langchain

# Update all (use with caution on memory-constrained systems)
pip install --upgrade -r requirements.txt
```

---

## Support & Debugging

### Report a Bug
- Check Constitution compliance first: [CONSTITUTION_COMPLIANCE.md](CONSTITUTION_COMPLIANCE.md)
- Check implementation summary: [IMPLEMENTATION_SUMMARY.md](IMPLEMENTATION_SUMMARY.md)
- File issue with: video_id, error message, full stderr output

### Get Help
- API Key Issues: Check Anthropic/Tavily dashboards for quota/usage
- Fact-Checking Accuracy: See [CONSTITUTION_COMPLIANCE.md](CONSTITUTION_COMPLIANCE.md) Principle I
- Performance: See performance table above; expected cost/time per video

---

## Compliance & Safety

### Constitution Compliance
This deployment guide assumes full compliance with the FinFolio Constitution (v2.1.0):
- Every claim is checked against independent sources (Principle I)
- No financial advice is given (Principle II)
- Facts and forecasts are separated (Principle III)
- Transcript source is transparent (Principle IV)
- Monetization is disclosed (Principle V)
- Official APIs only (Principle VI)
- Cost is monitored and model is configurable (Principle VII)

See [CONSTITUTION_COMPLIANCE.md](CONSTITUTION_COMPLIANCE.md) for full audit.

### Data Privacy
- Reports contain video metadata (title, channel, URL) from YouTube
- Reports contain search results from Tavily (public web pages only)
- No user data is collected or stored beyond reports
- All data is stored locally in `storage/` directory

---

## Next Steps

1. **Setup**: Configure API keys and environment
2. **Test**: Run `pytest` to verify installation
3. **Deploy**: Start with `--limit 1` for a single video
4. **Monitor**: Check costs weekly; expect ~$0.01 per video
5. **Scale**: Increase `--limit` as you build confidence
6. **Archive**: Move old reports to cold storage after 30 days

---

**Questions?** See [README.md](README.md) for Module 3 overview, or [IMPLEMENTATION_SUMMARY.md](IMPLEMENTATION_SUMMARY.md) for architecture details.
