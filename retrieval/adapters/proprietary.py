from __future__ import annotations

from collections.abc import Callable, Iterable
from typing import Any


class ProprietarySourceRetriever:
    source_type = "proprietary"

    def __init__(self, integrations: Iterable[Callable[[str, dict], Iterable[dict[str, Any]]] | Any] = ()) -> None:
        self.integrations = tuple(integrations)

    def search(self, query: str, context: dict) -> list[dict]:
        records: list[dict] = []
        for integration in self.integrations:
            search = getattr(integration, "search", integration)
            for record in search(query, context) or ():
                normalized = dict(record)
                normalized.setdefault("source_type", self.source_type)
                metadata = dict(normalized.get("metadata") or {})
                metadata.setdefault("adapter", self.source_type)
                metadata.setdefault("query", query)
                normalized["metadata"] = metadata
                records.append(normalized)
        return records
