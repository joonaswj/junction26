"""Per-customer financial summaries, returned as small JSON-ready dicts.

Used by the dashboard endpoints and as chatbot tools. All amounts are EUR.
Spending amounts are positive numbers. "Today" is the last date in the
dataset (see data_end_date()), not the real date.
"""

from __future__ import annotations

from datetime import date
from functools import lru_cache

import pandas as pd

from .data import load_customers, load_mortgage_events, load_mortgage_outcomes, load_transactions
from .insights import SPENDING_CATEGORIES, get_comparison, get_insights, get_profile

INCOME_CATEGORIES = ["Salary", "Other Income"]


class CustomerNotFound(KeyError):
    pass


@lru_cache(maxsize=1)
def data_end_date() -> date:
    return load_transactions()["tx_date"].max().date()


def _tx(customer_id: str) -> pd.DataFrame:
    if not load_customers()["customer_id"].eq(customer_id).any():
        raise CustomerNotFound(customer_id)
    return load_transactions([customer_id])


def _last_months(tx: pd.DataFrame, months: int) -> pd.DataFrame:
    start = pd.Timestamp(data_end_date()) - pd.DateOffset(months=months)
    return tx[tx["tx_date"] > start]


def _r(x: float) -> float:
    return round(float(x), 2)


def _spending_by_category(tx: pd.DataFrame) -> dict[str, float]:
    s = tx[tx["category"].isin(SPENDING_CATEGORIES)].groupby("category", observed=True)[
        "tx_amount_eur"
    ].sum()
    return {k: _r(-v) for k, v in s.sort_values().items() if v != 0}


def _monthly_table(tx: pd.DataFrame) -> pd.DataFrame:
    """One row per month: income, spending, invested, net, end balance."""
    month = tx["tx_date"].dt.to_period("M")
    amt = tx["tx_amount_eur"]
    cat = tx["category"]
    df = pd.DataFrame(
        {
            "income": amt.where(cat.isin(INCOME_CATEGORIES), 0.0),
            "spending": -amt.where(cat.isin(SPENDING_CATEGORIES), 0.0),
            "invested": -amt.where(cat.isin(["Invest Deposit", "Invest Withdraw"]), 0.0),
            "net": amt,
        }
    ).groupby(month).sum()
    df["end_balance"] = tx.sort_values("tx_timestamp").groupby(month)["balance_after_eur"].last()
    return df.round(2) + 0.0  # + 0.0 turns -0.0 into 0.0


def get_overview(customer_id: str) -> dict:
    """Headline numbers for the dashboard and the chatbot's first look."""
    tx = _tx(customer_id)
    last = tx.sort_values("tx_timestamp").iloc[-1]
    year = _last_months(tx, 12)
    monthly = _monthly_table(year)
    income = monthly["income"].mean()
    spending = monthly["spending"].mean()
    top = list(_spending_by_category(year).items())[:3]
    profile = get_profile(customer_id)
    return {
        "customer_id": customer_id,
        "age": profile["age"],
        "data_until": data_end_date().isoformat(),
        "current_balance_eur": _r(last["balance_after_eur"]),
        "avg_monthly_income_eur": _r(income),
        "avg_monthly_spending_eur": _r(spending),
        "avg_monthly_invested_eur": _r(monthly["invested"].mean()),
        "savings_rate_pct": round((income - spending) / income * 100, 1) if income else None,
        "top_categories_last_12_months": [
            {"category": c, "avg_monthly_eur": _r(v / 12)} for c, v in top
        ],
        "peer_group": profile["peer_group"],
        "low_activity": profile["low_activity"],
        "has_mortgage_application": customer_id
        in set(load_mortgage_outcomes()["customer_id"]),
    }


def get_spending(customer_id: str, months: int = 3, category: str | None = None) -> dict:
    """Total spending per category over the last `months` months.

    With a category, also returns that category's month-by-month totals and
    top merchants.
    """
    months = max(1, min(int(months), 24))
    tx = _last_months(_tx(customer_id), months)
    result: dict = {"months": months, "until": data_end_date().isoformat()}
    if category is None:
        by_cat = _spending_by_category(tx)
        result["total_eur"] = _r(sum(by_cat.values()))
        result["by_category_eur"] = by_cat
        return result

    cat = _match_category(category)
    sel = tx[tx["category"] == cat]
    per_month = (-sel.groupby(sel["tx_date"].dt.to_period("M"))["tx_amount_eur"].sum()).round(2)
    merchants = (
        -sel.groupby("merchant_id", observed=True)["tx_amount_eur"].sum()
    ).sort_values(ascending=False).head(5)
    result.update(
        {
            "category": cat,
            "total_eur": _r(-sel["tx_amount_eur"].sum()),
            "transactions": len(sel),
            "per_month_eur": {str(k): v for k, v in per_month.items()},
            "top_merchants_eur": {k: _r(v) for k, v in merchants.items() if v},
        }
    )
    return result


