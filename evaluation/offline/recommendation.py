from __future__ import annotations

from evaluation.models import EvaluationResult
from evaluation.offline.benchmark import BenchmarkCase
from workflow.pipeline import WorkflowRun


class RecommendationEvaluator:
    name = "offline.recommendation_match"

    def evaluate(self, run: WorkflowRun, benchmark: BenchmarkCase) -> EvaluationResult:
        expected = benchmark.expected_recommendation
        expected_confidence = benchmark.expected_confidence
        actual = run.to_evaluation_artifact()["final_memo"].get("recommendation", {})
        if expected is None and expected_confidence is None:
            return EvaluationResult(self.name, None, True, "No expected recommendation configured.", {})
        recommendation_match = expected is None or actual.get("recommendation") == expected
        confidence_match = expected_confidence is None or actual.get("confidence") == expected_confidence
        score = (int(recommendation_match) + int(confidence_match)) / 2
        return EvaluationResult(
            self.name,
            score,
            recommendation_match and confidence_match,
            "Recommendation matches benchmark." if recommendation_match and confidence_match else "Recommendation differs from benchmark.",
            {
                "expected_recommendation": expected,
                "actual_recommendation": actual.get("recommendation"),
                "expected_confidence": expected_confidence,
                "actual_confidence": actual.get("confidence"),
            },
        )
