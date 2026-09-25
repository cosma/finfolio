# Phase 0 Research: Transcript Summarization Module

**Date**: 2026-09-25 | **Status**: Complete

## LangChain Summarization Chain Pattern

**Question**: How should we structure a LangChain chain to extract both a summary and structured claims from a transcript?

**Decision**: Use `LangChain RunnableSequence` with:
1. Prompt template that instructs the LLM to return JSON with both `summary` and `claims` keys
2. LLM invocation via `ChatAnthropic` (langchain-anthropic)
3. `JsonOutputParser` to parse structured output
4. Pydantic model validation as a fallback

**Rationale**: 
- LangChain's `JsonOutputParser` handles JSON extraction safely
- Pydantic validation catches malformed output before storage
- RunnableSequence is composable and testable
- Aligns with Constitution Principle VII (LangChain abstraction)

**Alternatives Considered**:
- Direct Claude API calls: ❌ Violates Constitution Principle VII (must use LangChain abstraction)
- Langchain `StructuredOutputParser`: ❌ Deprecated in recent LangChain versions
- Custom regex parsing: ❌ Fragile and error-prone; Pydantic validation is more robust

---

## Cost Monitoring Pattern

**Question**: How should we log cost per LLM call without manual token counting?

**Decision**: 
1. `ChatAnthropic` from langchain-anthropic automatically returns `usage_metadata` in each call response
2. Calculate cost using published Haiku rates (input/output tokens × rate per 1M tokens)
3. Log structured JSON to stdout (following existing finfolio pattern)
4. Track cumulative cost across batch runs

**Rationale**:
- langchain-anthropic exposes token counts in response metadata
- No external API needed to track cost (Anthropic API response includes `usage_metadata`)
- Stdout logging is already established in `storage.py` and `cli.py`
- Enables cost reporting per transcript and per run

**Alternatives Considered**:
- Polling Anthropic billing API: ❌ Not real-time; costs are reported daily
- Manual token estimation: ❌ Inaccurate; actual tokenization differs from estimates
- Silent cost logging (no output): ❌ Violates Constitution Principle VII requirement for observability

---

## Transcript Truncation Strategy

**Question**: How to handle transcripts that exceed Haiku's context window (~100k tokens)?

**Decision**: 
1. Estimate transcript token count using `tiktoken` (OpenAI's tokenizer; conservative estimate)
2. If estimate exceeds 85k tokens (85% of limit, safety margin): truncate to first 75% of transcript
3. Log warning: `"transcript_truncated", video_id, original_tokens, truncated_tokens`
4. Proceed with truncated transcript; downstream fact-checking still processes available claims

**Rationale**:
- `tiktoken` is lightweight and accurate for this model family
- 85% threshold provides safety margin; Haiku's actual limit is ~100k but context varies
- Truncating front-loaded (start of transcript) preserves intro/key claims
- Better to have partial results than to fail completely
- User is informed via warning log entry

**Alternatives Considered**:
- Reject entirely: ❌ User must manually chunk; blocks pipeline
- Chunk and batch: ❌ Requires multiple API calls per transcript; increases cost and complexity
- Stream processing: ❌ LangChain chains are not designed for streaming large inputs

---

## Sponsored Content Filtering

**Question**: How accurate can we detect sponsored segments for filtering?

**Decision**:
1. Use LLM itself to identify and exclude sponsored content in the prompt
2. Instruct: "Exclude any sections where the host advertises or promotes a product/service (sections containing phrases like 'brought to you by', 'sponsored by', 'partner', 'affiliate link')"
3. No separate ML model or heuristic patterns needed
4. Log when sponsored content is detected (diagnostic info only; doesn't fail the run)

**Rationale**:
- LLM has semantic understanding of advertising language; regex patterns are fragile
- Spec FR-008 goal is to exclude ads; the prompt instruction achieves this
- No separate database of sponsor patterns needed
- Keeps architecture simple and maintainable

**Alternatives Considered**:
- Hardcoded regex patterns: ❌ High false-negative rate (sponsors use varied language)
- External ad-detection service: ❌ Additional dependency and latency; overkill for this use case
- Post-processing filtering: ❌ Harder to tell LLM to exclude from the start; would require re-summarization

---

## Immutability & Idempotency

**Question**: How to enforce immutability while supporting re-runs?

**Decision**:
1. Check `storage/summaries/{video_id}.json` at start of summarization
2. If file exists: skip immediately (idempotent)
3. If file corrupted (invalid JSON): log error, mark video as failed, continue batch
4. If user wants to regenerate: they manually delete the summary file, then re-run

**Rationale**:
- Simple check-exists logic is race-condition safe (atomic filesystem operations)
- Immutability prevents accidental overwrites of verified output
- Manual deletion is explicit and intentional (no silent regeneration)
- Aligns with spec requirement FR-016

**Alternatives Considered**:
- Version summaries with timestamps: ❌ Violates immutability principle
- Regenerate on re-run if transcript changed: ❌ Requires diff tracking; violates immutability
- Flag-based regeneration (--force): ❌ Spec explicitly forbids automatic updates

---

## Configuration: Model + Cost Monitoring

**Question**: Where should LLM model and cost tracking config live?

**Decision**:
1. **Model selection**: Read from env var `FINFOLIO_LLM_MODEL`, default to `claude-haiku-4-5-20251001`
2. **Cost tracking**: Built-in to summarizer; always logs cost to stdout
3. Configuration lives in `.env` (follow project pattern)
4. No separate config file needed for this feature

**Rationale**:
- Env vars are already used (see `.env.example`)
- Model as config enables swapping for testing/upgrades without code change
- Cost logging is always-on; no toggle needed
- Keeps implementation minimal and follows Constitution Principle VII

**Alternatives Considered**:
- Per-channel model selection in channels.yaml: ❌ Overengineering; assume uniform model across batch
- Separate summarization config file: ❌ Adds configuration burden; env var is sufficient

---

## Pydantic Output Schema

**Question**: Should we use Pydantic models for validation?

**Decision**: Yes. Define schema in `finfolio/summarizer_schema.py`:
- `Claim` model: type (Enum), claim (str), quote (str), source_timestamp (Optional[str]), confidence_score (Optional[float])
- `SummaryOutput` model: summary (str), claims (list[Claim]), metadata (dict)
- Validate every output before writing to disk (FR-014)

**Rationale**:
- Pydantic provides runtime validation and type safety
- Clear contract for downstream module (module 3 fact-checking)
- Fails fast if LLM output is malformed (easier to debug than silent corruption)
- JSON schema can be generated from Pydantic model

**Alternatives Considered**:
- Ad-hoc dict validation: ❌ Fragile; hard to maintain
- No validation: ❌ Violates FR-014 and principle of data integrity

