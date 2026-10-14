# Contract: Search chain (internal)

## Free source: `DuckDuckGoSearchClient.search(query) -> list[dict]`

- Returns `[{title, url, content}]`, or `[]` when nothing matches.
- Raises on backend failure. The chain catches this and falls back to the paid source.

## Paid source: `TavilySearchClient.search(query) -> list[dict]`

- Returns `[{title, url, content}]`, or `[]` when Tavily reports no results.
- Raises `SearchQuotaError` when credits are used up, `SearchError` for any other failure.
- Never returns an empty list for a failure. A failure must stop the run (FR-004).

## Chain: `FactChecker.verify_claim(claim) -> VerdictModel`

1. Search the free source. On error or no results, go to step 3.
2. Ask the model for a verdict from the free results. Accept it if not Unverified and confidence ≥ threshold (`verified_by=duckduckgo`). Otherwise go to step 3.
3. Search the paid source. Its errors propagate. Ask the model for a verdict (`verified_by=tavily`).
