# FinFolio
Fact-checks for finance content

## Quick Start

FinFolio automatically discovers and transcribes new videos from configured YouTube financial channels, with MM:SS timestamps for fact-checking verification.

### Setup (5 minutes)

```bash
# 1. Install dependencies with uv
uv sync

# 2. Get a YouTube API key
#    Go to: https://console.cloud.google.com
#    → APIs & Services → Credentials → Create API Key

# 3. Set your API key
export YOUTUBE_API_KEY=your-api-key-here

# 4. Edit channels.yaml with YouTube financial channels to monitor
#    Format:
#    channels:
#      - channel_id: UCxxxxx
#        display_name: "Channel Name"

# 5. Run the fetch
uv run finfolio fetch
```

### What Happens

```bash
$ uv run finfolio fetch
{"timestamp": "2026-09-24T...", "event": "fetch_start", "status": "success"}
{"timestamp": "2026-09-24T...", "event": "fetch_channel", "status": "success", "new_videos": 2}
{"timestamp": "2026-09-24T...", "event": "download_transcript", "status": "success", "video_id": "dQw4w9WgXcQ"}
...
```

Transcripts are saved to `storage/transcripts/{video_id}.txt` with MM:SS timestamps:

```
00:00 Welcome to this video on investment strategies.
00:15 Today we'll discuss three key principles.
02:30 Many investors make the mistake of over-concentrating.
```

Fact-checkers can construct YouTube jump-links: `youtu.be/{video_id}?t=150` to verify claims directly in the video.

### Testing

```bash
# Run all tests (uses mocked API, no key needed)
uv run pytest tests/ -v

# Run unit tests only
uv run pytest tests/unit/ -v
```

---

### Spec Kit 

```bash
specify init project --integration claude --force #use  --force for already existing directory
```

1. Go to the project folder: `cd project`
2. Start Claude in this project directory; spec-kit skills were installed to `.claude/skills`   
3. Start using skills with your coding agent:                                                 
   3.1 `/speckit-constitution` - Establish project principles                                   
   3.2 `/speckit-specify` - Create baseline specification                                       
   3.3 `/speckit-plan` - Create implementation plan                                             
   3.4 `/speckit-tasks` - Generate actionable tasks                                             
   3.5 `/speckit-implement` - Execute implementation                                            
   3.6 `/speckit-converge` - Assess the codebase and append remaining work as tasks 

#### Spec Kit Skills Workflow

These 6 core skills form a **spec-driven development loop**:

**1. `/speckit-constitution`** — Establishes project principles & governance
- Creates `.specify/memory/constitution.md` — your project's non-negotiable rules, principles, and governance
- Source of truth that all downstream artifacts must comply with
- For FinFolio: 7 core principles (accuracy, no financial advice, facts vs. forecasts, transparency, monetization awareness, official APIs, resource discipline)
- Updated rarely (only on major principle changes)

**2. `/speckit-specify`** — Creates baseline feature specification
- Produces `specs/<feature>/spec.md` — **"what are we building?"** document
- Includes feature description, user stories, acceptance criteria, edge cases, non-functional requirements
- Does NOT include implementation details (no tech stack, file names, code structure)
- Validated against constitution principles

**3. `/speckit-plan`** — Designs the implementation architecture
- Produces design artifacts: `research.md`, `data-model.md`, `contracts/`, `quickstart.md`
- Includes architecture, file structure, tech choices, API specs, integration guide
- Checked against constitution constraints (Haiku default, lean dependencies, official APIs only)

**4. `/speckit-tasks`** — Breaks the plan into executable tasks
- Produces `specs/<feature>/tasks.md` — ordered, dependency-aware checklist
- Each task is small enough to implement in one sitting
- Marked with IDs, parallel/sequential flags, dependencies, test-first ordering

**5. `/speckit-implement`** — Executes the tasks
- Reads `tasks.md` and writes the code
- Creates/updates source files, runs tests, marks tasks complete
- Handles project setup (`.gitignore`, env files, dependencies)
- Requires all checklists to pass before starting

**6. `/speckit-converge`** — Fills the gap between plan and reality
- Diffs your actual codebase against spec/plan/tasks
- Finds unbuilt work and appends it back to `tasks.md`
- Detects unexpected code (tech debt, exploration) not in the spec

