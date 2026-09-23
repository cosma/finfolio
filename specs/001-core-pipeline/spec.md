# FinFolio Core Pipeline Specification

## Feature Summary

Build FinFolio, a Python backend pipeline and web UI that monitors approximately 10 YouTube financial/investment advisor channels for new videos, automatically extracts and fact-checks their claims against independent sources, and presents findings in searchable per-video and weekly digest reports.

The system separates factual claims from opinions/forecasts, assigns verdicts to each claim (True / Partially Supported / Unverified / False) with sources, discloses monetization incentives, and tracks all LLM interactions for cost and audit purposes. A relational database maintains a processing memory to avoid reprocessing videos and a vector search index for content discovery.

## User Scenarios

### Scenario 1: Monitor New Content
**Actor**: FinFolio system (scheduled daily)
- System checks each of ~10 configured channels for new videos using YouTube Data API v3 search endpoint
- For each new video: fetches caption track via API, stores raw transcript, schedules for LLM processing
- Updates processing status (pending → processing → completed or failed)
- Returns: count of new videos found, URLs for each

### Scenario 2: Summarize & Extract Claims
**Actor**: LLM worker (for each transcript)
- Receives raw transcript from database
- Sends to LLM (Haiku via LangChain, temperature=0.3) with prompt: "Summarize this video and extract all checkable factual claims (numbers, dates, named deals, company/product facts) separately from opinions and forecasts."
- Receives structured response: (a) plain-language summary, (b) list of discrete claims, (c) list of stated opinions/forecasts
- Stores result with LLM metadata (model used, tokens consumed, cost incurred)
- Updates processing status (processing → claims_extracted)

### Scenario 3: Fact-Check Each Claim
**Actor**: Fact-checking worker (for each extracted claim)
- Receives claim from database
- Searches web against independent, primary sources
- Assigns verdict: True / Partially Supported (claim overstated or incomplete) / Unverified (no sources found) / False
- Records supporting evidence: URL(s), brief note explaining verdict
- Sends claim + verdict + sources to LLM (Haiku, temperature=0) for consistency check if ambiguous
- Stores verdict with LLM metadata if LLM was consulted
- Updates processing status (claims_extracted → fact_checked)

### Scenario 4: Generate Per-Video Report
**Actor**: Report generator (once all claims for a video are fact-checked)
- Assembles: video ID, channel, published date, summary, fact-check table (claim | verdict | note | source)
- Calculates: (a) accuracy score for hard facts (% of True + Partially Supported), (b) monetization disclosure (present/absent + description)
- Generates HTML/JSON report, stores in database
- Updates processing status (fact_checked → report_generated)

### Scenario 5: View Weekly Digest
**Actor**: End user
- UI displays weekly aggregation: all per-video reports from the past 7 days, summarized by channel
- Shows: video count, aggregate accuracy rate, most common verdict distribution, new monetization disclosures
- Allows filtering by channel, date range, verdict (e.g., all videos with ≥1 False claim)

### Scenario 6: Search Reports
**Actor**: End user
- UI provides vector search: user enters a topic/keyword
- Database returns matching videos using vector index (semantic search across summaries and claims)
- Alternative: user filters by channel, date range, accuracy threshold
- UI displays search results with snippets and links to full reports

## Functional Requirements

### F1: Channel Monitoring
- System maintains a configurable list of ~10 YouTube channels (stored in config or database)
- Daily scheduled task queries YouTube Data API v3 `search().list` endpoint for each channel with:
  - `q=<channel_handle>`, `type=video`, `maxResults=50`, `order=date`, `publishedAfter=<yesterday>`, etc.
  - Configurable publish date window (default: past 24 hours)
- For each new video detected (not in processing memory):
  - Fetch caption track via API `captions().list` → `captions().download`
  - Store raw transcript in database with: video_id, channel_id, title, published_date, transcript_text
  - Create processing record with status: `pending`
- Return: list of new video URLs, counts per channel, any API errors

