from __future__ import annotations

from evaluation.models import EvaluationResult
from evaluation.offline.benchmark import BenchmarkCase
from workflow.pipeline import WorkflowRun


class CitationEvaluator:
    name = "offline.citation_coverage"

    def evaluate(self, run: WorkflowRun, benchmark: BenchmarkCase) -> EvaluationResult:
        artifact = run.to_evaluation_artifact()
        evidence_ids = {item["id"] for item in artifact["evidence_pack"]}
        claims = []
        memo = artifact["final_memo"]
        claims.extend(memo.get("risks", []))
        claims.extend(memo.get("material_changes", []))
        recommendation = memo.get("recommendation") or {}
        if recommendation:
            claims.append(recommendation)
        if not claims:
            return EvaluationResult(self.name, 0.0, False, "No memo claims found.", {})

        cited = 0
        invalid_refs = []
        for claim in claims:
            refs = claim.get("evidence_refs", [])
            if refs:
                cited += 1
            invalid_refs.extend(ref for ref in refs if ref not in evidence_ids)
        score = cited / len(claims)
        passed = score >= 0.8 and not invalid_refs
        reason = "Citation coverage is acceptable." if passed else "Some claims lack valid evidence references."
        return EvaluationResult(
            self.name,
            score,
            passed,
            reason,
            {"claim_count": len(claims), "cited_claims": cited, "invalid_refs": invalid_refs},
        )
