from __future__ import annotations

from pathlib import Path

from retrieval.adapters.news import FixtureNewsRetriever
from retrieval.adapters.web_search import LiveWebSearchAdapter, SearchProvider, _missing_provider_record
from retrieval.adapters.url_fetcher import UrlFetcherAdapter


class LiveNewsSearchAdapter(LiveWebSearchAdapter):
    source_type = "news"

    def __init__(
        self,
        provider: SearchProvider | None = None,
        url_fetcher: UrlFetcherAdapter | None = None,
        result_limit: int = 5,
    ) -> None:
        super().__init__(provider=provider, url_fetcher=url_fetcher, result_limit=result_limit)

    def search(self, query: str, context: dict) -> list[dict]:
        if self.provider is None:
            return [_missing_provider_record(query, self.source_type)]
        return super().search(f"{query} reputable financial news", context)


class FixtureNewsSearchAdapter(FixtureNewsRetriever):
    def __init__(self, fixture_path: str | Path = "data/fixtures/external/news.json") -> None:
        super().__init__(fixture_path)