def get_monthly_trend(customer_id: str, months: int = 12) -> dict:
    """Month-by-month income, spending, investing, net cash flow, end balance."""
    months = max(1, min(int(months), 24))
    table = _monthly_table(_last_months(_tx(customer_id), months))
    table.index = table.index.astype(str)
    return {"months": table.reset_index(names="month").to_dict(orient="records")}


def compare_to_peers(customer_id: str, category: str | None = None) -> dict:
    """Spending vs similar users. Without a category: the biggest differences."""
    _tx(customer_id)  # 404 check
    if category is None:
        return get_insights(customer_id, limit=5)
    cat = _match_category(category)
    comp = get_comparison(customer_id)
    row = comp[comp["category"] == cat]
    if row.empty:
        return {"error": f"No peer comparison for {cat}. Available: {SPENDING_CATEGORIES}"}
    return {**get_profile(customer_id), **row.iloc[0].to_dict()}


def find_transactions(
    customer_id: str,
    category: str | None = None,
    merchant_id: str | None = None,
    start: str | None = None,
    end: str | None = None,
    min_amount_eur: float | None = None,
    sort: str = "recent",
    limit: int = 20,
) -> dict:
    """Search transactions. sort: 'recent' or 'largest' (biggest outflows)."""
    tx = _tx(customer_id)
    if category:
        tx = tx[tx["category"] == _match_category(category)]
    if merchant_id:
        tx = tx[tx["merchant_id"] == merchant_id]
    if start:
        tx = tx[tx["tx_date"] >= pd.Timestamp(start)]
    if end:
        tx = tx[tx["tx_date"] <= pd.Timestamp(end)]
    if min_amount_eur is not None:
        tx = tx[tx["tx_amount_eur"].abs() >= float(min_amount_eur)]
    tx = (
        tx.sort_values("tx_amount_eur")
        if sort == "largest"
        else tx.sort_values("tx_timestamp", ascending=False)
    )
    limit = max(1, min(int(limit), 50))
    cols = ["tx_date", "category", "tx_amount_eur", "merchant_id", "balance_after_eur"]
    rows = tx[cols].head(limit).assign(tx_date=lambda d: d["tx_date"].dt.date.astype(str))
    return {
        "matches": len(tx),
        "shown": len(rows),
        "transactions": rows.astype(object).where(rows.notna(), None).to_dict(orient="records"),
    }


def get_mortgage_status(customer_id: str) -> dict:
    """The customer's mortgage application: outcome and recent events."""
    outcomes = load_mortgage_outcomes()
    rows = outcomes[outcomes["customer_id"] == customer_id]
    if rows.empty:
        _tx(customer_id)  # 404 check
        return {"has_mortgage_application": False}
    outcome = rows.iloc[0]
    events = load_mortgage_events()
    ev = events[events["mortgage_customer_id"] == outcome["mortgage_customer_id"]]
    keep = ["timestamp", "event_type", "note"]
    recent = ev[keep].tail(8).assign(timestamp=lambda d: d["timestamp"].dt.date.astype(str))
    clean = outcome.astype(object).where(outcome.notna(), None).to_dict()
    return {
        "has_mortgage_application": True,
        **clean,
        "application_started": ev["timestamp"].min().date().isoformat(),
        "event_count": len(ev),
        "recent_events": recent.to_dict(orient="records"),
    }


def _match_category(name: str) -> str:
    """Case-insensitive category lookup, so 'groceries' -> 'Groceries'."""
    all_cats = list(load_transactions()["category"].cat.categories)
    for c in all_cats:
        if c.lower() == name.strip().lower():
            return c
    raise ValueError(f"Unknown category {name!r}. Categories: {all_cats}")


