from __future__ import annotations

import argparse
import json
from dataclasses import asdict, is_dataclass
from pathlib import Path
from typing import Any

from workflow.pipeline import run_investment_risk_workflow


def main() -> None:
    parser = argparse.ArgumentParser(description="Run investment risk workflow.")
    parser.add_argument("question", help="Investment risk question to analyze.")
    parser.add_argument("--documents-dir", default="data/documents", help="Directory of .txt/.md source documents.")
    parser.add_argument("--external-dir", default="data/fixtures/external", help="Directory of fixture-backed external sources.")
    parser.add_argument(
        "--retrieval-mode",
        choices=["live", "fixture", "hybrid"],
        help="External retrieval mode. Defaults to RETRIEVAL_MODE or live.",
    )
    parser.add_argument("--json", action="store_true", help="Emit structured JSON instead of markdown.")
    parser.add_argument("--output", help="Optional path for memo markdown or JSON output.")
    args = parser.parse_args()

    run = run_investment_risk_workflow(
        args.question,
        documents_dir=args.documents_dir,
        external_dir=args.external_dir,
        retrieval_mode=args.retrieval_mode,
    )
    rendered = json.dumps(_to_jsonable(run), indent=2) if args.json else run.memo.markdown

    if args.output:
        Path(args.output).write_text(rendered, encoding="utf-8")
    else:
        print(rendered)
        if not args.json:
            print(f"Citation verifier: {run.citation_verification.status}")


def _to_jsonable(value: Any) -> Any:
    if is_dataclass(value):
        return {key: _to_jsonable(item) for key, item in asdict(value).items()}
    if isinstance(value, list):
        return [_to_jsonable(item) for item in value]
    if isinstance(value, dict):
        return {key: _to_jsonable(item) for key, item in value.items()}
    return value


if __name__ == "__main__":
    main()
