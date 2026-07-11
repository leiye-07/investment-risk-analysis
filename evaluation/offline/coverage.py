from __future__ import annotations

from evaluation.models import EvaluationResult
from evaluation.offline.benchmark import BenchmarkCase
from workflow.pipeline import WorkflowRun


SOURCE_ALIASES = {
    "filing": {"filings", "sec_filings"},
    "filings": {"filings", "sec_filings"},
    "macro": {"market_macro", "market_data"},
    "market": {"market_macro", "market_data"},
    "news": {"news", "web_search"},
    "local": {"local_documents"},
}


class EvidenceCoverageEvaluator:
    name = "offline.evidence_source_coverage"

    def evaluate(self, run: WorkflowRun, benchmark: BenchmarkCase) -> EvaluationResult:
        artifact = run.to_evaluation_artifact()
        actual = {item.get("source_type") for item in artifact["evidence_pack"]}
        expected = benchmark.expected_sources
        if not expected:
            return EvaluationResult(self.name, None, True, "No expected sources configured.", {"actual_sources": sorted(actual)})
        matched = [source for source in expected if _source_present(source, actual)]
        score = len(matched) / len(expected)
        return EvaluationResult(
            self.name,
            score,
            score >= 0.8,
            "Expected source coverage met." if score >= 0.8 else "Expected source coverage is incomplete.",
            {"expected_sources": expected, "matched_sources": matched, "actual_sources": sorted(actual)},
        )


class RiskRecallEvaluator:
    name = "offline.risk_recall"

    def evaluate(self, run: WorkflowRun, benchmark: BenchmarkCase) -> EvaluationResult:
        artifact = run.to_evaluation_artifact()
        expected = benchmark.expected_findings
        risks = artifact["final_memo"].get("risks", [])
        text = " ".join(
            [
                str(risk.get("risk", "")) + " " + str(risk.get("reasoning_summary", ""))
                for risk in risks
            ]
        ).lower()
        if not expected:
            return EvaluationResult(self.name, None, True, "No expected findings configured.", {"risk_count": len(risks)})
        matched = [finding for finding in expected if _matches(finding, text)]
        score = len(matched) / len(expected)
        return EvaluationResult(
            self.name,
            score,
            score >= 0.6,
            "Expected risk findings were recalled." if score >= 0.6 else "Expected risk findings were missed.",
            {"expected_findings": expected, "matched_findings": matched, "risk_count": len(risks)},
        )


def _source_present(expected: str, actual: set[str]) -> bool:
    aliases = SOURCE_ALIASES.get(expected.lower(), {expected.lower()})
    return bool(aliases & {item.lower() for item in actual if item})


def _matches(finding: str, text: str) -> bool:
    terms = [term for term in finding.lower().replace("-", " ").split() if len(term) > 3]
    if not terms:
        return False
    return sum(1 for term in terms if term in text) >= max(1, len(terms) // 2)
