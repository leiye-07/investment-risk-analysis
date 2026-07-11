from __future__ import annotations

from dataclasses import asdict, dataclass, field, is_dataclass
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from models.schemas import (
    BusinessContext,
    CitationVerificationResult,
    Evidence,
    EvidenceNeed,
    FinancialAnalysis,
    InvestmentRequest,
    Recommendation,
    ReasoningState,
    RiskMemo,
    WorkflowPlan,
)
from retrieval.adapters.filings import FixtureSecFilingsAdapter, LiveSecFilingsAdapter
from retrieval.adapters.hybrid import HybridRetriever
from retrieval.adapters.local_documents import LocalDocumentRetriever
from retrieval.adapters.market_data import FixtureMarketDataAdapter, LiveMarketDataAdapter
from retrieval.adapters.news_search import FixtureNewsSearchAdapter, LiveNewsSearchAdapter
from retrieval.adapters.proprietary import ProprietarySourceRetriever
from retrieval.adapters.url_fetcher import UrlFetcherAdapter
from retrieval.adapters.web_search import FixtureWebSearchAdapter, LiveWebSearchAdapter
from retrieval.config import RetrievalConfig, load_retrieval_config
from retrieval.evidence_pack import build_evidence_pack
from retrieval.orchestrator import RetrievalOrchestrator
from workflow.citation_verifier import verify_citations
from workflow.evidence_planner import plan_evidence
from workflow.memo_composer import compose_memo
from workflow.parser import parse_request
from workflow.planner import plan_workflow
from workflow.reasoning_graph import run_reasoning_graph


@dataclass(frozen=True)
class WorkflowRun:
    request: InvestmentRequest
    workflow_plan: WorkflowPlan
    evidence_needs: list[EvidenceNeed]
    memo: RiskMemo
    citation_verification: CitationVerificationResult
    run_id: str = field(default_factory=lambda: f"run_{uuid4().hex[:12]}")
    retrieval_trace: dict[str, Any] = field(default_factory=dict)
    evidence_pack: list[Evidence] = field(default_factory=list)
    reasoning_nodes: list[dict[str, Any]] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_evaluation_artifact(self) -> dict[str, Any]:
        evidence = self.evidence_pack or self.memo.evidence_appendix
        retrieval_trace = dict(self.retrieval_trace)
        retrieval_trace.setdefault("evidence_needs", _to_jsonable(self.evidence_needs))
        retrieval_trace.setdefault("citation_verification", _to_jsonable(self.citation_verification))
        retrieval_trace.setdefault("retrieved_evidence_count", len(evidence))
        retrieval_trace.setdefault("source_counts", _source_counts(evidence))
        retrieval_trace.setdefault("retrieval_errors", _retrieval_errors(evidence))
        return {
            "run_id": self.run_id,
            "request": _to_jsonable(self.request),
            "workflow_plan": _to_jsonable(self.workflow_plan),
            "retrieval_trace": _to_jsonable(retrieval_trace),
            "evidence_pack": _to_jsonable(evidence),
            "reasoning_nodes": _to_jsonable(self.reasoning_nodes or _reasoning_nodes_from_memo(self.memo)),
            "final_memo": _to_jsonable(self.memo),
            "metadata": {
                "created_at": datetime.now(timezone.utc).isoformat(),
                "artifact_version": "eval_v1",
                **_to_jsonable(self.metadata),
            },
        }

    def to_dict(self) -> dict[str, Any]:
        return self.to_evaluation_artifact()


