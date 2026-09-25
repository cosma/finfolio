# Phase 0: Research & Discovery

**Date**: 2026-09-25 | **Branch**: `003-fact-checking-module`

## R-001: Web Search Provider Selection

**Decision**: Tavily API

**Rationale**:
- Purpose-built for AI agents; LangChain integration is first-class and well-documented
- Generous free tier sufficient for MVP (50 queries/month free, paid scale at $2-50/month)
- Returns structured results (title, URL, source, snippet) suitable for verdict assignment
- Supports search filtering and time-based queries (useful for dating claims)
- Cost is observable and low compared to Google Custom Search quota pricing
- Easier setup than Google Custom Search (no custom search engine ID required)

**Alternatives Considered**:
- **Google Custom Search**: Official, reliable, but requires custom search engine ID and API key setup; limited free quota (100/day); more expensive at scale
- **SerpAPI**: Reliable, clear docs, but less purpose-built for agents; requires API key; no structured agent integration in LangChain
- **Self-hosted SearXNG**: Reduces API costs but adds operational burden; requires hosting and maintenance on constrained VM

**Integration Path**:
- Use LangChain's `TavilySearchResults` tool directly
- Configure Tavily API key from environment variable
- Wrap in LangChain agent for verdict reasoning

---

## R-002: LangChain Abstraction & LLM Configuration

**Decision**: LangChain with Claude Haiku via LangChain ChatAnthropic

**Rationale**:
- Principle VII mandates LangChain abstraction for all LLM interactions
- Enables cost monitoring and seamless model switching (config-only, not code)
- Claude Haiku is cheap and deterministic (temperature=0 for fact-checking)
- LangChain provides tool-use orchestration (search + reasoning in single agent)

**Implementation Pattern**:
```python
# Config-based model selection
MODEL = os.getenv("FINFOLIO_LLM_MODEL", "claude-haiku-4-5-20251001")
llm = ChatAnthropic(
    model=MODEL,
    temperature=0,  # deterministic fact-checking
    api_key=os.getenv("ANTHROPIC_API_KEY")
)

# Tool-use agent
tools = [TavilySearchResults(...)]
agent = create_tool_calling_agent(llm, tools, prompt)
```

**Temperature Setting**:
- Fact-checking: `temperature=0` (per Constitution VII)
- Deterministic output ensures same input always produces same verdict
- Reduces hallucination risk when reasoning about search results

**Cost Monitoring**:
- LangChain callbacks capture token usage per call
- Log to structured JSON: model, tokens_in, tokens_out, cost_usd
- Aggregate per-run and per-video for cost visibility

---

## R-003: Verdict Assignment Logic

**Decision**: LLM-driven verdict synthesis with structured parsing

**Rationale**:
- Claims vary in specificity (stock price, deal announcement, analyst opinion)
- Manual rule-based classification insufficient (would need domain expertise rules)
- LLM with search results can reason across claims and sources
- Structured output (Pydantic model) ensures consistent schema

**Verdict Categories**:
- **True**: Claim supported by one or more independent sources; no contradictions
- **Partially supported/overstated**: Claim core is accurate but details or emphasis are exaggerated (e.g., "stock up 20%" vs. "stock up 5%")
- **Unverified**: No search results found; search timed out; sources inconclusive
- **False**: Claim contradicted by multiple independent sources

**LLM Prompt Structure**:
1. Present claim text and extracted quote
2. Provide search results (snippet + URL)
3. Ask LLM to assign verdict + note (1-2 sentences)
4. Parse structured output via Pydantic

**Handling Ambiguity**:
- If search results are sparse, favor "Unverified" over "False"
- If sources conflict, note contradiction in verdict note and mark "Partially supported"
- Opinion/forecast claims: skip fact-checking, mark as "Opinion" in report

---

## R-004: Per-Claim Resumability & Incremental Persistence

**Decision**: Per-claim in shared report file with atomic writes

**Rationale**:
- Save each verdict to the final report file as it completes
- Resume by reading already-completed verdicts from report
- Simpler than checkpoint files; uses single source of truth
- Atomic writes via .tmp pattern (inherited from Module 2) prevent partial corruption

