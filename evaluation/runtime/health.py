from __future__ import annotations

from evaluation.models import EvaluationResult
from workflow.pipeline import WorkflowRun


class RuntimeHealthEvaluator:
    name = "runtime.health"

    def evaluate(self, run: WorkflowRun) -> EvaluationResult:
        artifact = run.to_evaluation_artifact()
        checks = {
            "request": bool(artifact.get("request")),
            "workflow_plan": bool(artifact.get("workflow_plan", {}).get("steps")),
            "evidence_pack": bool(artifact.get("evidence_pack")),
            "reasoning_nodes": bool(artifact.get("reasoning_nodes")),
            "final_memo": bool(artifact.get("final_memo")),
        }
        passed = all(checks.values())
        score = sum(1 for value in checks.values() if value) / len(checks)
        return EvaluationResult(
            self.name,
            score,
            passed,
            "Workflow run artifact is complete." if passed else "Workflow run artifact is missing required sections.",
            checks,
        )
