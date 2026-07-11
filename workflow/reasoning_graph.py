from __future__ import annotations

from collections import Counter

from models.schemas import (
    BusinessContext,
    CounterEvidence,
    Evidence,
    EvidencePack,
    FinancialAnalysis,
    InvestmentRequest,
    MaterialChange,
    Recommendation,
    ReasoningState,
    RiskFinding,
)


RISK_KEYWORDS = {
    "financial": ["margin", "revenue", "cash flow", "liquidity", "debt", "financing"],
    "operational": ["supply", "capacity", "production", "execution", "customer concentration"],
    "competitive": ["competition", "pricing", "market share", "substitute"],
    "macro": ["rates", "inflation", "macro", "demand", "cyclical"],
    "execution": ["integration", "launch", "delivery", "delay", "forecast"],
    "regulatory": ["regulatory", "litigation", "compliance", "export", "sanction"],
}

COUNTER_KEYWORDS = ["offset", "mitigate", "strong", "improve", "growth", "resilient", "backlog", "cash"]


def run_reasoning_graph(request: InvestmentRequest, pack: EvidencePack) -> ReasoningState:
    """Run bounded reasoning nodes in design-doc order."""
    business_context = _business_context(request, pack.evidence)
    financial_analysis = _financial_analysis(pack.evidence)
    material_changes = _historical_comparison(pack.evidence)
    risks = _risk_identification(pack.evidence)
    counter_evidence = _counter_evidence(risks, pack.evidence)
    recommendation = _recommendation(risks, counter_evidence)
    return ReasoningState(
        business_context=business_context,
        financial_analysis=financial_analysis,
        material_changes=material_changes,
        risks=risks,
        counter_evidence=counter_evidence,
        recommendation=recommendation,
    )


def _business_context(request: InvestmentRequest, evidence: list[Evidence]) -> BusinessContext:
    refs = _refs(evidence, ["revenue", "business", "segment", "customer", "product"], limit=3)
    if refs:
        model = f"{request.entity} performance appears tied to the operating drivers described in the cited company materials."
    else:
        model = f"{request.entity} business context could not be established from the available evidence."
    return BusinessContext(
        business_model=model,
        main_revenue_drivers=_topics(evidence, ["revenue", "demand", "customer", "product", "segment"]),
        key_dependencies=_topics(evidence, ["supply", "capacity", "customer", "regulatory", "technology"]),
        evidence_refs=refs,
    )


def _financial_analysis(evidence: list[Evidence]) -> FinancialAnalysis:
    refs = _refs(evidence, ["revenue", "margin", "cash flow", "debt", "liquidity"], limit=4)
    return FinancialAnalysis(
        revenue_trend=_summarize_signal(evidence, "revenue"),
        margin_trend=_summarize_signal(evidence, "margin"),
        cash_flow_trend=_summarize_signal(evidence, "cash flow"),
        debt_liquidity_notes=_summarize_signal(evidence, "liquidity", fallback_keyword="debt"),
        evidence_refs=refs,
    )


def _historical_comparison(evidence: list[Evidence]) -> list[MaterialChange]:
    changes: list[MaterialChange] = []
    for keyword in ["increase", "decrease", "decline", "improve", "pressure", "change"]:
        matching = [item for item in evidence if keyword in item.text.lower()]
        if not matching:
            continue
        direction = "negative" if keyword in {"decrease", "decline", "pressure"} else "positive"
        if keyword == "change":
            direction = "neutral"
        changes.append(
            MaterialChange(
                change=_first_sentence(matching[0].text),
                direction=direction,
                evidence_refs=[matching[0].id],
            )
        )
        if len(changes) >= 4:
            break
    if changes:
        return changes
    return [
        MaterialChange(
            change="No explicit period-over-period change was identified in the available evidence.",
            direction="neutral",
            evidence_refs=[evidence[0].id] if evidence else [],
        )
    ]


def _risk_identification(evidence: list[Evidence]) -> list[RiskFinding]:
    findings: list[RiskFinding] = []
    used_refs: set[str] = set()
    for risk_type, keywords in RISK_KEYWORDS.items():
        matches = [item for item in evidence if any(keyword in item.text.lower() for keyword in keywords)]
        if not matches:
            continue
        top = matches[0]
        used_refs.add(top.id)
        severity = _severity(top.text)
        findings.append(
            RiskFinding(
                risk_type=risk_type,
                risk=_risk_statement(risk_type, top.text),
                severity=severity,
                likelihood=_likelihood(top.text, severity),
                evidence_refs=[top.id],
                reasoning_summary=f"Evidence from {top.source} indicates this risk through: {_first_sentence(top.text)}",
            )
        )
        if len(findings) >= 6:
            break

    if findings:
        return findings

    fallback_ref = evidence[0].id if evidence else ""
    return [
        RiskFinding(
            risk_type="execution",
            risk="The available evidence is too thin to support a reliable downside-risk assessment.",
            severity="medium",
            likelihood="medium",
            evidence_refs=[fallback_ref] if fallback_ref else [],
            reasoning_summary="Retrieval did not provide enough company-specific risk evidence.",
        )
    ]


