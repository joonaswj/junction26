"""Chart specs for the app, built from the customer's real data.

The chatbot never writes numbers into charts. It only asks for a chart by
name (a tag like [[chart:spending]] or by calling a tool), and the spec is
built here from the data. The frontend draws each `type`:

    bars      horizontal bars, one value per label
    columns   columns over months, 1-2 series
    line      one value over months
    compare   you vs similar customers, per category
    mortgage  the customer's own mortgage application
    calc      what-if mortgage estimate
"""

from __future__ import annotations

from . import finance
from .insights import SPENDING_CATEGORIES, get_comparison, get_profile
from .suggestions import question_for


def _direction(row) -> str:
    return "more" if row["you_eur"] > row["peer_median_eur"] else "less"


def _peer_text(peer_group: str) -> str:
    if peer_group.startswith("age "):
        age = peer_group.split(",")[0].removeprefix("age ").replace("-", "–")
        return f"customers aged {age} with a similar income"
    return "customers with a similar income"


def spending(customer_id: str, months: int = 3) -> dict:
    data = finance.get_spending(customer_id, months)
    return {
        "type": "bars",
        "title": "Where your money goes",
        "subtitle": f"Last {data['months']} months, total",
        "total": data["total_eur"],
        "items": [{"label": k, "value": v} for k, v in data["by_category_eur"].items()],
        "explore": {"group_by": "category", "months": data["months"]},
    }


def category_trend(customer_id: str, category: str, months: int = 12) -> dict:
    data = finance.get_spending(customer_id, months, category)
    # Fill months with no spending so the time axis has no holes.
    trend = finance.get_monthly_trend(customer_id, months)["months"]
    labels = [m["month"] for m in trend]
    values = [data["per_month_eur"].get(m, 0.0) for m in labels]
    return {
        "type": "columns",
        "title": f"{data['category']} per month",
        "subtitle": f"Last {len(labels)} months, average",
        "total": round(sum(values) / len(values), 2) if values else 0,
        "labels": labels,
        "series": [{"name": data["category"], "values": values}],
        "explore": {"group_by": "month", "months": len(labels),
                    "categories": [data["category"]]},
    }


def income_vs_spending(customer_id: str, months: int = 6) -> dict:
    trend = finance.get_monthly_trend(customer_id, months)["months"]
    return {
        "type": "columns",
        "title": "Income and spending",
        "subtitle": f"Last {len(trend)} months",
        "labels": [m["month"] for m in trend],
        "series": [
            {"name": "Income", "values": [m["income"] for m in trend]},
            {"name": "Spending", "values": [m["spending"] for m in trend]},
        ],
        "explore": {"measure": "saved", "months": len(trend)},
    }


def balance(customer_id: str, months: int = 12) -> dict:
    trend = finance.get_monthly_trend(customer_id, months)["months"]
    return {
        "type": "line",
        "title": "Your balance",
        "subtitle": f"End of each month, last {len(trend)} months",
        "labels": [m["month"] for m in trend],
        "values": [m["end_balance"] for m in trend],
        "explore": {"measure": "balance", "months": len(trend)},
    }


def peers(customer_id: str, category: str | None = None) -> dict:
    profile = get_profile(customer_id)
    comp = get_comparison(customer_id)
    spec = {
        "type": "compare",
        "title": "You and similar customers",
        "subtitle": f"Average per month, last 12 months. Compared with "
        f"{profile['peer_count']} {_peer_text(profile['peer_group'])}.",
        "you_label": "You",
        "peer_label": "Typical similar customer",
        "explore": {"group_by": "category", "months": 12, "compare": "peers",
                    **({"categories": [finance._match_category(category)]} if category else {})},
    }
    if category:
        cat = finance._match_category(category)
        row = comp[comp["category"] == cat]
        if row.empty:
            raise ValueError(f"No comparison for {cat}. Try one of {SPENDING_CATEGORIES}")
        r = row.iloc[0]
        spec["title"] = f"{cat}: you and similar customers"
        spec["items"] = [{"label": cat, "you": r["you_eur"], "peers": r["peer_median_eur"],
                          "question": question_for(cat, _direction(r))}]
        spec["percentile"] = int(r["percentile"])
        return spec
    # Biggest differences first, so the chart tells the story top-down.
    comp = comp.reindex(comp["diff_eur"].abs().sort_values(ascending=False).index).head(6)
    spec["items"] = [
        {"label": r["category"], "you": r["you_eur"], "peers": r["peer_median_eur"],
         "question": question_for(r["category"], _direction(r))}
        for _, r in comp.iterrows()
    ]
    return spec