**Implementation Pattern**:
```python
# Load existing verdicts from report (if partial)
verdicts = load_report_verdicts(video_id) or {}

# Process claims not yet in verdicts
for claim in claims:
    if claim['id'] not in verdicts:
        verdict = fact_check_claim(claim)
        verdicts[claim['id']] = verdict
        # Save atomically
        save_report_atomically(video_id, build_report(verdicts))
```

**Edge Cases Handled**:
- If search times out on claim #6, verdicts 1-5 are already saved
- Next run skips 1-5, retries 6+
- Concurrent runs: atomic writes prevent race conditions

**Error Recovery**:
- Network error → save partial verdicts, exit gracefully
- API quota exhausted → mark remaining as "Unverified", save, exit
- Malformed claim → log error, continue to next claim

---

## R-005: Report Schema & Backward Compatibility

**Decision**: Structured JSON report with metadata and per-claim verdicts

**Rationale**:
- Inherit summary metadata from input (video_id, title, transcript_source)
- Add fact-checking metadata (timestamp, search_provider, cost)
- Per-claim verdict structure includes source URL and publication date
- Future-proof for aggregation (Module 4) and trend analysis

**Schema Baseline**:
```json
{
  "video_id": "...",
  "title": "...",
  "source_url": "...",
  "summary": { ... },  // inherited from Module 2
  "fact_checked_at": "2026-09-25T12:00:00Z",
  "search_provider": "Tavily",
  "cost_usd": 0.05,
  "verdicts": [
    {
      "claim_id": "...",
      "claim_text": "...",
      "verdict": "True|Partially supported|Unverified|False",
      "note": "...",
      "source_url": "...",
      "source_title": "...",
      "source_date": "2026-09-24",
      "search_query": "...",
      "searched_at": "2026-09-25T12:00:00Z"
    }
  ],
  "disclaimer": "FinFolio reports facts and their accuracy. This is not financial advice."
}
```

---

## R-006: CLI Command Structure

**Decision**: Single command `finfolio factcheck` with batch processing

**Rationale**:
- Simple entry point for integration into scheduled workflows
- Batch processing all pending summaries in one run
- Progress logging (videos processed, claims verified, errors)

**CLI Interface**:
```bash
finfolio factcheck [--limit N] [--video-id ID] [--verbose]
```

**Options**:
- `--limit N`: Process max N videos (useful for testing)
- `--video-id ID`: Process single video (for debugging)
- `--verbose`: Log search queries and LLM reasoning

**Output**:
```
Processing 3 pending summaries...
video_001: 15 claims → 15 verdicts (1 False, 5 Partially supported, 9 Unverified) [cost: $0.03]
video_002: 12 claims → 10 verdicts, 2 errors (retryable) [cost: $0.02]
video_003: skipped (already has report)
---
Total: 2 processed, 27 claims verified, 2 errors
Cost: $0.05
Done.
```

---

## R-007: Testing Strategy

**Decision**: Test-first (Red-Green-Refactor per Constitution)

**Test Coverage**:

1. **Unit Tests** (verdict logic):
   - Test LLM prompt generation with mock search results
   - Test Pydantic schema validation
   - Test edge cases (empty results, conflicting sources, opinion claims)

2. **Integration Tests** (with real search):
   - Test Tavily API integration (single query)
   - Test report file I/O and atomic writes
   - Test resumability (partial report + retry)

3. **Contract Tests** (report schema):
   - Validate report structure matches schema
   - Verify disclaimer present
   - Check cost tracking logged

4. **CLI Tests**:
   - Test command parsing
   - Test batch processing with fixtures
   - Test idempotency (second run skips completed videos)

---

## Summary of Decisions

| Research Area | Decision | Key Constraint |
|---------------|----------|-----------------|
| Search Provider | Tavily | LangChain integration, low cost |
| LLM Abstraction | LangChain + Claude Haiku | Config-only model switching (Principle VII) |
| Temperature | 0 (fact-checking) | Deterministic verdicts (Principle VII) |
| Resumability | Per-claim in shared file | Atomic .tmp writes for safety |
| Report Schema | Structured JSON with metadata | Backward-compatible with summaries |
| CLI | `finfolio factcheck` batch | Simple integration into workflows |
| Testing | Test-first (pytest) | Constitution-driven test cases |

---

**Phase 0 Complete**: All NEEDS CLARIFICATION resolved. Ready for Phase 1 design.
