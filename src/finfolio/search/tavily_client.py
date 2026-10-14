"""Tavily web search API wrapper and integration."""

import json
import logging
import re
from typing import Any

from finfolio.search.errors import SearchError, SearchQuotaError

logger = logging.getLogger(__name__)


_QUOTA_PATTERN = re.compile(
    r"\b(432|429)\b.*client error|quota|usage limit|out of credits|insufficient credits",
    re.IGNORECASE,
)


def _is_quota_message(text: str) -> bool:
    """True if an error message says the Tavily quota or credits are used up."""
    return bool(_QUOTA_PATTERN.search(text))


class TavilySearchClient:
    """Wrapper for Tavily web search API integration with LangChain.

    Handles API key from environment variable TAVILY_API_KEY.
    Includes error handling for timeouts, quota exhaustion, and no results.
    """

    def __init__(self, api_key: str | None, timeout_seconds: float = 10.0):
        """Initialize Tavily search client.

        Args:
            api_key: Tavily API key (from environment); None lets the library read it
            timeout_seconds: Search timeout in seconds
        """
        self.api_key = api_key
        self.timeout_seconds = timeout_seconds
        self._initialize_tool()

    def _initialize_tool(self) -> None:
        """Initialize LangChain TavilySearchResults tool.

        Lazy initialization to avoid import errors if dependencies missing.
        """
        try:
            from langchain_community.tools.tavily_search import TavilySearchResults

            self.tool: Any | None = TavilySearchResults(
                api_key=self.api_key,
                max_results=5,  # Max results per query
            )
            logger.info("Tavily search client initialized")
        except ImportError as e:
            logger.error(f"Failed to import TavilySearchResults: {str(e)}")
            self.tool = None

    def search(self, query: str) -> list[dict[str, Any]]:
        """Perform web search via Tavily.

        Args:
            query: Search query string

        Returns:
            List of search results with title, URL, snippet
            Empty list when there are no results. Raises SearchError on any failure,
            and SearchQuotaError when the Tavily credits are used up.
        """
        if not self.tool:
            raise SearchError("Tavily tool not initialized")

        try:
            logger.info(f"Searching: {query}")
            results = self.tool.invoke({"query": query})

            if not results:
                logger.warning(f"No results for query: {query}")
                return []

            # Parse results if they come as JSON string
            if isinstance(results, str):
                try:
                    results = json.loads(results)
                except json.JSONDecodeError:
                    if _is_quota_message(results):
                        raise SearchQuotaError(results) from None
                    raise SearchError(f"Could not parse Tavily results: {results}") from None

            # Ensure results is a list
            if not isinstance(results, list):
                results = [results] if results else []

            logger.info(f"Got {len(results)} results for query: {query}")
            return results

        except SearchQuotaError:
            raise
        except TimeoutError as e:
            raise SearchError(f"Tavily search timed out: {e}") from e
        except Exception as e:
            error_msg = str(e)
            if _is_quota_message(error_msg):
                raise SearchQuotaError(error_msg) from e
            raise SearchError(f"Tavily search failed: {error_msg}") from e

    def format_results_for_llm(self, results: list[dict[str, Any]]) -> str:
        """Format search results for LLM consumption.

        Args:
            results: List of search result dicts

        Returns:
            Formatted string for LLM prompt
        """
        if not results:
            return "No search results available."

        formatted = []
        for i, result in enumerate(results, 1):
            title = result.get("title", "Unknown")
            url = result.get("url", "")
            snippet = result.get("content", result.get("snippet", ""))
            formatted.append(f"{i}. {title}\n   URL: {url}\n   Content: {snippet}")

        return "\n\n".join(formatted)