def run_investment_risk_workflow(
    question: str,
    documents_dir: str = "data/documents",
    external_dir: str = "data/fixtures/external",
    retrieval_mode: str | None = None,
    workflow_config: dict[str, Any] | None = None,
) -> WorkflowRun:
    request = parse_request(question)
    workflow_plan = plan_workflow(request)
    evidence_needs = plan_evidence(request, workflow_plan)
    config = load_retrieval_config(retrieval_mode)
    workflow_config = dict(workflow_config or {})
    retrieval_similarity_threshold = float(workflow_config.get("retrieval_similarity_threshold", 0.0))
    orchestrator = RetrievalOrchestrator(adapters=_build_adapters(documents_dir, external_dir, config))
    retrieved = orchestrator.retrieve(
        request,
        evidence_needs,
        similarity_threshold=retrieval_similarity_threshold,
    )
    pack = build_evidence_pack(request, retrieved)
    if config.mode == "live" and _has_blocking_live_retrieval_failure(pack.evidence):
        memo = _insufficient_external_evidence_memo(request, pack.evidence)
        verification = verify_citations(memo)
        return WorkflowRun(
            request=request,
            workflow_plan=workflow_plan,
            evidence_needs=evidence_needs,
            memo=memo,
            citation_verification=verification,
            retrieval_trace=_retrieval_trace(
                evidence_needs,
                pack.evidence,
                verification,
                config,
                retrieval_similarity_threshold,
            ),
            evidence_pack=pack.evidence,
            metadata={"retrieval_mode": config.mode, "workflow_config": workflow_config},
        )
    state = run_reasoning_graph(request, pack)
    memo = compose_memo(request, state, pack)
    verification = verify_citations(memo)
    return WorkflowRun(
        request=request,
        workflow_plan=workflow_plan,
        evidence_needs=evidence_needs,
        memo=memo,
        citation_verification=verification,
        retrieval_trace=_retrieval_trace(
            evidence_needs,
            pack.evidence,
            verification,
            config,
            retrieval_similarity_threshold,
        ),
        evidence_pack=pack.evidence,
        reasoning_nodes=reasoning_nodes_from_state(state),
        metadata={"retrieval_mode": config.mode, "workflow_config": workflow_config},
    )


def _build_adapters(documents_dir: str, external_dir: str, config: RetrievalConfig) -> list:
    url_fetcher = UrlFetcherAdapter(timeout_seconds=config.timeout_seconds)
    fixture_sec = FixtureSecFilingsAdapter(f"{external_dir}/filings.json")
    fixture_news = FixtureNewsSearchAdapter(f"{external_dir}/news.json")
    fixture_market = FixtureMarketDataAdapter(f"{external_dir}/market_macro.json")
    fixture_web = FixtureWebSearchAdapter(f"{external_dir}/news.json")
    live_sec = LiveSecFilingsAdapter()
    live_news = LiveNewsSearchAdapter(url_fetcher=url_fetcher, result_limit=config.max_search_results)
    live_market = LiveMarketDataAdapter()
    live_web = LiveWebSearchAdapter(url_fetcher=url_fetcher, result_limit=config.max_search_results)

    adapters = [LocalDocumentRetriever(documents_dir), url_fetcher, ProprietarySourceRetriever()]
    if config.mode == "fixture":
        return [*adapters, fixture_sec, fixture_news, fixture_market, fixture_web]
    if config.mode == "hybrid":
        return [
            *adapters,
            HybridRetriever(live_sec, fixture_sec),
            HybridRetriever(live_news, fixture_news),
            HybridRetriever(live_market, fixture_market),
            HybridRetriever(live_web, fixture_web),
        ]
    return [*adapters, live_sec, live_news, live_market, live_web]


def _retrieval_trace(
    evidence_needs: list[EvidenceNeed],
    evidence: list[Evidence],
    verification: CitationVerificationResult,
    config: RetrievalConfig,
    retrieval_similarity_threshold: float,
) -> dict:
    return {
        "mode": config.mode,
        "retrieval_similarity_threshold": retrieval_similarity_threshold,
        "limit": 48,
        "evidence_needs": [
            {"step": need.step, "source_types": need.source_types, "queries": need.queries}
            for need in evidence_needs
        ],
        "retrieved_evidence_count": len(evidence),
        "source_counts": _source_counts(evidence),
        "retrieval_errors": [
            item.metadata.get("retrieval_error", item.text)
            for item in evidence
            if item.source_type == "retrieval_error" or item.metadata.get("retrieval_error")
        ],
        "citation_verification": {
            "status": verification.status,
            "missing_evidence_claims": verification.missing_evidence_claims,
            "invalid_evidence_refs": verification.invalid_evidence_refs,
            "missing_source_metadata": verification.missing_source_metadata,
        },
    }


