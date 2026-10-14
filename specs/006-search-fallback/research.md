# Research: Search Fallback and Claim Re-check

## 1. Free search source

- **Decision**: `ddgs` library, version 9.16.0, `DDGS().text(query, max_results=5)`.
- **Rationale**: No API key and no fixed quota. Returns `title`, `href`, `body`, which map directly to the result shape the prompt uses. Exceptions are typed (`DDGSException`, `RatelimitException`, `TimeoutException`), so failures can be caught and turned into a fallback.
- **Alternatives considered**:
  - Brave Search API: free tier with a key. The tier size is not verified, so it is not used yet.
  - Google Programmable Search: 100 queries per day, too low for 1,000+ claims a month.
  - SearXNG (self-hosted): needs a server, heavy on the 2 GB Docker VM.
  - Scraping DuckDuckGo HTML: unofficial and brittle. Rejected.

## 2. Acceptance rule

- **Decision**: accept a free-source verdict when it is not Unverified and its confidence is at least the threshold.
- **Rationale**: The model already sees the sources and states its verdict; its confidence field is the signal the spec asks for (FR-002).
- **Alternatives considered**: counting matching sources (brittle, needs claim-specific rules); a second LLM judge (more cost, same weakness).

## 3. Threshold setting

- **Decision**: `FINFOLIO_SEARCH_MIN_CONFIDENCE`, default 0.8, validated to lie in [0, 1].
- **Rationale**: Settled in clarification (FR-012). Follows the existing `FINFOLIO_*` pattern in `Config`.
- **Alternatives considered**: a constant in code (rejected in clarification); a per-run CLI flag (more surface than needed).

## 4. Failure policy

- **Decision**: `SearchError` for any paid-search failure, with `SearchQuotaError` as a subclass. The CLI stops with exit code 2 for both and prints a message that tells them apart.
- **Rationale**: FR-004 requires the run to stop, and a single base type lets the CLI catch every failure in one place.
- **Alternatives considered**: returning an empty list on error (the silent failure this feature removes).

## 5. Re-check marker

- **Decision**: a verdict with no `verified_by` is checked again. Verdicts with `verified_by` are final.
- **Rationale**: One field carries the rule, and no separate status is needed. The field is already part of the verdict record.

## 6. Invalid model output

- **Decision**: a True or False verdict with no `source_url` is treated as a failed parse: Unverified, no `verified_by`, re-checked next run.
- **Rationale**: The verdict model rejects that combination, and the earlier uncaught exception stopped whole runs.

## 7. Test isolation

- **Decision**: an autouse fixture in `tests/conftest.py` stops `.env` loading and stubs the free search. Tests that need paid search results stub it themselves.
- **Rationale**: Prevents accidental live searches and credit use. Found necessary after an integration test with a real key made live calls.