**The Loop**:
```
constitution (principles, once)
      ↓
   spec (what to build)
      ↓
   plan (how to build it)
      ↓
   tasks (ordered checklist)
      ↓
 implement (write the code)
      ↓
  converge (find gaps)
      └→ (append more tasks if needed)
         └→ implement (finish)
```

Each stage **validates against the previous** (spec checks constitution, plan checks constitution & spec, tasks checks plan, etc.). This prevents drift and ensures FinFolio's constitution principles are enforced throughout development.

**Optional skills that you can use for your specs (improve quality & confidence)**
                                                                                         
- `/speckit-clarify` (optional) - Ask structured questions to de-risk ambiguous areas before planning (run before `/speckit-plan` if used)    
- `/speckit-analyze` (optional) - Cross-artifact consistency & alignment report (after `/speckit-tasks`, before `/speckit-implement`)
- `/speckit-checklist` (optional) - Generate quality checklists to validate requirements completeness, clarity, and consistency (after `/speckit-plan`)

---

## YouTube Transcript Fetch Module

The `finfolio fetch` command automatically discovers new videos from configured YouTube financial channels and downloads their transcripts via the official YouTube Data API v3.

### Installation

```bash
# Install dependencies with uv
uv sync

# Or install in editable mode with dev dependencies
uv pip install -e ".[dev]"
```

### Configuration

#### 1. YouTube API Key

Set the `YOUTUBE_API_KEY` environment variable or create a `.env` file:

```bash
# Option A: Environment variable
export YOUTUBE_API_KEY=your-youtube-api-key-here

# Option B: .env file (copy from .env.example)
cp .env.example .env
# Edit .env and add your API key
```

