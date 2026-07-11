from __future__ import annotations

from pathlib import Path

from retrieval.adapters.fixture import load_fixture, matches_query


class FixtureNewsRetriever:
    source_type = "news"

    def __init__(self, fixture_path: str | Path = "data/fixtures/external/news.json") -> None:
        self.fixture_path = Path(fixture_path)

    def search(self, query: str, context: dict) -> list[dict]:
        records = []
        for item in load_fixture(self.fixture_path):
            if not matches_query(item, query, context):
                continue
            records.append(
                {
                    "source": item.get("publisher", "news_fixture"),
                    "source_type": self.source_type,
                    "title": item.get("headline"),
                    "date": item.get("date"),
                    "text": item.get("snippet", ""),
                    "url": item.get("url"),
                    "metadata": {
                        "publisher": item.get("publisher"),
                        "headline": item.get("headline"),
                        "adapter": self.source_type,
                        "query": query,
                    },
                    "confidence": item.get("confidence", 0.7),
                }
            )
        return records


class NewsRetriever(FixtureNewsRetriever):
    """Compatibility alias for fixture-backed tests and offline demos."""