def _counter_evidence(risks: list[RiskFinding], evidence: list[Evidence]) -> list[CounterEvidence]:
    counters: list[CounterEvidence] = []
    for risk in risks:
        matches = [
            item
            for item in evidence
            if item.id not in set(risk.evidence_refs)
            and any(keyword in item.text.lower() for keyword in COUNTER_KEYWORDS)
        ]
        if not matches:
            continue
        top = matches[0]
        counters.append(
            CounterEvidence(
                claim=risk.risk,
                contradicting_evidence=_first_sentence(top.text),
                evidence_refs=[top.id],
            )
        )
    if counters:
        return counters[:4]
    return [
        CounterEvidence(
            claim="Risk thesis balance",
            contradicting_evidence="No clear counter-evidence was retrieved; analyst review should seek management commentary or alternative data before relying on the conclusion.",
            evidence_refs=[evidence[0].id] if evidence else [],
        )
    ]


def _recommendation(risks: list[RiskFinding], counters: list[CounterEvidence]) -> Recommendation:
    severity_counts = Counter(risk.severity for risk in risks)
    high = severity_counts["high"]
    medium = severity_counts["medium"]
    all_refs = list(dict.fromkeys(ref for risk in risks for ref in risk.evidence_refs))
    thin_evidence = any("too thin" in risk.risk.lower() for risk in risks)
    if thin_evidence or not all_refs:
        recommendation = "needs_more_review"
    elif high >= 2:
        recommendation = "avoid"
    elif high == 1 or medium >= 2:
        recommendation = "watch"
    else:
        recommendation = "proceed"

    return Recommendation(
        recommendation=recommendation,
        confidence="low" if thin_evidence or not all_refs else "medium",
        key_reasons=[risk.risk for risk in risks[:3]],
        open_questions=[
            "Are there newer filings, transcripts, internal notes, or news items missing from the evidence pack?",
            "Do portfolio exposures or position sizing constraints change the practical risk conclusion?",
        ],
        evidence_refs=all_refs[:6],
    )


def _refs(evidence: list[Evidence], keywords: list[str], limit: int) -> list[str]:
    refs = [item.id for item in evidence if any(keyword in item.text.lower() for keyword in keywords)]
    return list(dict.fromkeys(refs))[:limit]


def _topics(evidence: list[Evidence], keywords: list[str]) -> list[str]:
    found = []
    all_text = " ".join(item.text.lower() for item in evidence)
    for keyword in keywords:
        if keyword in all_text:
            found.append(keyword.replace("_", " "))
    return found[:5]


def _summarize_signal(evidence: list[Evidence], keyword: str, fallback_keyword: str | None = None) -> str:
    keywords = [keyword]
    if fallback_keyword:
        keywords.append(fallback_keyword)
    for item in evidence:
        lowered = item.text.lower()
        if any(word in lowered for word in keywords):
            return _first_sentence(item.text)
    return f"No specific {keyword} signal was found in the available evidence."


def _risk_statement(risk_type: str, text: str) -> str:
    return f"{risk_type.title()} risk may pressure the investment case: {_first_sentence(text)}"


def _severity(text: str) -> str:
    lowered = text.lower()
    if any(word in lowered for word in ["material", "significant", "substantial", "severe", "major"]):
        return "high"
    if any(word in lowered for word in ["could", "may", "pressure", "decline", "uncertain"]):
        return "medium"
    return "low"


def _likelihood(text: str, severity: str) -> str:
    lowered = text.lower()
    if any(word in lowered for word in ["currently", "ongoing", "continued", "expected"]):
        return "high"
    if severity == "high":
        return "medium"
    return "medium" if any(word in lowered for word in ["may", "could", "risk"]) else "low"


def _first_sentence(text: str) -> str:
    cleaned = " ".join(text.strip().split())
    if not cleaned:
        return ""
    for separator in [". ", "; "]:
        if separator in cleaned:
            return cleaned.split(separator, 1)[0].strip() + "."
    return cleaned[:240].strip()
