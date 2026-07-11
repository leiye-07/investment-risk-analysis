from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class BenchmarkCase:
    case_id: str
    investment_question: str
    expected_findings: list[str]
    expected_sources: list[str]
    expected_recommendation: str | None = None
    expected_confidence: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


def load_benchmark(path: str | Path) -> BenchmarkCase:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    return BenchmarkCase(
        case_id=data["case_id"],
        investment_question=data["investment_question"],
        expected_findings=list(data.get("expected_findings", [])),
        expected_sources=list(data.get("expected_sources", [])),
        expected_recommendation=data.get("expected_recommendation"),
        expected_confidence=data.get("expected_confidence"),
        metadata=dict(data.get("metadata") or {}),
    )