def demo_customers(limit: int = 10) -> list[dict]:
    """Good customers to demo with: full transaction history, some with mortgages."""
    from .insights import peer_data

    profiles = peer_data().profiles
    # Most card purchases first: their spending is most complete in this data.
    active = profiles[~profiles["low_activity"]].sort_values(
        "purchases_per_month", ascending=False
    )
    mortgage = load_mortgage_outcomes().set_index("customer_id")["final_decision"]
    picked = pd.concat(
        [
            active[active.index.isin(mortgage.index)].head(limit // 2),
            active[~active.index.isin(mortgage.index)].head(limit - limit // 2),
        ]
    )
    return [
        {
            "customer_id": cid,
            "age": int(row["customer_age"]),
            "peer_group": row["peer_group"],
            "mortgage_decision": mortgage.get(cid),
        }
        for cid, row in picked.iterrows()
    ]


# --- Mortgage: benchmarks, explanations and a what-if calculator -------------

# Rules of thumb used for teaching. Not S-Pankki's actual credit policy.
LTV_LIMIT = 0.90  # Finnish loan cap: loan at most 90% of collateral value
LTV_LIMIT_FIRST_HOME = 0.95
STRESS_RATE_PCT = 6.0  # common stress-test rate in Finland
STRESS_YEARS = 25
EXAMPLE_RATE_PCT = 4.0  # illustrative, not a quote
# In this dataset the bank's required income is always this share of the loan.
REQUIRED_INCOME_PER_LOAN_EUR = 0.0184

REJECTION_REASONS = {
    "insufficient_collateral": {
        "title": "Not enough collateral",
        "meaning": "The value the bank could count as security (the home and any "
        "other collateral) was too low compared with the loan.",
        "what_helps": "A smaller loan, a larger down payment, or extra collateral "
        "such as a guarantee.",
    },
    "insufficient_income": {
        "title": "Income too low for the loan",
        "meaning": "Your regular income was below what the bank requires to repay "
        "this loan safely, also if interest rates rise.",
        "what_helps": "A smaller loan, a longer repayment time, or applying together "
        "with a co-borrower.",
    },
    "insufficient_equity": {
        "title": "Down payment too small",
        "meaning": "Your own money covered too small a share of the price, so the "
        "loan would have been too large compared with the home's value.",
        "what_helps": "Saving a larger down payment or choosing a cheaper home.",
    },
    "existing_debt": {
        "title": "Existing debt too high",
        "meaning": "Together with your current loans, the new loan would have made "
        "your total debt too heavy for your income.",
        "what_helps": "Paying down existing loans first, or a smaller mortgage.",
    },
}


def _annuity(loan: float, rate_pct: float, years: int) -> float:
    """Monthly payment of an annuity loan."""
    n = years * 12
    r = rate_pct / 100 / 12
    return loan / n if r == 0 else loan * r / (1 - (1 + r) ** -n)


@lru_cache(maxsize=1)
def mortgage_benchmarks() -> dict:
    """How mortgage applications in the data turned out (anonymous aggregates)."""
    o = load_mortgage_outcomes()
    approved = o[o["final_decision"] == "approved"]
    return {
        "applications": len(o),
        "approved_pct": round(len(approved) / len(o) * 100),
        "median_ltv_approved": round(float(approved["final_loan_to_value"].median()), 3),
        "median_down_payment_pct_approved": round(
            float(
                (approved["final_equity_amount_eur"] / approved["final_property_price_eur"])
                .median()
                * 100
            ),
            1,
        ),
        "median_property_price_eur": _r(o["final_property_price_eur"].median()),
        "rejection_reasons": o["rejection_reason"].value_counts().to_dict(),
    }


def get_mortgage_details(customer_id: str) -> dict:
    """get_mortgage_status plus teaching context: explanation, benchmarks, income check."""
    status = get_mortgage_status(customer_id)
    if not status["has_mortgage_application"]:
        return status
    income = get_overview(customer_id)["avg_monthly_income_eur"]
    reason = status.get("rejection_reason")
    status.update(
        {
            "your_avg_monthly_income_eur": income,
            "ltv_limit": LTV_LIMIT,
            "rejection_explained": REJECTION_REASONS.get(reason) if reason else None,
            "all_applicants_in_data": mortgage_benchmarks(),
        }
    )
    return status


def mortgage_calculator(
    customer_id: str,
    property_price_eur: float,
    down_payment_eur: float | None = None,
    years: int = 25,
    interest_rate_pct: float = EXAMPLE_RATE_PCT,
) -> dict:
    """What-if estimate for buying a home. For learning, not a loan offer."""
    price = float(property_price_eur)
    if not 20_000 <= price <= 5_000_000:
        raise ValueError("property_price_eur must be between 20 000 and 5 000 000")
    years = max(5, min(int(years), 35))
    rate = max(0.0, min(float(interest_rate_pct), 15.0))
    overview = get_overview(customer_id)
    balance = overview["current_balance_eur"]
    min_down = price * (1 - LTV_LIMIT)
    if down_payment_eur is None:
        # Assume they'd use their balance, but at least the minimum.
        down, assumed = max(min_down, min(balance, price * 0.3)), True
    else:
        down, assumed = max(0.0, min(float(down_payment_eur), price)), False
    loan = price - down
    income = overview["avg_monthly_income_eur"]
    payment = _annuity(loan, rate, years)
    stress = _annuity(loan, STRESS_RATE_PCT, STRESS_YEARS)
    required_income = loan * REQUIRED_INCOME_PER_LOAN_EUR
    ltv = loan / price
    housing_now = _spending_by_category(_last_months(_tx(customer_id), 12)).get("Housing", 0) / 12
    return {
        "estimate_only": "Rough estimate for learning. Not a loan offer or decision.",
        "property_price_eur": _r(price),
        "down_payment_eur": _r(down),
        "down_payment_assumed": assumed,
        "minimum_down_payment_eur": _r(min_down),
        "loan_eur": _r(loan),
        "loan_to_value": round(ltv, 3),
        "ltv_limit": LTV_LIMIT,
        "ltv_ok": ltv <= LTV_LIMIT + 1e-9,
        "years": years,
        "interest_rate_pct": rate,
        "monthly_payment_eur": _r(payment),
        "stress_test": {
            "rate_pct": STRESS_RATE_PCT,
            "years": STRESS_YEARS,
            "monthly_payment_eur": _r(stress),
        },
        "your_avg_monthly_income_eur": income,
        "payment_share_of_income_pct": round(payment / income * 100, 1) if income else None,
        "required_monthly_income_eur": _r(required_income),
        "income_ok": income >= required_income,
        "your_current_housing_cost_eur": _r(housing_now),
        "your_balance_eur": balance,
        "savings_cover_down_payment": balance >= down,
        "max_loan_for_your_income_eur": _r(income / REQUIRED_INCOME_PER_LOAN_EUR),
        # The most expensive home their income supports with a 10% down payment.
        "max_price_for_your_income_eur": _r(income / REQUIRED_INCOME_PER_LOAN_EUR / LTV_LIMIT),
        "down_payment_needed_for_that_eur": _r(
            income / REQUIRED_INCOME_PER_LOAN_EUR / LTV_LIMIT * (1 - LTV_LIMIT)
        ),
        "all_applicants_in_data": {
            k: mortgage_benchmarks()[k]
            for k in ("approved_pct", "median_ltv_approved", "median_down_payment_pct_approved")
        },
    }


# --- Saving and investing ------------------------------------------------------

# General, neutral points the assistant may use. Not advice, no products.
INVESTING_BASICS = [
    "Before investing, many people keep a buffer for surprises on an account they can "
    "use straight away. How big it should be is personal.",
    "Investing suits money you won't need for several years. The value goes up and down, "
    "and you can lose money.",
    "Spreading money over many investments (diversification) lowers the risk that one of "
    "them fails.",
    "Costs and fees eat into returns, so they are worth comparing.",
    "Investing a fixed amount regularly evens out the effect of timing.",
]
INVESTING_DISCLAIMER = (
    "General information, not investment advice. For advice that fits your situation, "
    "talk to an S-Pankki advisor."
)


def get_investing_summary(customer_id: str) -> dict:
    """The customer's own saving and investing figures, plus general basics."""
    year = _last_months(_tx(customer_id), 12)
    deposits = year[year["category"] == "Invest Deposit"]
    withdrawn = float(year.loc[year["category"] == "Invest Withdraw", "tx_amount_eur"].sum())
    invested = float(-deposits["tx_amount_eur"].sum())
    overview = get_overview(customer_id)
    income = overview["avg_monthly_income_eur"]
    spending = overview["avg_monthly_spending_eur"]
    balance = overview["current_balance_eur"]
    return {
        "invests_from_this_account": invested > 0,
        "invested_last_12_months_eur": _r(invested) + 0.0,
        "withdrawn_from_investments_last_12_months_eur": _r(withdrawn),
        "avg_monthly_invested_eur": _r(invested / 12) + 0.0,
        "months_with_an_investment": int(deposits["tx_date"].dt.to_period("M").nunique()),
        "invested_share_of_income_pct": round(invested / 12 / income * 100, 1) if income else None,
        "avg_monthly_income_eur": income,
        "avg_monthly_spending_eur": spending,
        # What is left after spending and investing, on average.
        "avg_monthly_left_on_account_eur": _r(income - spending - invested / 12),
        "balance_eur": balance,
        "balance_covers_months_of_spending": round(balance / spending, 1) if spending else None,
        "general_basics": INVESTING_BASICS,
        "disclaimer": INVESTING_DISCLAIMER,
    }
