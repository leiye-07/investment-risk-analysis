from __future__ import annotations


def growth_rate(current: float, previous: float) -> float | None:
    if previous == 0:
        return None
    return round((current - previous) / abs(previous), 4)


def direction(current: float, previous: float, tolerance: float = 0.01) -> str:
    change = growth_rate(current, previous)
    if change is None or abs(change) <= tolerance:
        return "neutral"
    return "positive" if change > 0 else "negative"
