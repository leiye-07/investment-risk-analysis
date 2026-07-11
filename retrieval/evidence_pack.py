from __future__ import annotations

from dataclasses import replace

from models.schemas import Evidence, EvidencePack, InvestmentRequest
from retrieval.reranker import rerank_evidence


def build_evidence_pack(request: InvestmentRequest, evidence: list[Evidence], limit: int = 16) -> EvidencePack:
    """Create a compact, source-labeled evidence bundle for reasoning."""
    deduped: list[Evidence] = []
    seen: set[str] = set()
    for item in rerank_evidence(evidence):
        key = " ".join(item.text.lower().split())[:500]
        if key in seen:
            continue
        seen.add(key)
        metadata = dict(item.metadata)
        metadata.setdefault("topic", _infer_topic(item.text))
        metadata.setdefault("source_type", item.source_type)
        deduped.append(replace(item, metadata=metadata))
    stable = [replace(item, id=f"ev_{index:03d}") for index, item in enumerate(deduped[:limit], start=1)]
    return EvidencePack(entity=request.entity, evidence=stable)


def _infer_topic(text: str) -> str:
    lowered = text.lower()
    if any(term in lowered for term in ["margin", "cash flow", "liquidity", "debt", "revenue"]):
        return "financial_trend_analysis"
    if any(term in lowered for term in ["competition", "pricing", "market share"]):
        return "competitive_risk"
    if any(term in lowered for term in ["rates", "inflation", "macro", "supply chain", "demand"]):
        return "market_context"
    if any(term in lowered for term in ["regulatory", "export", "litigation", "compliance"]):
        return "regulatory_risk"
    return "general_risk"
