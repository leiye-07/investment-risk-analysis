from __future__ import annotations

from models.schemas import Evidence


def rerank_evidence(evidence: list[Evidence]) -> list[Evidence]:
    """Prefer high-confidence chunks with explicit risk or financial language."""
    risk_terms = ("risk", "decline", "pressure", "competition", "margin", "liquidity", "debt", "cash")

    def score(item: Evidence) -> tuple[float, int]:
        term_score = sum(1 for term in risk_terms if term in item.text.lower())
        return (item.confidence, term_score)

    return sorted(evidence, key=score, reverse=True)
