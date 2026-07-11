from __future__ import annotations

from typing import Any

from evaluation.models import EvaluationResult
from workflow.pipeline import WorkflowRun


class HumanReviewEvaluator:
    name = "online.human_review"

    def evaluate(self, run: WorkflowRun, user_actions: dict[str, Any]) -> EvaluationResult:
        approved = bool(user_actions.get("approved"))
        rejected = bool(user_actions.get("rejected"))
        edited = bool(user_actions.get("edited"))
        passed = approved and not rejected
        score = 1.0 if approved and not edited and not rejected else 0.7 if approved else 0.0
        return EvaluationResult(
            self.name,
            score,
            passed,
            "Human review approved the memo." if passed else "Human review did not approve the memo.",
            {"approved": approved, "edited": edited, "rejected": rejected},
        )
