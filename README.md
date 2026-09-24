# FinFolio
Fact-checks for finance content




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
# Install dependencies
pip install -r requirements.txt

# Or install in editable mode with dev dependencies
pip install -e ".[dev]"
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
# Run fetch command
finfolio fetch

# Use custom config file
finfolio fetch --config /path/to/channels.yaml

# Show help
finfolio fetch --help
```

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
pytest tests/ -v

# Run only unit tests
pytest tests/unit/ -v

# Run with coverage
pytest tests/ --cov=finfolio --cov-report=html

# Run specific test
pytest tests/unit/test_storage.py::TestStorage::test_save_transcript_writes_file -v
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
- `1` — General error (config, API auth, YAML parse error)
- `2` — Another fetch is already running (lock file exists)

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
ruff check finfolio/ tests/

# Type checking
mypy finfolio/

# Format code
ruff format finfolio/ tests/
```