### F2: Transcript Storage & Memory
- Relational database table `videos`: video_id (PK), channel_id, title, published_date, transcript_text, source_url
- Table `processing_status`: video_id (FK), status (pending / processing / claims_extracted / fact_checked / report_generated / failed), status_updated_at, error_message (if failed)
- Table `llm_calls`: video_id, call_type (summarization / fact_checking), model, tokens_input, tokens_output, cost_estimated, created_at
- Memory check: before processing a video, check `videos` table for existing entry by video_id; if found and status is completed, skip it
- Return: confirmation of storage, transcript_id for downstream processing

### F3: Summarization & Claim Extraction
- Input: transcript_id, raw_transcript
- Call LLM via LangChain abstraction with:
  - Model: Haiku (configurable)
  - Temperature: 0.3
  - Prompt: structured, requesting plain summary + discrete factual claims + opinions/forecasts (separated)
- Parse LLM response into:
  - `summary`: plain-language text (200–500 words)
  - `claims`: list of objects { claim_text, claim_type: "fact", original_source: "timestamp in transcript" }
  - `opinions`: list of objects { opinion_text, opinion_type: "opinion/forecast" }
- Store results in database table `claims`: video_id, claim_text, claim_type, opinions_list, extraction_timestamp
- Log LLM call: model, tokens, cost to `llm_calls` table
- Update `processing_status` to `claims_extracted`
- Return: count of claims extracted, count of opinions/forecasts identified, any parsing errors

### F4: Fact-Checking
- Input: claim_id, claim_text
- Primary method: web search against independent sources (Google Search API, news APIs, financial databases)
  - Search for claim using claim_text or key terms extracted from it
  - Evaluate top N results (configurable, default 5) for relevance and authority
  - Assign preliminary verdict: True / Partially Supported / Unverified / False
- If verdict is ambiguous (conflicting sources or marginal evidence):
  - Send claim + preliminary evidence to LLM via LangChain:
    - Model: Haiku, Temperature: 0
    - Prompt: "Given these sources, is this claim True, Partially Supported, Unverified, or False?"
  - Use LLM response to finalize verdict
  - Log LLM call to `llm_calls`
- Store result in database table `fact_checks`: claim_id, verdict (enum), source_urls (array), note_text, llm_consulted (bool), created_at
- Update `processing_status` to `fact_checked`
- Return: verdict, sources, note, LLM metadata (if consulted)

