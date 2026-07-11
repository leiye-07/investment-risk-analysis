from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Protocol

from retrieval.adapters.fixture import load_fixture, matches_query
from retrieval.adapters.url_fetcher import UrlFetcherAdapter, records_from_search_results


class SearchProvider(Protocol):
    def search(self, query: str, context: dict, limit: int = 5) -> list[dict]:
        """Return search results with at least a url field."""
        ...


class LiveWebSearchAdapter:
    source_type = "web_search"

    def __init__(
        self,
        provider: SearchProvider | None = None,
        url_fetcher: UrlFetcherAdapter | None = None,
        result_limit: int = 5,
    ) -> None:
        self.provider = provider
        self.url_fetcher = url_fetcher or UrlFetcherAdapter()
        self.result_limit = result_limit

    def search(self, query: str, context: dict) -> list[dict]:
        if self.provider is None:
            return [_missing_provider_record(query, self.source_type)]
        results = self.provider.search(query, context, limit=self.result_limit)
        return records_from_search_results(results, self.url_fetcher, query=query)


class FixtureWebSearchAdapter:
    source_type = "web_search"

    def __init__(self, fixture_path: str | Path = "data/fixtures/external/news.json") -> None:
        self.fixture_path = Path(fixture_path)

    def search(self, query: str, context: dict) -> list[dict]:
        records = []
        retrieved_at = datetime.now(timezone.utc).isoformat()
        for item in load_fixture(self.fixture_path):
            if not matches_query(item, query, context):
                continue
            url = item.get("url")
            domain = str(url).split("/")[2].removeprefix("www.") if url and "://" in str(url) else ""
            records.append(
                {
                    "source": item.get("publisher") or item.get("source") or "fixture_web_search",
                    "source_type": self.source_type,
                    "title": item.get("headline") or item.get("title") or item.get("topic"),
                    "date": item.get("date"),
                    "text": item.get("snippet") or item.get("text", ""),
                    "url": url,
                    "metadata": {
                        "domain": domain,
                        "retrieved_at": retrieved_at,
                        "query": query,
                        "adapter": "fixture_web_search",
                        "fixture": True,
                        "chunk_index": 1,
                    },
                    "confidence": item.get("confidence", 0.6),
                }
            )
        return records


def _missing_provider_record(query: str, adapter: str) -> dict:
    retrieved_at = datetime.now(timezone.utc).isoformat()
    return {
        "source": "retrieval_error",
        "source_type": "retrieval_error",
        "title": "Live search provider is not configured",
        "date": "unknown",
        "text": (
            f"{adapter} requires a SearchProvider implementation or explicit fixture mode. "
            "Set RETRIEVAL_MODE=fixture for deterministic tests, or inject a live search provider."
        ),
        "url": None,
        "metadata": {
            "retrieved_at": retrieved_at,
            "query": query,
            "adapter": adapter,
            "retrieval_error": "missing_live_search_provider",
            "critical": True,
        },
        "confidence": 0.0,
    }
