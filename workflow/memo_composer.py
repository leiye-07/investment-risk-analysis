from __future__ import annotations

from models.schemas import EvidencePack, InvestmentRequest, ReasoningState, RiskMemo


def compose_memo(request: InvestmentRequest, state: ReasoningState, pack: EvidencePack) -> RiskMemo:
    executive_summary = _executive_summary(request, state)
    markdown = _render_markdown(request, executive_summary, state, pack)
    return RiskMemo(
        entity=request.entity,
        executive_summary=executive_summary,
        business_context=state.business_context,
        financial_analysis=state.financial_analysis,
        material_changes=state.material_changes,
        risks=state.risks,
        counter_evidence=state.counter_evidence,
        recommendation=state.recommendation,
        evidence_appendix=pack.evidence,
        markdown=markdown,
    )


def _executive_summary(request: InvestmentRequest, state: ReasoningState) -> str:
    top_risks = ", ".join(risk.risk_type for risk in state.risks[:3]) or "insufficient evidence"
    return (
        f"For {request.entity} over {request.time_horizon}, the workflow identifies {top_risks} "
        f"as the main downside areas. The recommended stance is "
        f"{state.recommendation.recommendation.replace('_', ' ')} with {state.recommendation.confidence} confidence."
    )


def _render_markdown(
    request: InvestmentRequest,
    executive_summary: str,
    state: ReasoningState,
    pack: EvidencePack,
) -> str:
    lines = [
        f"# Investment Risk Memo: {request.entity}",
        "",
        "## 1. Executive Summary",
        executive_summary,
        "",
        "## 2. Business Context",
        f"- Business model: {state.business_context.business_model} {_cite(state.business_context.evidence_refs)}",
        f"- Revenue drivers: {_list_or_none(state.business_context.main_revenue_drivers)}",
        f"- Key dependencies: {_list_or_none(state.business_context.key_dependencies)}",
        "",
        "## 3. Material Changes",
    ]
    for change in state.material_changes:
        lines.append(f"- ({change.direction}) {change.change} {_cite(change.evidence_refs)}")

    lines.extend(["", "## 4. Key Risks"])
    for risk in state.risks:
        lines.append(
            f"- {risk.risk_type.title()} | severity={risk.severity}, likelihood={risk.likelihood}: "
            f"{risk.risk} {_cite(risk.evidence_refs)}"
        )
        lines.append(f"  Reasoning: {risk.reasoning_summary}")

    lines.extend(["", "## 5. Counter-Evidence"])
    for counter in state.counter_evidence:
        lines.append(f"- Against '{counter.claim}': {counter.contradicting_evidence} {_cite(counter.evidence_refs)}")

    lines.extend(
        [
            "",
            "## 6. Open Questions",
            *[f"- {question}" for question in state.recommendation.open_questions],
            "",
            "## 7. Recommendation",
            f"{state.recommendation.recommendation.replace('_', ' ').title()} "
            f"({state.recommendation.confidence} confidence). {_cite(state.recommendation.evidence_refs)}",
            "",
            "Key reasons:",
            *[f"- {reason}" for reason in state.recommendation.key_reasons],
            "",
            "## 8. Evidence Appendix",
        ]
    )
    for item in pack.evidence:
        section = f", section={item.section}" if item.section else ""
        title = f"{item.title}; " if item.title else ""
        url = f" {item.url}" if item.url else ""
        lines.append(f"- [{item.id}] {title}{item.source} ({item.source_type}, date={item.date}{section}): {item.text}{url}")
    return "\n".join(lines).strip() + "\n"


def _cite(refs: list[str]) -> str:
    return "[" + ", ".join(refs) + "]" if refs else "[missing evidence]"


def _list_or_none(values: list[str]) -> str:
    return ", ".join(values) if values else "not established from evidence"