def mortgage(customer_id: str) -> dict | None:
    d = finance.get_mortgage_details(customer_id)
    if not d["has_mortgage_application"]:
        return None
    return {
        "type": "mortgage",
        "title": "Your mortgage application",
        "decision": d["final_decision"],
        "reason": d["rejection_explained"],
        "property_price": d["final_property_price_eur"],
        "loan": d["final_requested_loan_eur"],
        "down_payment": d["final_equity_amount_eur"],
        "ltv": round(float(d["final_loan_to_value"]), 3),
        "ltv_limit": d["ltv_limit"],
        "ltv_typical_approved": d["all_applicants_in_data"]["median_ltv_approved"],
        "approved_pct": d["all_applicants_in_data"]["approved_pct"],
    }


def calc(result: dict) -> dict:
    """Spec for a finance.mortgage_calculator result."""
    return {
        "type": "calc",
        "title": "Home loan estimate",
        "property_price": result["property_price_eur"],
        "down_payment": result["down_payment_eur"],
        "down_payment_assumed": result["down_payment_assumed"],
        "loan": result["loan_eur"],
        "ltv": result["loan_to_value"],
        "ltv_limit": result["ltv_limit"],
        "years": result["years"],
        "rate_pct": result["interest_rate_pct"],
        "monthly_payment": result["monthly_payment_eur"],
        "stress_payment": result["stress_test"]["monthly_payment_eur"],
        "stress_rate_pct": result["stress_test"]["rate_pct"],
        "income": result["your_avg_monthly_income_eur"],
        "required_income": result["required_monthly_income_eur"],
        "current_housing_cost": result["your_current_housing_cost_eur"],
        "balance": result["your_balance_eur"],
        "max_price_for_income": result["max_price_for_your_income_eur"],
        "note": result["estimate_only"],
    }


def finland(customer_id: str, category: str | None = None) -> dict | None:
    """You vs the Finnish average for your age (Statistics Finland)."""
    from .explore import explore

    cats = [category] if category else None
    result = explore(customer_id, group_by="category", months=12, categories=cats,
                     compare="finland")
    if not result["visual"]["items"]:
        return None
    return from_explore(result)


def from_explore(result: dict) -> dict:
    """The chart of an explore() result, with a link back to the same view."""
    q = result["query"]
    link = {k: v for k, v in q.items() if k != "categories"}
    if len(q["categories"]) < len(result["options"]["categories"]):
        link["categories"] = q["categories"]
    return {**result["visual"], "explore": link, "notes": result["notes"],
            "source": result["source"]}


def from_tag(customer_id: str, tag: str) -> dict | None:
    """Build a chart from a tag body like 'spending' or 'category:Groceries'.

    Returns None for unknown tags or bad arguments: a missing chart is better
    than an error in the middle of an answer.
    """
    kind, _, arg = tag.strip().partition(":")
    arg = arg.strip() or None
    try:
        match kind.strip().lower():
            case "spending":
                return spending(customer_id)
            case "category" if arg:
                return category_trend(customer_id, arg)
            case "income_vs_spending":
                return income_vs_spending(customer_id)
            case "balance":
                return balance(customer_id)
            case "peers":
                return peers(customer_id, arg)
            case "mortgage":
                return mortgage(customer_id)
            case "finland":
                return finland(customer_id, arg)
    except (ValueError, KeyError):
        return None
    return None


def from_tool(customer_id: str, name: str, args: dict, result: dict) -> dict | None:
    """The chart that goes with a tool call, if any."""
    if "error" in result:
        return None
    try:
        match name:
            case "get_spending":
                if args.get("category"):
                    return category_trend(customer_id, args["category"])
                return spending(customer_id, int(args.get("months") or 3))
            case "get_monthly_trend":
                return income_vs_spending(customer_id)
            case "compare_to_peers":
                return peers(customer_id, args.get("category"))
            case "get_mortgage_status":
                return mortgage(customer_id)
            case "mortgage_calculator":
                return calc(result)
            case "explore_data":
                return from_explore(result) if result.get("visual") else None
    except (ValueError, KeyError, TypeError):
        return None
    return None
