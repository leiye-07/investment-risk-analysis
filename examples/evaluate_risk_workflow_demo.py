from __future__ import annotations

import json
from pathlib import Path
import sys


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from evaluation.offline.benchmark import load_benchmark
from evaluation.report import save_report
from evaluation.runner import EvaluationRunner
from workflow.pipeline import run_investment_risk_workflow


def main() -> None:
    benchmark = load_benchmark("data/benchmarks/nvidia_risk_case.json")
    run = run_investment_risk_workflow(
        benchmark.investment_question,
        retrieval_mode="fixture",
    )
    report = EvaluationRunner().evaluate(run, benchmark=benchmark)
    path = save_report(report)

    print(json.dumps(report.to_dict(), indent=2))
    print(f"\nSaved report: {path}")


if __name__ == "__main__":
    main()
