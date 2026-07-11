from __future__ import annotations

from evaluation.models import EvaluationResult
from workflow.pipeline import WorkflowRun


class ReplayEvaluator:
    name = "runtime.replay"

    def evaluate(self, run: WorkflowRun) -> EvaluationResult:
        return EvaluationResult(self.name, None, True, "Skipped: replay inputs are unavailable.", {"skipped": True})
