from __future__ import annotations

from pathlib import Path

from retrieval.adapters.fixture import load_fixture, matches_query


class FixtureMarketMacroRetriever:
    source_type = "market_macro"

    def __init__(self, fixture_path: str | Path = "data/fixtures/external/market_macro.json") -> None:
        self.fixture_path = Path(fixture_path)

    def search(self, query: str, context: dict) -> list[dict]:
        records = []
        for item in load_fixture(self.fixture_path):
            if not matches_query(item, query, context):
                continue
            records.append(
                {
                    "source": item.get("source", "macro_fixture"),
                    "source_type": self.source_type,
                    "title": item.get("topic") or item.get("indicator"),
                    "date": item.get("date"),
                    "text": item.get("text", ""),
                    "url": item.get("url"),
                    "metadata": {
                        "indicator": item.get("indicator"),
                        "topic": item.get("topic"),
                        "adapter": self.source_type,
                        "query": query,
                    },
                    "confidence": item.get("confidence", 0.65),
                }
            )
        return records


class MarketMacroRetriever(FixtureMarketMacroRetriever):
    """Compatibility alias for fixture-backed tests and offline demos."""
