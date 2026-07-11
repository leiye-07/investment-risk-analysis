from __future__ import annotations

from evaluation.models import EvaluationResult
from workflow.pipeline import WorkflowRun


class DriftEvaluator:
    name = "runtime.drift"

    def __init__(self, baseline_run: WorkflowRun | None = None) -> None:
        self.baseline_run = baseline_run

    def evaluate(self, run: WorkflowRun) -> EvaluationResult:
        if self.baseline_run is None:
            return EvaluationResult(self.name, None, True, "Skipped: baseline run is unavailable.", {"skipped": True})
        return EvaluationResult(self.name, None, True, "Drift comparison hook is available but not implemented.", {"skipped": True})
