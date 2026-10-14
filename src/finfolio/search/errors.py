"""Errors raised by search clients. A SearchError means the search itself failed, not that it found nothing."""


class SearchError(RuntimeError):
    """A search failed for a reason other than having no results. The fact-check run stops on it."""


class SearchQuotaError(SearchError):
    """The search provider refused searches because its credits are used up."""
