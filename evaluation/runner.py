from __future__ import annotations

from typing import Any

from evaluation.failure_classifier import classify_failures
from evaluation.models import EvaluationReport, EvaluationResult
from evaluation.offline.benchmark import BenchmarkCase
from evaluation.offline.citation import CitationEvaluator
from evaluation.offline.coverage import EvidenceCoverageEvaluator, RiskRecallEvaluator
from evaluation.offline.llm_judge import LLMJudgeEvaluator
from evaluation.offline.recommendation import RecommendationEvaluator
from evaluation.online.ab_test import ABTestEvaluator
from evaluation.online.feedback import FeedbackEvaluator
from evaluation.online.human_review import HumanReviewEvaluator
from evaluation.runtime.drift import DriftEvaluator
from evaluation.runtime.health import RuntimeHealthEvaluator
from evaluation.runtime.replay import ReplayEvaluator
from evaluation.runtime.thresholds import ThresholdEvaluator
from workflow.pipeline import WorkflowRun


class EvaluationRunner:
    def evaluate(
        self,
        run: WorkflowRun,
        benchmark: BenchmarkCase | None = None,
        user_actions: dict[str, Any] | None = None,
    ) -> EvaluationReport:
        artifact = run.to_evaluation_artifact()
        runtime = [
            RuntimeHealthEvaluator().evaluate(run),
            ThresholdEvaluator().evaluate(run),
            ReplayEvaluator().evaluate(run),
            DriftEvaluator().evaluate(run),
        ]
        offline: list[EvaluationResult] = []
        if benchmark is not None:
            offline = [
                CitationEvaluator().evaluate(run, benchmark),
                EvidenceCoverageEvaluator().evaluate(run, benchmark),
                RiskRecallEvaluator().evaluate(run, benchmark),
                RecommendationEvaluator().evaluate(run, benchmark),
                LLMJudgeEvaluator().evaluate(run, benchmark),
            ]
        online: list[EvaluationResult] = []
        if user_actions is not None:
            online = [
                HumanReviewEvaluator().evaluate(run, user_actions),
                FeedbackEvaluator().evaluate(run, user_actions),
                ABTestEvaluator().evaluate(run, user_actions),
            ]

        failures = classify_failures(offline=offline, runtime=runtime, online=online, run=run)
        all_results = [*offline, *runtime, *online]
        passed = sum(1 for result in all_results if result.passed)
        scored = [result.score for result in all_results if result.score is not None]
        return EvaluationReport(
            run_id=artifact["run_id"],
            offline=offline,
            runtime=runtime,
            online=online,
            failures=failures,
            summary={
                "passed": passed,
                "total": len(all_results),
                "average_score": sum(scored) / len(scored) if scored else None,
                "failure_count": len(failures),
                "online_skipped": user_actions is None,
                "offline_skipped": benchmark is None,
            },
        )
