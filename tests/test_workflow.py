from __future__ import annotations

from pathlib import Path
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from threading import Thread

from models.schemas import EvidenceNeed
from retrieval.adapters.source_policy import SourcePolicy
from retrieval.adapters.url_fetcher import UrlFetcherAdapter
from retrieval.adapters.web_search import LiveWebSearchAdapter
from retrieval.adapters.filings import FilingRetriever
from retrieval.adapters.local_documents import LocalDocumentRetriever
from retrieval.adapters.market_macro import MarketMacroRetriever
from retrieval.adapters.news import NewsRetriever
from retrieval.orchestrator import RetrievalOrchestrator
from workflow.parser import parse_request
from workflow.pipeline import run_investment_risk_workflow


def test_parse_request_extracts_entity_and_horizon() -> None:
    request = parse_request("Analyze NVIDIA's major downside risks over the next 12 months using the latest 10-Q.")

    assert request.entity == "NVIDIA"
    assert request.time_horizon == "12_months"
    assert "downside_risk" in request.focus


def test_pipeline_builds_cited_memo_from_local_documents(tmp_path: Path) -> None:
    documents = tmp_path / "documents"
    documents.mkdir()
    (documents / "nvidia-10q-2026-05-10.md").write_text(
        """
# Business
NVIDIA revenue depends on data center demand, product execution, and customer adoption.

# Risk Factors
Revenue growth may decline if export controls, supply constraints, or competition pressure demand.
Margin pressure could be significant if component costs rise.

# Liquidity
The company has strong cash balances that may mitigate liquidity risk.
""",
        encoding="utf-8",
    )

    run = run_investment_risk_workflow(
        "Analyze NVIDIA's major downside risks over the next 12 months.",
        documents_dir=str(documents),
        external_dir=str(tmp_path / "missing_external"),
        retrieval_mode="fixture",
    )

    assert run.request.entity == "NVIDIA"
    assert run.workflow_plan.steps == [
        "business_context",
        "financial_trend_analysis",
        "historical_comparison",
        "risk_identification",
        "counter_evidence",
        "recommendation",
    ]
    assert run.memo.risks
    assert "[ev_" in run.memo.markdown
    assert run.citation_verification.status == "verified"


def test_pipeline_handles_missing_documents_without_inventing_evidence(tmp_path: Path) -> None:
    run = run_investment_risk_workflow(
        "Assess ACME downside risk.",
        documents_dir=str(tmp_path / "missing"),
        external_dir=str(tmp_path / "missing_external"),
        retrieval_mode="fixture",
    )

    assert run.memo.evidence_appendix[0].source == "retrieval_gap"
    assert run.memo.recommendation.recommendation == "needs_more_review"
    assert run.memo.recommendation.confidence == "low"
    assert "retrieval gap" in run.memo.markdown.lower()


def test_adapters_return_source_labeled_records(tmp_path: Path) -> None:
    documents = tmp_path / "documents"
    external = tmp_path / "external"
    documents.mkdir()
    external.mkdir()
    (documents / "nvidia-note.md").write_text("NVIDIA revenue faces competition risk.", encoding="utf-8")
    (external / "news.json").write_text(
        '[{"entity":"NVIDIA","publisher":"News","headline":"Risk","date":"2026-06-01","snippet":"NVIDIA competition pressure increased."}]',
        encoding="utf-8",
    )
    (external / "market_macro.json").write_text(
        '[{"source":"Macro","topic":"supply chain","indicator":"capacity","date":"2026-06-01","text":"Supply chain risk may pressure semiconductor demand."}]',
        encoding="utf-8",
    )
    (external / "filings.json").write_text(
        '[{"entity":"NVIDIA","source":"10-Q","filing_type":"10-Q","period":"Q1","section":"Risk Factors","date":"2026-05-10","text":"Margin and revenue risk could be material."}]',
        encoding="utf-8",
    )
    context = {"entity": "NVIDIA"}

    records = [
        LocalDocumentRetriever(documents).search("NVIDIA revenue risk", context)[0],
        NewsRetriever(external / "news.json").search("NVIDIA competition risk", context)[0],
        MarketMacroRetriever(external / "market_macro.json").search("semiconductor supply chain risk", context)[0],
        FilingRetriever(external / "filings.json").search("NVIDIA margin risk", context)[0],
    ]

    assert {record["source_type"] for record in records} == {
        "local_documents",
        "news",
        "market_macro",
        "filings",
    }
    assert all(record["text"] for record in records)


