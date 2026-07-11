from __future__ import annotations

from dataclasses import replace

from models.schemas import Evidence, EvidenceNeed, InvestmentRequest
from retrieval.adapters.base import EvidenceSourceAdapter
from retrieval.adapters.local_documents import LocalDocumentRetriever
from retrieval.adapters.filings import LiveSecFilingsAdapter
from retrieval.adapters.market_data import LiveMarketDataAdapter
from retrieval.adapters.news_search import LiveNewsSearchAdapter
from retrieval.adapters.proprietary import ProprietarySourceRetriever
from retrieval.adapters.url_fetcher import UrlFetcherAdapter
from retrieval.adapters.web_search import LiveWebSearchAdapter


class RetrievalOrchestrator:
    """Coordinate source adapters and return normalized Evidence objects."""

    def __init__(self, adapters: list[EvidenceSourceAdapter] | None = None) -> None:
        adapter_list = adapters or [
            LocalDocumentRetriever(),
            UrlFetcherAdapter(),
            LiveSecFilingsAdapter(),
            LiveNewsSearchAdapter(),
            LiveMarketDataAdapter(),
            LiveWebSearchAdapter(),
            ProprietarySourceRetriever(),
        ]
        self.adapters = {adapter.source_type: adapter for adapter in adapter_list}

    def retrieve(
        self,
        request: InvestmentRequest,
        needs: list[EvidenceNeed],
        limit: int = 48,
        similarity_threshold: float = 0.0,
    ) -> list[Evidence]:
        context = {
            "entity": request.entity,
            "time_horizon": request.time_horizon,
            "focus": request.focus,
            "urls": request.urls,
        }
        raw_records: list[dict] = []
        for need in needs:
            for query in need.queries:
                for source_type in need.source_types:
                    adapter = self.adapters.get(source_type)
                    if adapter is None:
                        continue
                    for record in adapter.search(query, context):
                        record.setdefault("metadata", {})
                        record["metadata"].setdefault("step", need.step)
                        raw_records.append(record)

        evidence = [_normalize(record, index) for index, record in enumerate(raw_records, start=1)]
        deduped = _deduplicate(evidence)
        if similarity_threshold > 0:
            deduped = [item for item in deduped if item.confidence >= similarity_threshold]
        if not deduped:
            return _fallback_evidence(request)
        return _renumber(deduped[:limit])


def _normalize(record: dict, index: int) -> Evidence:
    metadata = dict(record.get("metadata") or {})
    source_type = str(record.get("source_type") or metadata.get("adapter") or "unknown")
    return Evidence(
        id=str(record.get("id") or f"ev_{index:03d}"),
        source=str(record.get("source") or source_type),
        source_type=source_type,
        title=record.get("title"),
        date=record.get("date") or "unknown",
        text=str(record.get("text") or ""),
        url=record.get("url"),
        metadata=metadata,
        section=record.get("section"),
        confidence=float(record.get("confidence", 0.0)),
    )


def _deduplicate(evidence: list[Evidence]) -> list[Evidence]:
    deduped: list[Evidence] = []
    seen: set[tuple[str, str, str]] = set()
    for item in evidence:
        text_key = " ".join(item.text.lower().split())[:500]
        key = (item.source_type, item.source, text_key)
        if key in seen:
            continue
        seen.add(key)
        deduped.append(item)
    return deduped


def _fallback_evidence(request: InvestmentRequest) -> list[Evidence]:
    text = (
        f"No source evidence was available for {request.entity}. "
        "This placeholder evidence records the retrieval gap and should be replaced with filings, "
        "transcripts, internal notes, news, market data, or proprietary sources before relying on the memo."
    )
    return [
        Evidence(
            id="ev_001",
            source="retrieval_gap",
            source_type="system_note",
            title="Retrieval Gap",
            date="unknown",
            text=text,
            url=None,
            metadata={"source_available": False},
            section="Retrieval Gap",
            confidence=0.1,
        )
    ]


def _renumber(evidence: list[Evidence]) -> list[Evidence]:
    return [replace(item, id=f"ev_{index:03d}") for index, item in enumerate(evidence, start=1)]
