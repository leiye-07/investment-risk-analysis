from __future__ import annotations

from typing import Any

from evaluation.models import EvaluationResult
from workflow.pipeline import WorkflowRun


class ABTestEvaluator:
    name = "online.ab_test"

    def evaluate(self, run: WorkflowRun, user_actions: dict[str, Any]) -> EvaluationResult:
        return EvaluationResult(self.name, None, True, "Skipped: A/B comparison is not configured.", {"skipped": True})
