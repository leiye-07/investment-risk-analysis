from __future__ import annotations


def gross_margin(revenue: float, gross_profit: float) -> float | None:
    return _ratio(gross_profit, revenue)


def operating_margin(revenue: float, operating_income: float) -> float | None:
    return _ratio(operating_income, revenue)


def current_ratio(current_assets: float, current_liabilities: float) -> float | None:
    return _ratio(current_assets, current_liabilities)


def debt_to_cash(total_debt: float, cash_and_equivalents: float) -> float | None:
    return _ratio(total_debt, cash_and_equivalents)


def _ratio(numerator: float, denominator: float) -> float | None:
    if denominator == 0:
        return None
    return round(numerator / denominator, 4)
