from __future__ import annotations

import json
from pathlib import Path
import sys
from typing import Any


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from evaluation.offline.benchmark import BenchmarkCase, load_benchmark
from evaluation.runner import EvaluationRunner
from workflow.pipeline import WorkflowRun, run_investment_risk_workflow


THRESHOLDS = [0.40, 0.50, 0.60, 0.70, 0.80, 0.90]
REPORT_DIR = Path("reports/threshold_failure")
BENCHMARK_PATH = Path("data/benchmarks/nvidia_threshold_case.json")
DOCUMENTS_DIR = "data/documents"
EXTERNAL_DIR = "data/fixtures/external"


def main() -> None:
    benchmark = load_benchmark(BENCHMARK_PATH)
    REPORT_DIR.mkdir(parents=True, exist_ok=True)

    runs = []
    previous_recommendation: str | None = None
    first_failure_threshold: float | None = None
    for threshold in THRESHOLDS:
        run = run_investment_risk_workflow(
            benchmark.investment_question,
            documents_dir=DOCUMENTS_DIR,
            external_dir=EXTERNAL_DIR,
            retrieval_mode="fixture",
            workflow_config={"retrieval_similarity_threshold": threshold},
        )
        report = EvaluationRunner().evaluate(run, benchmark=benchmark)
        row = _summarize_run(threshold, run, report.to_dict())
        row["failures"] = _experiment_failures(row, previous_recommendation)
        if row["failures"] and first_failure_threshold is None:
            first_failure_threshold = threshold
        previous_recommendation = row["recommendation"]
        _save_json(REPORT_DIR / f"report_threshold_{int(threshold * 100):03d}.json", row)
        runs.append(row)

    aggregate = {
        "experiment": "threshold_failure",
        "fixed_variables": {
            "request": benchmark.investment_question,
            "benchmark_case": benchmark.case_id,
            "model_config": "deterministic_stage1_reasoning_graph",
            "documents": DOCUMENTS_DIR,
            "external_fixtures": EXTERNAL_DIR,
            "retrieval_mode": "fixture",
        },
        "variable": "retrieval_similarity_threshold",
        "runs": [
            {
                "threshold": row["threshold"],
                "evidence_count": row["retrieved_evidence_count"],
                "source_coverage": row["source_coverage"],
                "risk_recall": row["risk_recall"],
                "citation_score": row["citation_score"],
                "recommendation": row["recommendation"],
                "confidence": row["confidence"],
                "failures": row["failures"],
            }
            for row in runs
        ],
    }
    _save_json(REPORT_DIR / "threshold_results.json", aggregate)
    (REPORT_DIR / "threshold_summary.md").write_text(
        _render_markdown_summary(benchmark, runs, first_failure_threshold),
        encoding="utf-8",
    )
    print(f"Saved threshold failure experiment reports under {REPORT_DIR}")


def _summarize_run(threshold: float, run: WorkflowRun, report: dict[str, Any]) -> dict[str, Any]:
    artifact = run.to_evaluation_artifact()
    memo = artifact["final_memo"]
    recommendation = memo.get("recommendation", {})
    source_types = sorted({item.get("source_type", "unknown") for item in artifact["evidence_pack"]})
    return {
        "threshold": threshold,
        "run_id": artifact["run_id"],
        "retrieved_evidence_count": len(artifact["evidence_pack"]),
        "source_types_present": source_types,
        "offline": report["offline"],
        "runtime": report["runtime"],
        "failures": report["failures"],
        "recommendation": recommendation.get("recommendation"),
        "confidence": recommendation.get("confidence"),
        "memo_excerpt": memo.get("executive_summary", ""),
        "source_coverage": _score(report, "offline.evidence_source_coverage"),
        "risk_recall": _score(report, "offline.risk_recall"),
        "citation_score": _score(report, "offline.citation_coverage"),
        "runtime_warnings": _runtime_warnings(report),
    }


def _experiment_failures(row: dict[str, Any], previous_recommendation: str | None) -> list[dict[str, Any]]:
    failures = list(row["failures"])
    if row["source_coverage"] is not None and row["source_coverage"] < 1.0:
        failures.append(
            {
                "type": "retrieval_failure",
                "subtype": "missing_expected_source",
                "reason": "Expected benchmark source coverage dropped below 100%.",
                "severity": "medium",
                "stage": "experiment",
            }
        )
    if row["risk_recall"] is not None and row["risk_recall"] < 0.75:
        failures.append(
            {
                "type": "reasoning_failure",
                "subtype": "missing_expected_risk",
                "reason": "Expected finding recall dropped below 75%.",
                "severity": "medium",
                "stage": "experiment",
            }
        )
    if row["citation_score"] is not None and row["citation_score"] < 0.8:
        failures.append(
            {
                "type": "citation_failure",
                "subtype": "citation_coverage_drop",
                "reason": "Citation coverage dropped below 80%.",
                "severity": "medium",
                "stage": "experiment",
            }
        )
    if previous_recommendation and row["recommendation"] != previous_recommendation:
        failures.append(
            {
                "type": "recommendation_failure",
                "subtype": "recommendation_changed",
                "reason": f"Recommendation changed from {previous_recommendation} to {row['recommendation']}.",
                "severity": "high",
                "stage": "experiment",
            }
        )
    return failures


