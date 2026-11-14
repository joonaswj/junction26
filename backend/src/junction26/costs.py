"""Cost types: what you must pay, what you must pay but varies, what you choose.

    fixed      Fixed essentials: the same every month (housing).
    variable   Essentials that vary: you need them, but a month can be heavy
               or light (groceries, utilities, health, transportation).
    free       Free-choice spending: restaurants, entertainment, lifestyle,
               travel, home & tech.

In the data, housing varies about 3 % from month to month, groceries about
80 % and health about 160 %. So one month of an essential that varies says
little. Everywhere a "per month" figure is shown or compared, essentials
that vary use the customer's 12-MONTH AVERAGE, whatever period is selected.
A heavy month then doesn't distort the picture. Fixed and free-choice costs
use the selected period.

    monthly_figures()   per-month figure per category, on the right basis
    budget()            where the income goes: fixed / varies / free / left over
"""

from __future__ import annotations

import pandas as pd

from . import finance
from .insights import SPENDING_CATEGORIES

COST_TYPES = {
    "fixed": {
        "label": "Fixed essentials",
        "short": "Fixed",
        "description": "Costs you must pay that stay the same every month.",
        "categories": ["Housing"],
    },
    "variable": {
        "label": "Essentials that vary",
        "short": "Varies",
        "description": "Costs you need, but some months are heavier than others. Shown as "
        "your 12-month average so one heavy month doesn't distort the picture.",
        "categories": ["Groceries", "Utilities", "Health", "Transportation"],
    },
    "free": {
        "label": "Free-choice spending",
        "short": "Free choice",
        "description": "Spending you decide on yourself.",
        "categories": ["Restaurants", "Entertainment", "Lifestyle", "Travel", "Home & Tech"],
    },
}
YEAR = 12  # months used for essentials that vary

_TYPE_OF = {c: t for t, info in COST_TYPES.items() for c in info["categories"]}
assert set(_TYPE_OF) == set(SPENDING_CATEGORIES), "every spending category needs a cost type"


def cost_type(category: str) -> str:
    return _TYPE_OF[category]


def uses_yearly_average(category: str) -> bool:
    return _TYPE_OF.get(category) == "variable"


def basis_months(category: str, months: int) -> int:
    """How many months to average a category over, given the selected period."""
    return YEAR if uses_yearly_average(category) else months


def _monthly_average(tx: pd.DataFrame, months: int) -> dict[str, float]:
    """Average spending per month and category over the last `months` months."""
    recent = finance._last_months(tx, months)
    recent = recent[recent["category"].isin(SPENDING_CATEGORIES)]
    sums = (-recent["tx_amount_eur"]).groupby(recent["category"], observed=True).sum()
    return {c: float(sums.get(c, 0.0)) / months for c in SPENDING_CATEGORIES}


def monthly_figures(customer_id: str, months: int = 3) -> dict[str, dict]:
    """Per-month spending per category, each on the basis that makes sense for it.

    {category: {"eur", "type", "basis_months"}}. Essentials that vary are
    always the 12-month average; the rest is the average of the last `months`.
    """
    tx = finance._tx(customer_id)
    selected = _monthly_average(tx, months)
    yearly = selected if months == YEAR else _monthly_average(tx, YEAR)
    return {
        c: {
            "eur": round(yearly[c] if uses_yearly_average(c) else selected[c], 2),
            "type": _TYPE_OF[c],
            "basis_months": basis_months(c, months),
        }
        for c in SPENDING_CATEGORIES
    }


def usual(customer_id: str) -> dict[str, float]:
    """The customer's usual month per category: their 12-month average."""
    return {c: round(v, 2) for c, v in _monthly_average(finance._tx(customer_id), YEAR).items()}


def budget(customer_id: str, months: int = 3) -> dict:
    """Where an average month's income goes, by cost type."""
    figures = monthly_figures(customer_id, months)
    trend = finance.get_monthly_trend(customer_id, YEAR)["months"]
    # Income is averaged over the year too: bonuses and holiday pay vary.
    income = sum(m["income"] for m in trend) / len(trend) if trend else 0.0

    segments = []
    spent = 0.0
    for key, info in COST_TYPES.items():
        items = sorted(
            ({"label": c, "value": figures[c]["eur"], "yearly": round(figures[c]["eur"] * 12)}
             for c in info["categories"]),
            key=lambda i: -i["value"],
        )
        value = round(sum(i["value"] for i in items), 2)
        spent += value
        segments.append({
            "key": key,
            "label": info["label"],
            "description": info["description"],
            "value": value,
            "share_pct": round(value / income * 100) if income else None,
            "items": items,
        })
    left = round(income - spent, 2)
    # Part of what is left may already go to investments.
    invested = round(sum(m["invested"] for m in trend) / len(trend), 2) if trend else 0.0
    return {
        "income": round(income, 2),
        "spent": round(spent, 2),
        "left": left,
        "invested": max(invested, 0.0),
        "left_share_pct": round(left / income * 100) if income else None,
        "segments": segments,
        "months": months,
        "basis": (
            "An average month over the last 12 months."
            if months == YEAR
            else "An average month. Income and essentials that vary are your 12-month average. "
            f"Fixed essentials and free-choice spending are the average of the last {months} "
            f"month{'' if months == 1 else 's'}."
        ),
    }
