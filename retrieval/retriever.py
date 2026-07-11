from __future__ import annotations

from pathlib import Path

from models.schemas import Evidence, EvidenceNeed, InvestmentRequest
from retrieval.adapters.local_documents import LocalDocumentRetriever as LocalDocumentAdapter
from retrieval.orchestrator import _normalize, _renumber


class LocalDocumentRetriever:
    """Backward-compatible wrapper around the local document source adapter."""

    def __init__(self, documents_dir: str | Path = "data/documents") -> None:
        self.adapter = LocalDocumentAdapter(documents_dir)

    def retrieve(self, request: InvestmentRequest, needs: list[EvidenceNeed], limit: int = 24) -> list[Evidence]:
        context = {"entity": request.entity, "time_horizon": request.time_horizon, "focus": request.focus}
        raw_records: list[dict] = []
        for need in needs:
            for query in need.queries:
                raw_records.extend(self.adapter.search(query, context))
        evidence = [_normalize(record, index) for index, record in enumerate(raw_records, start=1)]
        return _renumber(evidence[:limit])
