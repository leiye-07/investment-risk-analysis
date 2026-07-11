from __future__ import annotations

from models.schemas import EvidenceNeed, InvestmentRequest, WorkflowPlan


SOURCE_MAP = {
    "business_context": ["sec_filings", "local_documents", "web_search", "proprietary"],
    "financial_trend_analysis": ["sec_filings", "local_documents", "market_data", "web_search"],
    "historical_comparison": ["sec_filings", "local_documents", "news", "web_search"],
    "risk_identification": ["sec_filings", "local_documents", "news", "web_search", "market_data", "proprietary"],
    "counter_evidence": ["news", "sec_filings", "web_search", "local_documents", "proprietary"],
    "recommendation": ["sec_filings", "local_documents", "news", "web_search", "market_data", "proprietary"],
}

STEP_QUERY_HINTS = {
    "business_context": ["business model revenue drivers investor relations latest filing"],
    "financial_trend_analysis": ["latest revenue margin cash flow liquidity debt filing"],
    "historical_comparison": ["material changes prior quarter prior year earnings"],
    "risk_identification": ["recent risk news competition supply chain macro risks"],
    "counter_evidence": ["mitigating evidence strong demand cash backlog"],
    "recommendation": ["investment risk conclusion downside risk open questions"],
}

STEP_EXTRA_QUERIES = {
    "business_context": ["latest 10-K business overview investor relations"],
    "financial_trend_analysis": ["latest 10-Q revenue margin cash flow liquidity"],
    "risk_identification": [
        "AI infrastructure capex risk recent news",
        "supply chain advanced packaging capacity risk 2026",
    ],
}


def plan_evidence(request: InvestmentRequest, plan: WorkflowPlan) -> list[EvidenceNeed]:
    """Map each workflow step to source types and retrieval queries."""
    needs: list[EvidenceNeed] = []
    for step in plan.steps:
        source_types = SOURCE_MAP.get(step, ["local_documents"])
        queries = [f"{request.entity} {hint}" for hint in STEP_QUERY_HINTS.get(step, [step.replace("_", " ")])]
        queries.extend(f"{request.entity} {query}" for query in STEP_EXTRA_QUERIES.get(step, []))
        queries.extend(f"{request.entity} {focus.replace('_', ' ')}" for focus in request.focus)
        needs.append(EvidenceNeed(step=step, source_types=source_types, queries=list(dict.fromkeys(queries))))
    if request.urls:
        needs.append(EvidenceNeed(step="provided_urls", source_types=["url_fetcher"], queries=request.urls))
    return needs
