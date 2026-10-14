"""Tavily web search API wrapper and integration."""

import json
import logging
from typing import Any

logger = logging.getLogger(__name__)


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
            Empty list on error (timeout, quota, no results)
        """
        if not self.tool:
            logger.error("Tavily tool not initialized")
            return []

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
                    logger.error(f"Failed to parse Tavily results: {results}")
                    return []

            # Ensure results is a list
            if not isinstance(results, list):
                results = [results] if results else []

            logger.info(f"Got {len(results)} results for query: {query}")
            return results

        except TimeoutError as e:
            logger.warning(f"Search timeout for query '{query}': {str(e)}")
            return []
        except Exception as e:
            # Catch quota exhaustion, API errors, etc.
            error_msg = str(e)
            if "quota" in error_msg.lower():
                logger.warning(f"Tavily quota exhausted: {error_msg}")
            else:
                logger.error(f"Search error for query '{query}': {error_msg}")
            return []

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
