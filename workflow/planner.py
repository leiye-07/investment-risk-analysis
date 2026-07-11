from __future__ import annotations

from models.schemas import InvestmentRequest, WorkflowPlan


DEFAULT_STEPS = [
    "business_context",
    "financial_trend_analysis",
    "historical_comparison",
    "risk_identification",
    "counter_evidence",
    "recommendation",
]


def plan_workflow(request: InvestmentRequest) -> WorkflowPlan:
    """Define the bounded reasoning steps for a risk analysis workflow memo."""
    return WorkflowPlan(steps=DEFAULT_STEPS.copy())
