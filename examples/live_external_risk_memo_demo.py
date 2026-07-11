from __future__ import annotations

from collections import Counter
from pathlib import Path
import sys


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from workflow.pipeline import run_investment_risk_workflow


def main() -> None:
    question = (
        "Analyze NVIDIA's major downside risks over the next 12 months using filings, "
        "recent news, macro data, and this trusted URL: https://www.sec.gov/"
    )
    run = run_investment_risk_workflow(question, retrieval_mode="live")
    source_counts = Counter(item.source_type for item in run.memo.evidence_appendix)

    print("Planner generated external retrieval tasks:")
    for need in run.evidence_needs:
        external_sources = [source for source in need.source_types if source != "local_documents"]
        if external_sources:
            print(f"- {need.step}: {external_sources} -> {need.queries[:2]}")

    print()
    print("Evidence source types after normalization:")
    for source_type, count in sorted(source_counts.items()):
        print(f"- {source_type}: {count}")

    print()
    print("External evidence metadata:")
    for item in run.memo.evidence_appendix:
        if item.url or item.metadata.get("retrieved_at"):
            print(f"- {item.id}: url={item.url} retrieved_at={item.metadata.get('retrieved_at')}")

    print()
    print(run.memo.markdown)
    print(f"Citation verifier: {run.citation_verification.status}")


if __name__ == "__main__":
    main()
