from __future__ import annotations

from evaluation.models import EvaluationResult
from workflow.pipeline import WorkflowRun


def classify_failures(
    offline: list[EvaluationResult],
    runtime: list[EvaluationResult],
    online: list[EvaluationResult],
    run: WorkflowRun,
) -> list[dict]:
    failures: list[dict] = []
    artifact = run.to_evaluation_artifact()
    evidence_count = len(artifact.get("evidence_pack", []))
    retrieval_trace = artifact.get("retrieval_trace", {})
    threshold = float(retrieval_trace.get("retrieval_similarity_threshold") or 0.0)
    source_count = len(retrieval_trace.get("source_counts", {}))
    if evidence_count < 3:
        failures.append(
            {
                "type": "retrieval_failure",
                "subtype": "retrieval_threshold_too_high" if threshold >= 0.8 else "low_evidence",
                "reason": "Evidence pack contained fewer than 3 evidence items.",
                "severity": "medium",
                "stage": "runtime",
            }
        )
    if threshold >= 0.8 and source_count < 3:
        failures.append(
            {
                "type": "retrieval_failure",
                "subtype": "retrieval_threshold_too_high",
                "reason": "High retrieval threshold reduced source diversity.",
                "severity": "medium",
                "stage": "runtime",
            }
        )
    if threshold <= 0.4 and evidence_count >= 16:
        failures.append(
            {
                "type": "retrieval_failure",
                "subtype": "retrieval_threshold_too_low",
                "reason": "Low retrieval threshold admitted the maximum evidence-pack size.",
                "severity": "low",
                "stage": "runtime",
            }
        )
    for result in runtime:
        if not result.passed:
            failures.append(_failure("execution_failure", result, "runtime"))
    for result in offline:
        if result.passed:
            continue
        if "citation" in result.name:
            failures.append(_failure("citation_failure", result, "offline", "citation_coverage_drop"))
        elif "recommendation" in result.name:
            failures.append(_failure("recommendation_failure", result, "offline", "recommendation_changed"))
        elif "risk" in result.name:
            failures.append(_failure("reasoning_failure", result, "offline", "missing_expected_risk"))
        elif "coverage" in result.name:
            failures.append(_failure("retrieval_failure", result, "offline", "missing_expected_source"))
    for result in online:
        if not result.passed:
            failures.append(_failure("online_value_failure", result, "online"))
    if artifact.get("retrieval_trace", {}).get("retrieval_errors"):
        failures.append(
            {
                "type": "retrieval_failure",
                "reason": "Retrieval trace contains retrieval errors.",
                "severity": "medium",
                "stage": "runtime",
            }
        )
    return failures


def _failure(kind: str, result: EvaluationResult, stage: str, subtype: str | None = None) -> dict:
    return {
        "type": kind,
        "subtype": subtype,
        "reason": result.reason,
        "severity": "high" if result.score == 0 else "medium",
        "stage": stage,
        "evaluator": result.name,
    }
