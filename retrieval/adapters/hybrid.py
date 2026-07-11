from __future__ import annotations


class HybridRetriever:
    def __init__(self, live_adapter: object, fixture_adapter: object) -> None:
        self.live_adapter = live_adapter
        self.fixture_adapter = fixture_adapter
        self.source_type = getattr(live_adapter, "source_type")

    def search(self, query: str, context: dict) -> list[dict]:
        live_records = list(self.live_adapter.search(query, context))
        if live_records and any(record.get("source_type") != "retrieval_error" for record in live_records):
            return live_records
        fixture_records = list(self.fixture_adapter.search(query, context))
        if fixture_records:
            return fixture_records
        return live_records
