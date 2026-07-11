from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from retrieval.adapters.market_macro import FixtureMarketMacroRetriever


class LiveMarketDataAdapter:
    source_type = "market_data"

    def __init__(self, provider: object | None = None) -> None:
        self.provider = provider

    def search(self, query: str, context: dict) -> list[dict]:
        if self.provider is None:
            return [
                {
                    "source": "retrieval_error",
                    "source_type": "retrieval_error",
                    "title": "Live market data provider is not configured",
                    "date": "unknown",
                    "text": (
                        "market_data requires a provider implementation for live mode. "
                        "Set RETRIEVAL_MODE=fixture for deterministic tests, or inject a live market data provider."
                    ),
                    "url": None,
                    "metadata": {
                        "retrieved_at": datetime.now(timezone.utc).isoformat(),
                        "query": query,
                        "adapter": self.source_type,
                        "retrieval_error": "missing_live_market_data_provider",
                        "critical": False,
                    },
                    "confidence": 0.0,
                }
            ]
        search = getattr(self.provider, "search")
        return list(search(query, context))


class FixtureMarketDataAdapter(FixtureMarketMacroRetriever):
    source_type = "market_data"

    def __init__(self, fixture_path: str | Path = "data/fixtures/external/market_macro.json") -> None:
        super().__init__(fixture_path)
