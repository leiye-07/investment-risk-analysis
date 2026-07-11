from __future__ import annotations

from evaluation.models import EvaluationResult
from workflow.pipeline import WorkflowRun


class ThresholdEvaluator:
    name = "runtime.thresholds"

    def evaluate(self, run: WorkflowRun) -> EvaluationResult:
        artifact = run.to_evaluation_artifact()
        evidence = artifact.get("evidence_pack", [])
        source_count = len({item.get("source_type") for item in evidence})
        retrieval_trace = artifact.get("retrieval_trace", {})
        threshold_used = retrieval_trace.get("retrieval_similarity_threshold", 0.0)
        limit = retrieval_trace.get("limit") or "default"
        low_evidence = len(evidence) < 3
        sparse_sources = source_count < 3
        return EvaluationResult(
            self.name,
            0.0 if low_evidence else 0.7 if sparse_sources else 1.0,
            not low_evidence,
            "Evidence volume is above runtime warning threshold." if not low_evidence else "Low evidence warning.",
            {
                "retrieval_threshold_used": threshold_used,
                "retrieval_limit": limit,
                "evidence_count": len(evidence),
                "source_count": source_count,
                "low_evidence_warning": low_evidence,
                "sparse_source_warning": sparse_sources,
            },
        )