def test_orchestrator_merges_dedupes_and_reasoning_consumes_multi_source_evidence(tmp_path: Path) -> None:
    external = tmp_path / "external"
    external.mkdir()
    duplicate_text = "NVIDIA revenue and margin risk could be material if demand slows."
    (external / "news.json").write_text(
        f"""[
          {{"entity":"NVIDIA","publisher":"News A","headline":"Risk A","date":"2026-06-01","snippet":"{duplicate_text}"}},
          {{"entity":"NVIDIA","publisher":"News A","headline":"Risk A Copy","date":"2026-06-01","snippet":"{duplicate_text}"}},
          {{"entity":"NVIDIA","publisher":"News B","headline":"Competition","date":"2026-06-02","snippet":"Competition risk may pressure pricing."}}
        ]""",
        encoding="utf-8",
    )
    (external / "market_macro.json").write_text(
        '[{"source":"Macro","topic":"rates","indicator":"financial conditions","date":"2026-06-01","text":"Interest rates can pressure technology valuations."}]',
        encoding="utf-8",
    )
    (external / "filings.json").write_text(
        '[{"entity":"NVIDIA","source":"10-Q","filing_type":"10-Q","period":"Q1","section":"Risk Factors","date":"2026-05-10","text":"Supply constraints may pressure revenue timing."}]',
        encoding="utf-8",
    )
    request = parse_request("Analyze NVIDIA downside risks.")
    needs = [
        EvidenceNeed(
            step="risk_identification",
            source_types=["news", "market_macro", "filings"],
            queries=["NVIDIA revenue margin competition risk supply constraints rates"],
        )
    ]
    orchestrator = RetrievalOrchestrator(
        adapters=[
            NewsRetriever(external / "news.json"),
            MarketMacroRetriever(external / "market_macro.json"),
            FilingRetriever(external / "filings.json"),
        ]
    )

    evidence = orchestrator.retrieve(request, needs)

    assert len(evidence) == 4
    assert {item.source_type for item in evidence} == {"news", "market_macro", "filings"}

    run = run_investment_risk_workflow(
        "Analyze NVIDIA downside risks.",
        documents_dir=str(tmp_path / "missing_documents"),
        external_dir=str(external),
        retrieval_mode="fixture",
    )
    assert {"news", "market_data", "sec_filings"}.issubset(
        {item.metadata["source_type"] for item in run.memo.evidence_appendix}
    )
    assert run.memo.risks


def test_live_mode_reports_missing_provider_without_fixture_fallback(tmp_path: Path) -> None:
    run = run_investment_risk_workflow(
        "Assess ACME downside risk.",
        documents_dir=str(tmp_path / "missing_documents"),
        external_dir=str(tmp_path / "missing_external"),
        retrieval_mode="live",
    )

    assert any(item.source_type == "retrieval_error" for item in run.memo.evidence_appendix)
    assert any("requires" in item.text for item in run.memo.evidence_appendix)


def test_url_fetcher_fetches_chunks_and_preserves_metadata(tmp_path: Path) -> None:
    site = tmp_path / "site"
    site.mkdir()
    (site / "risk.html").write_text(
        "<html><head><title>Risk Update</title></head><body><h1>2026-06-01</h1>"
        "<p>NVIDIA revenue risk from supply constraints and competition may pressure margins.</p></body></html>",
        encoding="utf-8",
    )

    class Handler(SimpleHTTPRequestHandler):
        def log_message(self, format: str, *args: object) -> None:
            return

    server = ThreadingHTTPServer(("127.0.0.1", 0), lambda *args, **kwargs: Handler(*args, directory=str(site), **kwargs))
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        url = f"http://127.0.0.1:{server.server_port}/risk.html"
        fetcher = UrlFetcherAdapter(source_policy=SourcePolicy(trusted_domains={"127.0.0.1"}))
        records = fetcher.search(url, {"entity": "NVIDIA", "urls": []})
    finally:
        server.shutdown()
        thread.join(timeout=2)

    assert records
    assert records[0]["url"].endswith("/risk.html")
    assert records[0]["metadata"]["domain"] == "127.0.0.1"
    assert records[0]["metadata"]["retrieved_at"]
    assert records[0]["metadata"]["adapter"] == "url_fetcher"
    assert "NVIDIA revenue risk" in records[0]["text"]


def test_live_web_search_fetches_returned_urls(tmp_path: Path) -> None:
    site = tmp_path / "site"
    site.mkdir()
    (site / "market.html").write_text(
        "<html><head><title>Market Risk</title></head><body>"
        "<p>Semiconductor demand risk increased as AI infrastructure capex slowed.</p></body></html>",
        encoding="utf-8",
    )

    class Handler(SimpleHTTPRequestHandler):
        def log_message(self, format: str, *args: object) -> None:
            return

    server = ThreadingHTTPServer(("127.0.0.1", 0), lambda *args, **kwargs: Handler(*args, directory=str(site), **kwargs))
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        url = f"http://127.0.0.1:{server.server_port}/market.html"

        class Provider:
            def search(self, query: str, context: dict, limit: int = 5) -> list[dict]:
                return [{"title": "Market Risk", "url": url, "snippet": "capex risk"}]

        fetcher = UrlFetcherAdapter(source_policy=SourcePolicy(trusted_domains={"127.0.0.1"}))
        records = LiveWebSearchAdapter(provider=Provider(), url_fetcher=fetcher).search(
            "semiconductor demand risk",
            {"entity": "NVIDIA"},
        )
    finally:
        server.shutdown()
        thread.join(timeout=2)

    assert records
    assert records[0]["url"].endswith("/market.html")
    assert records[0]["metadata"]["search_title"] == "Market Risk"
    assert "AI infrastructure capex" in records[0]["text"]
