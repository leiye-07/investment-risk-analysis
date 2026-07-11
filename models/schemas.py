from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal


Severity = Literal["low", "medium", "high"]
Likelihood = Literal["low", "medium", "high"]
RecommendationValue = Literal["proceed", "watch", "avoid", "needs_more_review"]


@dataclass(frozen=True)
class InvestmentRequest:
    entity: str
    task_type: str = "investment_risk_memo"
    time_horizon: str = "12_months"
    focus: list[str] = field(default_factory=lambda: ["downside_risk", "material_changes"])
    urls: list[str] = field(default_factory=list)
    required_outputs: list[str] = field(
        default_factory=lambda: [
            "executive_summary",
            "risk_factors",
            "evidence",
            "open_questions",
        ]
    )
    original_question: str = ""


@dataclass(frozen=True)
class WorkflowPlan:
    steps: list[str]


@dataclass(frozen=True)
class EvidenceNeed:
    step: str
    source_types: list[str]
    queries: list[str]


@dataclass(frozen=True)
class Evidence:
    id: str
    source: str
    source_type: str
    date: str | None
    text: str
    title: str | None = None
    url: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    section: str | None = None
    confidence: float = 0.0


@dataclass(frozen=True)
class EvidencePack:
    entity: str
    evidence: list[Evidence]


@dataclass(frozen=True)
class RiskFinding:
    risk_type: str
    risk: str
    severity: Severity
    likelihood: Likelihood
    evidence_refs: list[str]
    reasoning_summary: str


@dataclass(frozen=True)
class BusinessContext:
    business_model: str
    main_revenue_drivers: list[str]
    key_dependencies: list[str]
    evidence_refs: list[str]


@dataclass(frozen=True)
class FinancialAnalysis:
    revenue_trend: str
    margin_trend: str
    cash_flow_trend: str
    debt_liquidity_notes: str
    evidence_refs: list[str]


@dataclass(frozen=True)
class MaterialChange:
    change: str
    direction: Literal["positive", "negative", "neutral"]
    evidence_refs: list[str]


@dataclass(frozen=True)
class CounterEvidence:
    claim: str
    contradicting_evidence: str
    evidence_refs: list[str]


@dataclass(frozen=True)
class Recommendation:
    recommendation: RecommendationValue
    confidence: Literal["low", "medium", "high"]
    key_reasons: list[str]
    open_questions: list[str]
    evidence_refs: list[str]


@dataclass(frozen=True)
class ReasoningState:
    business_context: BusinessContext
    financial_analysis: FinancialAnalysis
    material_changes: list[MaterialChange]
    risks: list[RiskFinding]
    counter_evidence: list[CounterEvidence]
    recommendation: Recommendation


@dataclass(frozen=True)
class RiskMemo:
    entity: str
    executive_summary: str
    business_context: BusinessContext
    financial_analysis: FinancialAnalysis
    material_changes: list[MaterialChange]
    risks: list[RiskFinding]
    counter_evidence: list[CounterEvidence]
    recommendation: Recommendation
    evidence_appendix: list[Evidence]
    markdown: str


@dataclass(frozen=True)
class CitationVerificationResult:
    status: Literal["verified", "needs_revision"]
    missing_evidence_claims: list[str]
    invalid_evidence_refs: list[str]
    missing_source_metadata: list[str]