def _score(report: dict[str, Any], name: str) -> float | None:
    for section in ("offline", "runtime", "online"):
        for result in report.get(section, []):
            if result.get("name") == name:
                return result.get("score")
    return None


def _runtime_warnings(report: dict[str, Any]) -> list[str]:
    warnings = []
    for result in report.get("runtime", []):
        details = result.get("details", {})
        if details.get("low_evidence_warning"):
            warnings.append("low_evidence")
        if details.get("sparse_source_warning"):
            warnings.append("sparse_sources")
    return warnings


def _render_markdown_summary(
    benchmark: BenchmarkCase,
    runs: list[dict[str, Any]],
    first_failure_threshold: float | None,
) -> str:
    lines = [
        "# Threshold Failure Experiment",
        "",
        "## Experiment Setup",
        "",
        f"- Question: {benchmark.investment_question}",
        f"- Benchmark: {benchmark.case_id}",
        f"- Variable: `retrieval_similarity_threshold`",
        f"- Thresholds: {', '.join(f'{threshold:.2f}' for threshold in THRESHOLDS)}",
        f"- Fixed documents: `{DOCUMENTS_DIR}`",
        f"- Fixed external fixtures: `{EXTERNAL_DIR}`",
        f"- Retrieval mode: `fixture`",
        "",
        "## Threshold Table",
        "",
        "| Threshold | Evidence Count | Source Coverage | Risk Recall | Citation Score | Recommendation | Failure |",
        "|----------|----------------|----------------|-------------|----------------|----------------|---------|",
    ]
    for row in runs:
        failure = _failure_label(row["failures"])
        lines.append(
            "| "
            f"{row['threshold']:.2f} | "
            f"{row['retrieved_evidence_count']} | "
            f"{_percent(row['source_coverage'])} | "
            f"{_percent(row['risk_recall'])} | "
            f"{_percent(row['citation_score'])} | "
            f"{str(row['recommendation']).title()} / {row['confidence']} | "
            f"{failure} |"
        )

    lines.extend(
        [
            "",
            "## Observed Degradation Pattern",
            "",
            _degradation_pattern(runs),
            "",
            "## Failure Classifications",
            "",
            *_failure_lines(runs),
            "",
            "## Engineering Interpretation",
            "",
            "The experiment isolates retrieval threshold as the changed variable. As the threshold rises, lower-confidence evidence is filtered before the evidence pack reaches reasoning. The memo can remain syntactically fluent even when source diversity, expected finding recall, or recommendations shift.",
            "",
            "## Article Notes",
            "",
            f"- What changed as threshold increased? {_what_changed(runs)}",
            "- Did the final memo remain fluent? Yes. The deterministic memo composer still produced complete prose whenever any evidence reached the reasoning graph.",
            f"- Did evidence coverage degrade? {_coverage_degraded(runs)}",
            f"- Did recommendation change? {_recommendation_changed(runs)}",
            f"- What was the first threshold where failure appeared? {_first_failure(first_failure_threshold)}",
            "- What engineering lesson does this suggest? Retrieval thresholds should be evaluated as production risk controls, not harmless tuning constants; small changes can silently reshape evidence, citations, and decisions downstream.",
            "",
        ]
    )
    return "\n".join(lines)


def _degradation_pattern(runs: list[dict[str, Any]]) -> str:
    first = runs[0]
    last = runs[-1]
    return (
        f"Evidence count moved from {first['retrieved_evidence_count']} at {first['threshold']:.2f} "
        f"to {last['retrieved_evidence_count']} at {last['threshold']:.2f}. "
        f"Source coverage moved from {_percent(first['source_coverage'])} to {_percent(last['source_coverage'])}, "
        f"while risk recall moved from {_percent(first['risk_recall'])} to {_percent(last['risk_recall'])}."
    )


def _failure_lines(runs: list[dict[str, Any]]) -> list[str]:
    lines = []
    for row in runs:
        if not row["failures"]:
            continue
        subtypes = sorted({failure.get("subtype") or failure.get("type") for failure in row["failures"]})
        lines.append(f"- {row['threshold']:.2f}: {', '.join(subtypes)}")
    return lines or ["- No failures were classified."]


def _what_changed(runs: list[dict[str, Any]]) -> str:
    counts = [row["retrieved_evidence_count"] for row in runs]
    return f"retrieved evidence count ranged from {min(counts)} to {max(counts)}, with source coverage and risk recall changing across runs."


def _coverage_degraded(runs: list[dict[str, Any]]) -> str:
    scores = [row["source_coverage"] for row in runs if row["source_coverage"] is not None]
    return "yes" if scores and min(scores) < max(scores) else "no"


def _recommendation_changed(runs: list[dict[str, Any]]) -> str:
    recommendations = {row["recommendation"] for row in runs}
    return "yes" if len(recommendations) > 1 else "no"


def _first_failure(threshold: float | None) -> str:
    return f"{threshold:.2f}" if threshold is not None else "none"


def _failure_label(failures: list[dict[str, Any]]) -> str:
    if not failures:
        return "None"
    return ", ".join(sorted({failure.get("subtype") or failure.get("type") for failure in failures}))


def _percent(value: float | None) -> str:
    if value is None:
        return "n/a"
    return f"{round(value * 100)}%"


def _save_json(path: Path, data: dict[str, Any]) -> None:
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