Get your API key from [Google Cloud Console](https://console.cloud.google.com/apis/dashboard).

#### 2. Channels Configuration

Create a `channels.yaml` file (or copy from `channels.yaml.example`):

```yaml
channels:
  - channel_id: "UC7_ZLN2t-U-tZ7CgzQ0OoXw"
    display_name: "Graham Stephan"
  - channel_id: "UC_x5XG1OV2P6uZZ5FSM9Ttw"
    display_name: "Two Cents"
  - channel_id: "UCF1DiS9jhNXqxPfj7pEj2lg"
    display_name: "Andrei Jikh"
```

### Usage

```bash
# Run fetch command (default: random 10-20 second delays)
finfolio fetch

# Use custom config file
finfolio fetch --config /path/to/channels.yaml

# Customize random delay range (min: 5-15 seconds)
finfolio fetch --min-delay 5 --max-delay 15

# More conservative delays (10-30 seconds)
finfolio fetch --min-delay 10 --max-delay 30

# Very conservative (20-40 seconds)
finfolio fetch --min-delay 20 --max-delay 40

# Show help
finfolio fetch --help
```

**Random Delay**: By default, the system adds random delays between 10-20 seconds between each transcript fetch. This mimics human behavior and prevents YouTube from blocking your IP. The randomization makes it harder for YouTube to detect automated requests.

**Delay Options**:
- `--min-delay`: Minimum seconds to wait (default: 10)
- `--max-delay`: Maximum seconds to wait (default: 20)

If you're still getting "YouTube is blocking requests from your IP" errors, increase both values (e.g., `--min-delay 30 --max-delay 60`).

### Output

The command outputs structured JSON logs to stdout (one object per line):

```json
{"timestamp": "2026-09-24T10:15:30Z", "event": "fetch_start", "status": "success"}
{"timestamp": "2026-09-24T10:15:31Z", "event": "fetch_channel", "channel_id": "UCxxxxx", "status": "success", "new_videos": 2}
{"timestamp": "2026-09-24T10:15:45Z", "event": "download_transcript", "video_id": "dQw4w9WgXcQ", "status": "success"}
{"timestamp": "2026-09-24T10:16:00Z", "event": "fetch_complete", "status": "success", "quota_units": 87}
```

### Features

- **Video Discovery**: Automatically finds new videos from configured YouTube channels
- **Transcript Download**: Fetches raw captions via YouTube API v3
- **Idempotent**: Safe to run repeatedly; transcripts are never re-downloaded
- **Atomic Writes**: Uses `.tmp` file pattern to ensure data integrity
- **State Persistence**: Tracks last-fetch timestamp per channel for efficient incremental updates
- **Lock File**: Prevents concurrent runs with exclusive locking
- **Quota Tracking**: Logs YouTube API quota consumption per run
- **Graceful Error Handling**: Continues processing if one channel fails
- **Configuration-Driven**: Channels editable in YAML without code changes

### Architecture

```
finfolio/
├── cli.py                   # Click CLI entry point (finfolio fetch)
├── channel_monitor.py       # Video discovery via YouTube API
├── transcript_fetcher.py    # Caption download and storage
├── youtube_client.py        # YouTube API v3 wrapper
├── config.py                # YAML configuration loading
└── storage.py               # Filesystem abstraction (transcripts, state, locks)

storage/                      # Auto-created at runtime
├── transcripts/             # Raw transcript files (video_id.txt)
├── .finfolio-state.json    # Last-fetch timestamp per channel
└── .finfolio.lock          # Exclusive lock file

channels.yaml                # Channel configuration (editable)
```

### Testing

```bash
# Run all tests
uv run pytest tests/ -v

# Run only unit tests
uv run pytest tests/unit/ -v

# Run with coverage
uv run pytest tests/ --cov=finfolio --cov-report=html

# Run specific test
uv run pytest tests/unit/test_storage.py::TestStorage::test_save_transcript_writes_file -v
```

### Example Workflow

```bash
# 1. Set up environment
export YOUTUBE_API_KEY=abc123...

# 2. Edit channels.yaml with your channels

# 3. Run fetch (first time)
$ finfolio fetch
{"timestamp": "2026-09-24T10:15:30Z", "event": "fetch_start", "status": "success"}
{"timestamp": "2026-09-24T10:15:31Z", "event": "fetch_channel", "channel_id": "UC7_ZLN2t-U-tZ7CgzQ0OoXw", "status": "success", "new_videos": 3}
{"timestamp": "2026-09-24T10:15:45Z", "event": "download_transcript", "video_id": "dQw4w9WgXcQ", "status": "success"}
{"timestamp": "2026-09-24T10:16:00Z", "event": "fetch_complete", "status": "success", "quota_units": 87}

# 4. Check results
$ ls storage/transcripts/
dQw4w9WgXcQ.txt
jNQXAC9IVRw.txt
...

# 5. Run again (idempotent - no new videos, zeros new downloads)
$ finfolio fetch
{"timestamp": "2026-09-24T11:00:00Z", "event": "fetch_start", "status": "success"}
{"timestamp": "2026-09-24T11:00:01Z", "event": "fetch_channel", "channel_id": "UC7_ZLN2t-U-tZ7CgzQ0OoXw", "status": "success", "new_videos": 0}
{"timestamp": "2026-09-24T11:00:05Z", "event": "fetch_complete", "status": "success", "quota_units": 0}
```

### Exit Codes

- `0` — Success (all channels fetched, transcripts saved)
- `1` — General error (config, API auth, YAML parse error, or YouTube IP blocked)
- `2` — Another fetch is already running (lock file exists)

**IP Block Handling**: If YouTube detects "too many requests" or blocks your IP during a fetch, the system immediately stops and exits with code `1`, rather than wasting time on failed requests. You'll see:
```
{"event": "download_transcript", "status": "failed", "video_id": "...", "error": "...too many requests..."}
{"event": "fetch_failed", "status": "failed", "error": "IP_BLOCKED_BY_YOUTUBE", "message": "YouTube blocked your IP. Please wait and try again later."}
```
**What to do**: 
- Wait **1-24 hours** before running `finfolio fetch` again (YouTube auto-unblocks after this)
- Try with higher delays next time: `finfolio fetch --min-delay 30 --max-delay 60`
- Already-fetched transcripts are saved and won't be re-fetched

### Constraints & Limits

- **YouTube API Quota**: 10,000 units per day (logged per run)
- **Channels**: Tested with up to 50 channels
- **Videos**: Handles channels with 2-3 new videos per week (20-30 total/week across 10 channels)
- **Performance**: Full run on 10 channels completes in under 5 minutes

### Troubleshooting

**"YOUTUBE_API_KEY not found"**
- Set environment variable: `export YOUTUBE_API_KEY=your-key`
- Or create `.env` file with: `YOUTUBE_API_KEY=your-key`

**"Config file not found"**
- Create `channels.yaml` with channel list
- Or use: `finfolio fetch --config /path/to/channels.yaml`

**"Another fetch is running"**
- Delete `storage/.finfolio.lock` if a previous run crashed
- Or wait for the other process to complete

**"No captions available"**
- Some YouTube videos don't have captions
- The fetch command logs this and continues to next video

### Development

```bash
# Linting
uv run ruff check finfolio/ tests/

# Type checking
uv run mypy finfolio/

# Format code
uv run ruff format finfolio/ tests/
```

---

## Transcript Summarization Module

The `finfolio summarize` command processes transcripts (from `finfolio fetch`) using Claude AI to extract plain-language summaries and discrete factual claims for downstream fact-checking.

### Quick Start

```bash
# Set Anthropic API key
export ANTHROPIC_API_KEY=your-anthropic-api-key-here

# Summarize all unsummarized transcripts
uv run finfolio summarize

# Use custom batch size (limit files per run)
uv run finfolio summarize --batch-size 50
```

### What It Does

1. **Discovers pending transcripts**: Scans `storage/transcripts/` for unsummarized videos
2. **Calls Claude Haiku**: Sends each transcript to Claude via LangChain for summarization
3. **Extracts facts from opinions**: Separates verifiable claims (numbers, dates, deals) from opinions/forecasts
4. **Filters sponsored content**: Removes sections advertising products/affiliates per FinFolio Constitution
5. **Saves structured JSON**: Outputs to `storage/summaries/{video_id}.json` with summary, claims, and metadata
6. **Tracks costs**: Logs token usage and API cost per transcript

### Configuration

#### Anthropic API Key

Set the `ANTHROPIC_API_KEY` environment variable or create a `.env` file:

```bash
# Option A: Environment variable
export ANTHROPIC_API_KEY=your-anthropic-api-key-here

# Option B: .env file
cp .env.example .env
# Edit .env and add: ANTHROPIC_API_KEY=your-key
```

#### LLM Model Selection

By default, uses `claude-haiku-4-5-20251001` (cheap, fast for summarization).

Override with environment variable:

```bash
export FINFOLIO_LLM_MODEL_SUMMARIZATION=claude-opus-4-1-20250805  # More capable but slower/pricier
```

### Usage

```bash
# Summarize all pending transcripts
uv run finfolio summarize

# Summarize with custom batch size
uv run finfolio summarize --batch-size 25

# Show help
uv run finfolio summarize --help
```

### Output Format

The command outputs structured JSON logs to stdout (one object per line):

```json
{"timestamp": "2026-09-25T10:15:30Z", "event": "summarization_start", "status": "success"}
{"timestamp": "2026-09-25T10:15:35Z", "event": "transcript_processed", "video_id": "dQw4w9WgXcQ", "claims_count": 12, "cost_usd": 0.042}
{"timestamp": "2026-09-25T10:15:45Z", "event": "transcript_error", "video_id": "jNQXAC9IVRw", "error": "Transcript too short"}
{"timestamp": "2026-09-25T10:15:50Z", "event": "summarization_complete", "status": "success", "processed": 5, "errors": 1, "skipped": 2, "total_cost_usd": 0.187}
```

### Output Schema

Each summary file (`storage/summaries/{video_id}.json`) contains:

```json
{
  "summary": "Plain-language summary (150-400 words) of key investment insights from the video",
  "claims": [
    {
      "type": "number|date|deal|company-fact|product-fact",
      "claim": "The factual statement",
      "quote": "Exact text from transcript",
      "source_timestamp": "MM:SS or null",
      "confidence_score": 0.0-1.0 or null
    }
  ],
  "metadata": {
    "transcript_tokens": 2847,
    "input_tokens": 2847,
    "output_tokens": 312,
    "cost_usd": 0.042,
    "model": "claude-haiku-4-5-20251001",
    "temperature": 0.3,
    "timestamp": "2026-09-25T10:15:35Z",
    "transcript_truncated": false
  }
}
```

### Features

- **Facts vs. Opinions Separation**: Extracts only verifiable factual claims (numbers, dates, named deals); excludes opinions, forecasts, and predictions
- **Sponsored Content Filtering**: Automatically removes sections advertising products or affiliate links per Constitution Principle V
- **Structured Extraction**: Each claim includes type, quote, optional timestamp, and confidence score
- **Idempotent Processing**: Safe to run repeatedly; existing summaries are skipped (unless deleted)
- **Cost Tracking**: Logs token usage and estimated cost per transcript for budget monitoring
- **Atomic Writes**: Uses `.tmp` file pattern to ensure data integrity
- **Error Resilience**: Implements exponential backoff and retry logic for API transients (rate limits, timeouts)
- **LangChain Abstraction**: All LLM calls via LangChain + ChatAnthropic (not direct API)
- **Temperature Control**: Uses temperature=0.3 for deterministic, precise summarization per Constitution Principle VII

### Exit Codes

- `0` — Success (at least one transcript processed or skipped)
- `1` — Critical error (missing API key, no transcripts found, all transcripts failed)

### Example Workflow

```bash
# 1. Fetch transcripts from YouTube
$ uv run finfolio fetch
{"event": "fetch_complete", "status": "success", "new_videos": 5}

# 2. Summarize the transcripts
$ uv run finfolio summarize
{"event": "summarization_start", "status": "success"}
{"event": "transcript_processed", "video_id": "dQw4w9WgXcQ", "claims_count": 12, "cost_usd": 0.042}
{"event": "transcript_processed", "video_id": "jNQXAC9IVRw", "claims_count": 8, "cost_usd": 0.035}
{"event": "summarization_complete", "status": "success", "processed": 2, "errors": 0, "skipped": 3, "total_cost_usd": 0.077}

# 3. Inspect a summary
$ cat storage/summaries/dQw4w9WgXcQ.json | jq .claims
[
  {
    "type": "number",
    "claim": "Apple's stock price reached $195.42",
    "quote": "Apple closed at $195.42 today",
    "source_timestamp": "02:15",
    "confidence_score": 0.95
  },
  {
    "type": "deal",
    "claim": "Microsoft acquired Activision for $68.7 billion",
    "quote": "The Microsoft-Activision deal closed for $68.7B",
    "source_timestamp": "05:30",
    "confidence_score": 0.98
  }
]

# 4. Run again (idempotent - skip existing summaries)
$ uv run finfolio summarize
{"event": "summarization_complete", "status": "success", "processed": 0, "errors": 0, "skipped": 5, "total_cost_usd": 0.0}
```

### Cost Monitoring

Each transcript costs $0.01-0.05 USD with Haiku model. For ~20-30 videos/week:

```
Expected weekly cost: $0.20-1.50 (well within Constitutional limit)
Expected monthly cost: $0.80-6.00
```

Check total cost in final `summarization_complete` log event.

### Troubleshooting

**"ANTHROPIC_API_KEY not found"**
- Set environment variable: `export ANTHROPIC_API_KEY=your-key`
- Or add to `.env` file

**"ModuleNotFoundError: No module named 'langchain'"**
- Install dependencies: `uv sync`

**"No transcripts found"**
- Run `uv run finfolio fetch` first to download transcripts
- Check that `storage/transcripts/` contains `.txt` files

**"Transcript too short / empty"**
- Some videos may not have captions or may be too short (minimum 50 characters)
- These are logged and skipped; processing continues with next transcript

**"LLM API error after retries"**
- Check your `ANTHROPIC_API_KEY` is valid
- If rate-limited, the system automatically retries with exponential backoff (1s, 2s, 4s)
- Wait a few minutes and run again

### Testing

```bash
# Run all tests (unit + integration)
uv run pytest tests/ -v

# Run summarization tests only
uv run pytest tests/test_summarizer*.py -v

# Run with coverage
uv run pytest tests/ --cov=finfolio.summarizer --cov-report=html
```
---

## Fact-Checking Module

The `finfolio factcheck` command fact-checks extracted claims from video summaries using web search and Claude LLM.

### Installation

```bash
# Install dependencies (includes LangChain, Tavily)
uv sync
```

### Configuration

Set these environment variables (or add to `.env`):

```bash
export ANTHROPIC_API_KEY=your-anthropic-api-key
export TAVILY_API_KEY=your-tavily-api-key
export FINFOLIO_LLM_MODEL=claude-haiku-4-5-20251001  # Default (cheap)
export FINFOLIO_LOG_LEVEL=INFO
```

### Usage

```bash
# Process all pending summaries
finfolio factcheck

# Process single video
finfolio factcheck --video-id dQw4w9WgXcQ

# Limit batch size
finfolio factcheck --limit 5

# Verbose output (DEBUG logging)
finfolio factcheck --verbose
```

### Features

- **Claim Verification**: Uses Tavily web search + Claude LLM (temperature=0 for determinism)
- **Resumability**: If fact-checking fails mid-video, next run skips already-verified claims
- **Opinion Skipping**: Automatically skips opinion/forecast claims (no fact-checking applied)
- **Atomic Writes**: `.tmp` file pattern ensures crash safety
- **Idempotency**: Running twice produces identical results
- **Cost Tracking**: All search + LLM costs are logged per video
- **Error Recovery**: Timeouts, quota limits, and errors yield "Unverified" verdicts

### Output

Reports are saved to `storage/reports/videos/{video_id}.json`:

```json
{
  "video_id": "dQw4w9WgXcQ",
  "title": "Apple Q3 Earnings",
  "verdict_count": 15,
  "verdicts": [
    {
      "claim_id": "claim_001",
      "claim_text": "Apple stock closed at $195.42",
      "verdict": "True",
      "note": "Verified against Yahoo Finance",
      "source_url": "https://finance.yahoo.com/quote/AAPL",
      "source_date": "2026-09-25"
    }
  ],
  "verdict_breakdown": {
    "True": 10,
    "Partially supported/overstated": 2,
    "Unverified": 2,
    "False": 1
  },
  "cost": {"search_usd": 0.02, "llm_usd": 0.01, "total_usd": 0.03},
  "disclaimer": "FinFolio reports facts and their accuracy. This is not financial advice."
}
```

### Architecture

```
finfolio/
├── fact_checker.py              # Core fact-checking orchestrator
├── models.py                    # Pydantic schemas (Claim, Verdict, Report)
├── cli.py                       # CLI command (finfolio factcheck)
├── config.py                    # Configuration management
├── logging_utils.py             # Structured JSON logging
├── search/
│   └── tavily_client.py        # Tavily web search wrapper
└── llm/
    ├── cost_tracking.py        # LangChain cost monitoring
    └── prompts.py              # Verdict reasoning prompts
```

### Testing

```bash
# Run fact-checking tests
uv run pytest tests/unit/test_fact_checker*.py -v
uv run pytest tests/integration/test_fact_check*.py -v
uv run pytest tests/integration/test_resumability.py -v

# Full test suite
uv run pytest tests/ --cov=finfolio --cov-report=html
```

### Troubleshooting

**"TAVILY_API_KEY not set"**
- Get a key from [tavily.com](https://tavily.com/)
- Set: `export TAVILY_API_KEY=your-key`

**"No pending videos to process"**
- Run `finfolio summarize` first to create summaries
- Or use `--video-id` to process a specific video

**"Search timeout" verdicts**
- Normal for slow internet or heavy load
- Next run will retry (resumability)
- Consider increasing `FINFOLIO_SEARCH_TIMEOUT`

**"Unverified" on all claims**
- Check Tavily API key and quota
- Verify internet connection
- Run with `--verbose` to see search queries

### Cost Estimation

With Haiku model (cheap):
- Per video: $0.01-0.05 (10-30 claims)
- Per week (20 videos): $0.20-1.00
- Per month: $0.80-4.00

All costs are logged and reported per video.

---

**For complete implementation details, see:**
- `specs/003-fact-checking-module/` - Full specification
- `IMPLEMENTATION_SUMMARY.md` - Architecture decisions
