from __future__ import annotations

from evaluation.models import EvaluationResult
from evaluation.offline.benchmark import BenchmarkCase
from workflow.pipeline import WorkflowRun


class LLMJudgeEvaluator:
    name = "offline.llm_judge"

    def __init__(self, client: object | None = None) -> None:
        self.client = client

    def evaluate(self, run: WorkflowRun, benchmark: BenchmarkCase) -> EvaluationResult:
        if self.client is None:
            return EvaluationResult(self.name, None, True, "Skipped: no LLM judge client configured.", {"skipped": True})
        return EvaluationResult(self.name, None, True, "LLM judge client hook is configured but not implemented.", {"skipped": True})
