from __future__ import annotations

import json
from pathlib import Path

from evaluation.models import EvaluationReport


def save_report(report: EvaluationReport, reports_dir: str | Path = "reports") -> Path:
    directory = Path(reports_dir)
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"evaluation_report_{report.run_id}.json"
    path.write_text(json.dumps(report.to_dict(), indent=2), encoding="utf-8")
    return path