def _source_counts(evidence: list[Evidence]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for item in evidence:
        counts[item.source_type] = counts.get(item.source_type, 0) + 1
    return counts


def reasoning_nodes_from_state(state: ReasoningState) -> list[dict[str, Any]]:
    return [
        {"name": "business_context", "output": _to_jsonable(state.business_context)},
        {"name": "financial_analysis", "output": _to_jsonable(state.financial_analysis)},
        {"name": "material_changes", "output": _to_jsonable(state.material_changes)},
        {"name": "risk_identification", "output": _to_jsonable(state.risks)},
        {"name": "counter_evidence", "output": _to_jsonable(state.counter_evidence)},
        {"name": "recommendation", "output": _to_jsonable(state.recommendation)},
    ]


def _reasoning_nodes_from_memo(memo: RiskMemo) -> list[dict[str, Any]]:
    return [
        {"name": "business_context", "output": _to_jsonable(memo.business_context)},
        {"name": "financial_analysis", "output": _to_jsonable(memo.financial_analysis)},
        {"name": "material_changes", "output": _to_jsonable(memo.material_changes)},
        {"name": "risk_identification", "output": _to_jsonable(memo.risks)},
        {"name": "counter_evidence", "output": _to_jsonable(memo.counter_evidence)},
        {"name": "recommendation", "output": _to_jsonable(memo.recommendation)},
    ]


def _retrieval_errors(evidence: list[Evidence]) -> list[dict[str, Any]]:
    return [
        _to_jsonable(item)
        for item in evidence
        if item.source_type == "retrieval_error" or item.metadata.get("retrieval_error")
    ]


def _to_jsonable(value: Any) -> Any:
    if is_dataclass(value):
        return _to_jsonable(asdict(value))
    if isinstance(value, list):
        return [_to_jsonable(item) for item in value]
    if isinstance(value, tuple):
        return [_to_jsonable(item) for item in value]
    if isinstance(value, dict):
        return {str(key): _to_jsonable(item) for key, item in value.items()}
    return value


def _has_blocking_live_retrieval_failure(evidence: list[Evidence]) -> bool:
    has_critical_error = any(item.metadata.get("critical") is True for item in evidence)
    has_live_external_evidence = any(
        item.source_type in {"url_fetcher", "web_search", "news", "market_data", "sec_filings"}
        and item.source_type != "retrieval_error"
        and item.metadata.get("retrieved_at")
        for item in evidence
    )
    return has_critical_error and not has_live_external_evidence


def _insufficient_external_evidence_memo(request: InvestmentRequest, evidence: list[Evidence]) -> RiskMemo:
    refs = [item.id for item in evidence if item.source_type == "retrieval_error"][:6]
    reasons = [
        f"{item.metadata.get('adapter', item.source_type)} failed: {item.metadata.get('retrieval_error', item.text)}"
        for item in evidence
        if item.source_type == "retrieval_error"
    ]
    recommendation = Recommendation(
        recommendation="needs_more_review",
        confidence="low",
        key_reasons=reasons or ["Live external retrieval did not return sufficient evidence."],
        open_questions=[
            "Configure live search, SEC filings, news, or market data providers.",
            "Use explicit trusted URLs, or rerun with RETRIEVAL_MODE=fixture for deterministic offline tests.",
        ],
        evidence_refs=refs,
    )
    business_context = BusinessContext(
        business_model="Not established because critical live external retrieval failed.",
        main_revenue_drivers=[],
        key_dependencies=[],
        evidence_refs=refs,
    )
    financial_analysis = FinancialAnalysis(
        revenue_trend="Not established from live external evidence.",
        margin_trend="Not established from live external evidence.",
        cash_flow_trend="Not established from live external evidence.",
        debt_liquidity_notes="Not established from live external evidence.",
        evidence_refs=refs,
    )
    executive_summary = (
        f"Insufficient live external evidence for {request.entity}. "
        "The workflow did not use synthetic fixture evidence in live mode."
    )
    lines = [
        f"# Investment Risk Memo: {request.entity}",
        "",
        "## 1. Executive Summary",
        executive_summary,
        "",
        "## 2. Retrieval Status",
        "Live external retrieval failed for critical source tasks. Configure providers or use explicit fixture mode.",
        "",
        "## 3. Retrieval Errors",
        *[f"- {reason}" for reason in recommendation.key_reasons],
        "",
        "## 4. Recommendation",
        "Needs more review (low confidence).",
        "",
        "## 5. Evidence Appendix",
    ]
    for item in evidence:
        lines.append(f"- [{item.id}] {item.title or item.source}: {item.text}")
    return RiskMemo(
        entity=request.entity,
        executive_summary=executive_summary,
        business_context=business_context,
        financial_analysis=financial_analysis,
        material_changes=[],
        risks=[],
        counter_evidence=[],
        recommendation=recommendation,
        evidence_appendix=evidence,
        markdown="\n".join(lines).strip() + "\n",
    )
