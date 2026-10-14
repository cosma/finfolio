"""DuckDuckGo search via the ddgs library. Free and keyless; first step in the search chain."""

import logging
from typing import Any

from ddgs import DDGS

logger = logging.getLogger(__name__)


class DuckDuckGoSearchClient:
    """Returns results in the same shape as TavilySearchClient: title, url, content."""

    def __init__(self, max_results: int = 5):
        self.max_results = max_results

    def search(self, query: str) -> list[dict[str, Any]]:
        """Search DuckDuckGo. Raises on backend failure; returns [] when nothing matches."""
        raw = DDGS().text(query, max_results=self.max_results)
        return [
            {
                "title": item.get("title", ""),
                "url": item.get("href", ""),
                "content": item.get("body", ""),
            }
            for item in raw or []
        ]
