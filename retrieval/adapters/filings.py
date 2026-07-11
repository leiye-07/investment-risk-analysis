from __future__ import annotations

from pathlib import Path
from datetime import datetime, timezone

from retrieval.adapters.fixture import load_fixture, matches_query


class FixtureFilingRetriever:
    source_type = "filings"

    def __init__(self, fixture_path: str | Path = "data/fixtures/external/filings.json") -> None:
        self.fixture_path = Path(fixture_path)

    def search(self, query: str, context: dict) -> list[dict]:
        records = []
        for item in load_fixture(self.fixture_path):
            if not matches_query(item, query, context):
                continue
            records.append(
                {
                    "source": item.get("source", "filing_fixture"),
                    "source_type": self.source_type,
                    "title": item.get("title") or item.get("section"),
                    "date": item.get("date"),
                    "text": item.get("text", ""),
                    "url": item.get("url"),
                    "section": item.get("section"),
                    "metadata": {
                        "filing_type": item.get("filing_type"),
                        "period": item.get("period"),
                        "section": item.get("section"),
                        "adapter": self.source_type,
                        "query": query,
                    },
                    "confidence": item.get("confidence", 0.75),
                }
            )
        return records


class FilingRetriever(FixtureFilingRetriever):
    """Compatibility alias for fixture-backed tests and offline demos."""


class LiveSecFilingsAdapter:
    source_type = "sec_filings"

    def __init__(self, provider: object | None = None) -> None:
        self.provider = provider

    def search(self, query: str, context: dict) -> list[dict]:
        if self.provider is None:
            return [
                {
                    "source": "retrieval_error",
                    "source_type": "retrieval_error",
                    "title": "Live SEC filings provider is not configured",
                    "date": "unknown",
                    "text": (
                        "sec_filings requires a provider implementation for live mode. "
                        "Set RETRIEVAL_MODE=fixture for deterministic tests, or inject a SEC/company filings provider."
                    ),
                    "url": None,
                    "metadata": {
                        "retrieved_at": datetime.now(timezone.utc).isoformat(),
                        "query": query,
                        "adapter": self.source_type,
                        "retrieval_error": "missing_live_sec_filings_provider",
                        "critical": True,
                    },
                    "confidence": 0.0,
                }
            ]
        search = getattr(self.provider, "search")
        return list(search(query, context))


class FixtureSecFilingsAdapter(FixtureFilingRetriever):
    source_type = "sec_filings"