### F5: Per-Video Report Generation
- Input: video_id (with all claims fact-checked)
- Assemble report:
  - Metadata: video_id, channel, title, published_date, summary
  - Fact-check table: claim | verdict | note | source_urls
  - Accuracy calculation: (# True + # Partially Supported) / (total hard facts) × 100%
  - Monetization disclosure: yes/no + description (extracted from summary or claims)
  - Overall assessment: structured summary of hard facts accuracy + monetization disclosure + key findings
- Store report in database table `reports`: video_id, report_json, report_html, accuracy_score, monetization_disclosed, generated_at
- Store report as searchable text in vector index (for semantic search)
- Update `processing_status` to `report_generated`
- Return: report_id, URL for accessing report via UI

### F6: Weekly Digest
- Input: date range (default: past 7 days)
- Query `reports` table for all reports generated in date range
- Aggregate:
  - By channel: video count, average accuracy, verdict distribution (count of True / Partially Supported / Unverified / False across all claims)
  - Monetization summary: list of videos disclosing monetization
- Generate weekly digest: markdown or HTML document containing aggregated stats + links to all per-video reports
- Store digest in database table `digests`: week_start_date, digest_json, digest_html, generated_at
- Return: digest_id, URL for accessing digest via UI

### F7: Vector Search & Filtering
- Database: populate vector index (e.g., PostgreSQL pgvector) with embeddings for:
  - Each report's summary text
  - Each claim text
- Vector search: user enters query → system generates embedding → retrieves top N results by semantic similarity
- Filtering: by channel, date range, verdict, accuracy threshold
- Return: ranked list of reports/claims matching query, with snippets

### F8: Frontend UI
- Dashboard: display latest weekly digest, quick stats (channels monitored, videos processed this week, overall accuracy rate)
- Per-video report page: video metadata, summary, fact-check table, accuracy score, monetization disclosure, accuracy breakdown (by verdict)
- Weekly digest page: aggregated stats, links to all reports from the week
- Search interface: text search box + optional filters (channel, date, verdict, accuracy)
- Report list: paginated/sortable list of all reports, filterable by date, channel, accuracy
- Responsive design (mobile + desktop)

### F9: Processing Statuses
- Required statuses:
  - `pending`: video transcript fetched, awaiting summarization + claim extraction
  - `processing`: LLM is currently working on summarization/extraction or fact-checking
  - `claims_extracted`: summarization complete, facts and opinions identified, awaiting fact-checking
  - `fact_checked`: all claims have verdicts, awaiting report generation
  - `report_generated`: report assembled and stored, processing complete
  - `failed`: error occurred (transcript fetch failed, LLM error, fact-checking error, etc.)
- Each status transition logs a timestamp and, if applicable, error details
- UI allows manual retry of failed videos

### F10: LLM Cost Tracking
- Log every LLM call to `llm_calls` table with:
  - model (e.g., "claude-haiku-4-5-20251001")
  - tokens_input, tokens_output (from LLM response metadata)
  - cost_estimated (calculated from token usage × model pricing)
  - call_type ("summarization" or "fact_checking")
  - video_id, created_at
- Dashboard endpoint: returns cumulative cost for current month, cost per call_type, tokens used, LLM model breakdown
- Alert threshold: if monthly cost exceeds configured limit (default: $20), log warning and notify admin

## Key Entities

### Video
- video_id (YouTube video ID, PK)
- channel_id (YouTube channel ID)
- title
- published_date (ISO 8601)
- transcript_text (raw captions)
- source_url (link to YouTube video)
- created_at

### ProcessingStatus
- video_id (FK to Video)
- status (enum: pending, processing, claims_extracted, fact_checked, report_generated, failed)
- updated_at
- error_message (nullable)

### Claim
- claim_id (PK, UUID)
- video_id (FK)
- claim_text
- claim_type (enum: fact, opinion, forecast)
- extraction_timestamp

### FactCheck
- fact_check_id (PK, UUID)
- claim_id (FK)
- verdict (enum: True, Partially Supported, Unverified, False)
- source_urls (array/JSON)
- note_text
- llm_consulted (boolean)
- created_at

### Report
- report_id (PK, UUID)
- video_id (FK)
- report_json (structured data)
- report_html (rendered HTML)
- accuracy_score (float 0–100)
- monetization_disclosed (boolean)
- generated_at

### LLMCall
- llm_call_id (PK, UUID)
- video_id (FK, nullable for non-video calls)
- call_type (summarization, fact_checking, other)
- model (string)
- tokens_input, tokens_output (integers)
- cost_estimated (float)
- created_at

### Digest
- digest_id (PK, UUID)
- week_start_date (ISO 8601)
- digest_json (aggregated stats + links)
- digest_html (rendered HTML)
- generated_at

## Success Criteria

1. **Video Coverage**: System processes 2–3 new videos per monitored channel per week (~20–30 videos/week across 10 channels) without missed videos or duplicates.

2. **Processing Speed**: Per-video processing (from transcript fetch to report generation) completes within 2 hours for 95% of videos.

3. **Fact-Check Accuracy**: Fact-checking verdicts match independent review by a human auditor in ≥90% of cases (validated on sample of 20+ videos).

4. **LLM Cost Control**: Total LLM spend remains within $10–20/month at current operational scale.

5. **Data Integrity**: All videos processed are recorded in database; no video is processed twice (deduplication via processing_status check).

6. **Search Performance**: Vector search and keyword filtering return results in <2 seconds for typical queries.

7. **UI Usability**: End user can find, read, and compare fact-checks for any monitored video within 3 interactions (search → filter → open report).

8. **Monetization Disclosure**: System correctly identifies and flags ≥95% of videos where monetization is mentioned in transcripts.

## Output

Reports are stored in the database and browsable through a lightweight web UI, showing:
- **Weekly digest**: aggregated statistics for all monitored channels from the past 7 days (video count, aggregate accuracy rate, verdict distribution, monetization disclosures)
- **Per-video fact-check reports**: individual report for each processed video containing:
  - Video metadata: channel, title, published date, YouTube link
  - Summary: plain-language overview of video content
  - Fact-check table: claim | verdict | source URL(s) | note
  - Accuracy breakdown: % of claims that are True / Partially Supported / Unverified / False
  - Monetization disclosure: yes/no + description
  - Processing metadata: LLM model(s) used, token count, processing date/time
- **Search and filtering**: vector search by topic + filters by channel, date range, verdict, accuracy threshold
- **Cost dashboard**: cumulative LLM spend for current month, breakdown by call type (summarization vs. fact-checking)

All reports are updated in real-time as new videos are processed and facts are verified.

## Assumptions

- YouTube Data API v3 credentials and quota are configured (10,000 units/day sufficient for ~100 videos/week)
- Captions are available for all monitored videos (if captions unavailable for a video, mark as failed with reason "no_captions_available")
- LLM (Haiku via LangChain) is accessible and responsive (configured via environment variables)
- Web search for fact-checking is via a configurable search API (Google Custom Search, Bing, or similar; not implemented in v1 scope, assume external service)
- Database (PostgreSQL or similar) is available with pgvector extension for vector search
- "Independent, primary sources" means: government data, academic papers, verified news outlets, official corporate filings, not social media or unverified blogs
- Monetization disclosure means: any mention of paid courses, apps, affiliate links, sponsorships, or other revenue streams the advisor benefits from

## Out of Scope (v1)

- Investment recommendations of any kind
- Trading signals or buy/sell alerts
- Real-time or sub-daily monitoring (daily check is sufficient for v1)
- Video platforms other than YouTube
- Multi-language support (English only for v1)
- Interactive debate or comment moderation
- Alert/notification system for users (reports are pull-only via UI)
- Advanced analytics or pattern detection across channels
- ML-based claim extraction (using LLM-based summarization, not training custom ML)

## Acceptance Scenarios

### Scenario A: Happy Path — New Video Processed End-to-End
1. System detects new video on monitored channel
2. Fetches transcript successfully
3. LLM summarizes and extracts 5–10 factual claims
4. Fact-checker assigns verdicts to all claims (mix of True, Partially Supported, False)
5. Per-video report is generated with accuracy score
6. Report is searchable via UI

**Acceptance**: Report appears in UI within 2 hours, all claims have verdicts, accuracy score calculated correctly.

### Scenario B: Monetization Disclosure Detected
1. Video transcript mentions "my paid course" or affiliate link
2. LLM extracts mention during summarization
3. Report flags monetization_disclosed = true with description
4. Report visible in weekly digest under "monetization disclosures"

**Acceptance**: Monetization disclosure appears in report and digest without false negatives.

### Scenario C: Ambiguous Claim Resolved via LLM
1. Claim: "Stock XYZ is up 50% this year"
2. Web search finds conflicting data (up 48% vs. up 52%)
3. System sends claim + sources to LLM for verdict
4. LLM responds: "Partially Supported (claim slightly overstated)"
5. Verdict recorded with LLM metadata

**Acceptance**: LLM call is logged with model, tokens, cost; verdict is reasonable given sources.

### Scenario D: Search by Topic
1. User enters "interest rates" in search box
2. UI returns all reports with claims mentioning interest rates (via vector search)
3. User filters by date range (past month) and channel
4. Report snippets are displayed with highlighted matching text

**Acceptance**: Search returns relevant results within 2 seconds; filtering works correctly.

### Scenario E: Cost Monitoring Alert
1. System accumulates 100 LLM calls over the month (50 summarizations, 50 fact-checks)
2. Monthly cost calculated from logged tokens: $18.50
3. Dashboard displays: "$18.50 this month (within budget)" and breakdown by call_type
4. No alert triggered (under $20 limit)

**Acceptance**: Cost tracking is accurate; alert fires if limit is exceeded.
