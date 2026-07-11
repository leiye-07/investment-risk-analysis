from __future__ import annotations

from models.schemas import CitationVerificationResult, RiskMemo


def verify_citations(memo: RiskMemo) -> CitationVerificationResult:
    """Light verifier for evidence coverage and source metadata."""
    evidence_ids = {item.id for item in memo.evidence_appendix}
    invalid_refs: list[str] = []
    missing_claims: list[str] = []

    claim_refs = {
        "business_context": memo.business_context.evidence_refs,
        "financial_analysis": memo.financial_analysis.evidence_refs,
        "recommendation": memo.recommendation.evidence_refs,
    }
    claim_refs.update({f"risk:{risk.risk[:60]}": risk.evidence_refs for risk in memo.risks})
    claim_refs.update({f"change:{change.change[:60]}": change.evidence_refs for change in memo.material_changes})
    claim_refs.update({f"counter:{counter.claim[:60]}": counter.evidence_refs for counter in memo.counter_evidence})

    for claim, refs in claim_refs.items():
        if not refs:
            missing_claims.append(claim)
        invalid_refs.extend(ref for ref in refs if ref not in evidence_ids)

    missing_metadata = [
        item.id
        for item in memo.evidence_appendix
        if not item.source or not item.source_type or item.date is None
    ]
    status = "needs_revision" if missing_claims or invalid_refs or missing_metadata else "verified"
    return CitationVerificationResult(
        status=status,
        missing_evidence_claims=missing_claims,
        invalid_evidence_refs=sorted(set(invalid_refs)),
        missing_source_metadata=missing_metadata,
    )
