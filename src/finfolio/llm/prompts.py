"""Prompt templates for fact-checking verdict reasoning."""

VERDICT_REASONING_PROMPT = """You are a fact-checking expert. Evaluate the following claim against the provided search results.

CLAIM:
{claim_text}

SEARCH RESULTS:
{search_results}

Based on the search results, assign a verdict using EXACTLY ONE of these categories:
- "True": The claim is supported by the search results
- "False": The claim contradicts the search results
- "Partially supported/overstated": The claim is partially true but overstated or has misleading elements
- "Unverified": The search results do not provide enough information to verify or contradict the claim

Respond in JSON format with exactly these fields:
{{
    "verdict": "True|False|Partially supported/overstated|Unverified",
    "note": "1-2 sentence explanation of the verdict (max 250 chars)",
    "source_url": "URL of the primary source used (null if Unverified)",
    "source_title": "Title of the source (null if Unverified)",
    "source_date": "Publication date in ISO 8601 format (null if Unverified)"
}}

IMPORTANT:
- Be objective and evidence-based
- If search results conflict, note the conflict in the reasoning
- Never add opinion or speculation
- If there's insufficient information, return "Unverified"
- Always include a brief, factual note explaining the verdict
- Temperature is 0 for consistency; verdicts must be deterministic"""


def get_verdict_prompt(claim_text: str, search_results: str) -> str:
    """Format verdict reasoning prompt.

    Args:
        claim_text: The claim to fact-check
        search_results: Formatted search results to evaluate against

    Returns:
        Formatted prompt string
    """
    return VERDICT_REASONING_PROMPT.format(claim_text=claim_text, search_results=search_results)
