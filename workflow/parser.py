from __future__ import annotations

import re

from models.schemas import InvestmentRequest


URL_PATTERN = re.compile(r"https?://[^\s<>)\"']+", re.I)

TIME_HORIZON_PATTERNS = [
    (re.compile(r"\bnext\s+(\d+)\s+months?\b", re.I), "{n}_months"),
    (re.compile(r"\b(\d+)\s*-\s*month\b", re.I), "{n}_months"),
    (re.compile(r"\bnext\s+year\b", re.I), "12_months"),
    (re.compile(r"\b(\d+)\s+years?\b", re.I), "{n}_years"),
]


def parse_request(question: str) -> InvestmentRequest:
    """Convert a natural-language investment question into structured input."""
    normalized = " ".join(question.strip().split())
    entity = _extract_entity(normalized)
    focus = _extract_focus(normalized)
    return InvestmentRequest(
        entity=entity,
        time_horizon=_extract_time_horizon(normalized),
        focus=focus,
        urls=_extract_urls(normalized),
        original_question=normalized,
    )


def _extract_entity(question: str) -> str:
    quoted = re.search(r"['\"]([^'\"]+)['\"]", question)
    if quoted:
        return quoted.group(1).strip()

    analyze_match = re.search(
        r"\b(?:analyze|assess|evaluate|review)\s+(.+?)(?:'s|\s+major|\s+downside|\s+risk|\s+over|\s+using|$)",
        question,
        re.I,
    )
    if analyze_match:
        return analyze_match.group(1).strip(" .")

    ticker_match = re.search(r"\b[A-Z]{2,6}\b", question)
    if ticker_match:
        return ticker_match.group(0)

    return "Unknown Entity"


def _extract_time_horizon(question: str) -> str:
    for pattern, template in TIME_HORIZON_PATTERNS:
        match = pattern.search(question)
        if not match:
            continue
        if "{n}" in template:
            return template.format(n=match.group(1))
        return template
    return "12_months"


def _extract_focus(question: str) -> list[str]:
    focus = ["downside_risk", "material_changes"]
    lowered = question.lower()
    if "liquidity" in lowered or "debt" in lowered:
        focus.append("liquidity")
    if "competitive" in lowered or "competition" in lowered:
        focus.append("competitive_position")
    if "macro" in lowered or "rates" in lowered:
        focus.append("macro")
    return list(dict.fromkeys(focus))


def _extract_urls(question: str) -> list[str]:
    return list(dict.fromkeys(match.group(0).rstrip(".,;") for match in URL_PATTERN.finditer(question)))
