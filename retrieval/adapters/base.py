from __future__ import annotations

from typing import Protocol


class EvidenceSourceAdapter(Protocol):
    source_type: str

    def search(self, query: str, context: dict) -> list[dict]:
        """Return raw source records for a query.

        Adapters keep source-specific retrieval separate from workflow reasoning.
        The retrieval orchestrator normalizes these records into Evidence objects.
        """
        ...
