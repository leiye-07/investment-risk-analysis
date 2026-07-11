from __future__ import annotations

from typing import Any

from evaluation.models import EvaluationResult
from workflow.pipeline import WorkflowRun


class FeedbackEvaluator:
    name = "online.feedback"

    def evaluate(self, run: WorkflowRun, user_actions: dict[str, Any]) -> EvaluationResult:
        feedback = str(user_actions.get("feedback") or "")
        return EvaluationResult(
            self.name,
            None,
            True,
            "Captured user feedback." if feedback else "No free-text feedback provided.",
            {"feedback": feedback},
        )
