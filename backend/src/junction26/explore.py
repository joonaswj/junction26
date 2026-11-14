"""Free exploration of the customer's own data (MyData spirit).

Instead of fixed charts, the customer chooses what to look at:

    measure     spending | income | saved | balance
    group_by    month | category | merchant | weekday   (spending only)
    months      1-24, how far back
    categories  which spending categories (default: all)
    compare     none | peers | finland                  (spending by month/category)

explore() answers any combination with a chart spec, the same numbers as a
table, a one-sentence takeaway, notes on where benchmarks come from, and
questions to hand over to the assistant about exactly this view.
"""

from __future__ import annotations

import re
from functools import lru_cache

import pandas as pd

from . import costs, finance, household, opendata
from .data import load_transactions
from .insights import SPENDING_CATEGORIES, _peers, peer_data
from .suggestions import adjective, question_for

MEASURES = ["spending", "income", "saved", "balance"]
GROUPS = ["category", "type", "month", "merchant", "weekday"]
COMPARES = ["none", "peers", "finland"]
PERIODS = [3, 6, 12, 24]
WEEKDAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

LABELS = {
    "spending": "Spending",
    "income": "Income",
    "saved": "Saved (income minus spending)",
    "balance": "Balance",
}


def _eur(amount: float) -> str:
    return f"{amount:,.0f}".replace(",", " ") + " €"


def _window(months: int, month: str | None = None):
    """All customers' transactions in the period, its month labels, start and end.

    `month` ("2026-01") narrows the period to that one calendar month.
    """
    tx = load_transactions()
    if month:
        start = pd.Timestamp(f"{month}-01")
        end = start + pd.offsets.MonthEnd(0)
        tx = tx[(tx["tx_date"] >= start) & (tx["tx_date"] <= end)]
        return tx, [month], start, end
    end = pd.Timestamp(finance.data_end_date())
    start = end - pd.DateOffset(months=months) + pd.Timedelta(days=1)
    tx = tx[tx["tx_date"] >= start]
    labels = [str(p) for p in pd.period_range(end=end, periods=months, freq="M")]
    return tx, labels, start, end


def _peer_ids(customer_id: str) -> tuple[str, ...]:
    profiles = peer_data().profiles
    return tuple(_peers(profiles, profiles.loc[customer_id]).index)


@lru_cache(maxsize=64)
def _peer_median(peer_ids: tuple[str, ...], categories: tuple[str, ...], months: int,
                 by: str, month: str | None = None) -> dict[str, float]:
    """Typical (median) similar customer: spending per month or per category."""
    tx, labels, _, _ = _window(months, month)
    sub = tx[tx["customer_id"].isin(peer_ids) & tx["category"].isin(categories)]
    key = sub["tx_date"].dt.to_period("M").astype(str) if by == "month" else sub["category"]
    table = (
        (-sub["tx_amount_eur"])
        .groupby([sub["customer_id"], key], observed=True)
        .sum()
        .unstack(fill_value=0.0)
        .reindex(index=list(peer_ids), fill_value=0.0)
    )
    columns = labels if by == "month" else list(categories)
    table = table.reindex(columns=columns, fill_value=0.0)
    if by == "category":
        table = table / months  # average per month
    return {str(k): round(float(v), 2) for k, v in table.median().items()}


def _valid_month(month: str | None) -> str | None:
    """'2026-01' if it is a month inside the data, else None."""
    if not month or not re.fullmatch(r"\d{4}-(0[1-9]|1[0-2])", str(month)):
        return None
    tx = load_transactions()
    first, last = tx["tx_date"].min().strftime("%Y-%m"), tx["tx_date"].max().strftime("%Y-%m")
    return month if first <= month <= last else None


def _clean(measure, group_by, months, categories, compare, month=None) -> dict:
    month = _valid_month(month)
    measure = measure if measure in MEASURES else "spending"
    if month:
        # One month: always spending, sliced inside the month.
        measure = "spending"
        group_by = (group_by if group_by in ("category", "type", "merchant", "weekday")
                    else "category")
        months = 1
    if measure != "spending":
        group_by, compare, categories = "month", "none", None
    group_by = group_by if group_by in GROUPS else "category"
    months = max(1, min(int(months or 3), 24))
    cats = [finance._match_category(c) for c in (categories or [])]
    cats = [c for c in SPENDING_CATEGORIES if c in cats] or list(SPENDING_CATEGORIES)
    compare = compare if compare in COMPARES else "none"
    if group_by in ("type", "merchant", "weekday"):
        compare = "none"
    return {"measure": measure, "group_by": group_by, "months": months,
            "categories": cats, "compare": compare, "month": month}


def _scope(cats: list[str]) -> str:
    """'spending' / 'groceries spending' / 'groceries and travel spending'."""
    if len(cats) == len(SPENDING_CATEGORIES):
        return "spending"
    names = [adjective(c) for c in cats]
    joined = names[0] if len(names) == 1 else ", ".join(names[:-1]) + " and " + names[-1]
    return f"{joined} spending"


def _peer_question(scope: str, all_selected: bool) -> str:
    if all_selected:
        return "Where do I spend more than similar customers?"
    return f"How does my {scope} compare with similar customers?"


def _finland_question(cats: list[str], all_selected: bool) -> str:
    if all_selected or len(cats) > 2:
        return "How do I compare with the Finnish average for my age?"
    return f"How does my {_scope(cats)} compare with the Finnish average?"


def explore(
    customer_id: str,
    measure: str = "spending",
    group_by: str = "category",
    months: int = 3,
    categories: list[str] | None = None,
    compare: str = "none",
    month: str | None = None,
) -> dict:
    q = _clean(measure, group_by, months, categories, compare, month)
    months, cats, month = q["months"], q["categories"], q["month"]
    profile = finance.get_profile(customer_id)  # KeyError if unknown
    tx_all, labels, start, end = _window(months, month)
    tx = tx_all[tx_all["customer_id"] == customer_id]
    if month:
        period = the_period = pd.Timestamp(f"{month}-01").strftime("%B %Y")
    else:
        period = f"last {months} months" if months > 1 else "last month"
        the_period = "the " + period
    notes: list[str] = []
    source = None
    scope = _scope(cats)
    all_cats = len(cats) == len(SPENDING_CATEGORIES)

    # ---- Benchmarks, shared by "month" and "category" views
    peer_label = f"Typical similar customer ({profile['peer_count']} people)"
    # With household details the benchmark is "households like yours" and the
    # customer's shared costs are put on the same per-person footing.
    home = household.get(customer_id)
    national = opendata.national_spending(
        profile["age"], (home.partner, home.children) if home else None
    )
    fin_label = f"Finnish average, {national['group']}"
    you_label = "You"

    def factor(category: str) -> float:
        return household.per_person_factor(category, home)

    def per_person_by_month(used: list[str]) -> list[float]:
        """The customer's spending per month in `used`, per person in the household."""
        sub = tx[tx["category"].isin(used)]
        table = (
            (-sub["tx_amount_eur"])
            .groupby([sub["tx_date"].dt.to_period("M").astype(str), sub["category"]],
                     observed=True)
            .sum()
            .unstack(fill_value=0.0)
            .reindex(index=labels, fill_value=0.0)
        )
        return [round(float(sum(row.get(c, 0.0) * factor(c) for c in used)), 2)
                for _, row in table.iterrows()]

    def add_finland_notes(used: list[str], skipped: list[str]) -> None:
        nonlocal source
        source = opendata.source()
        whom = (national["group"] if national["by"] == "household"
                else f"households where the main earner is {national['age_group']}")
        notes.append(
            f"Finnish average: {source['source']} {source['year']}, spending per person "
            f"(consumption unit) for {whom}. Categories are matched approximately."
        )
        if home and any(factor(c) != 1 for c in used):
            for c in (c for c in used if factor(c) != 1):
                how = (f"scaled up to your whole household (you said your partner pays about "
                       f"{home.partner_share_pct(c)} %) and " if home.partner else "")
                notes.append(
                    f"Your {c.lower()} are {how}divided by your household's size "
                    f"({home.consumption_units:.1f} consumption units: first adult 1, second "
                    "adult 0.5, each child 0.3), so both sides are per person. Other costs are "
                    "shown as they are."
                )
        for c in used:
            if national["categories"][c]["caveat"]:
                notes.append(f"{c}: {national['categories'][c]['caveat']}")
        for c in skipped:
            notes.append(national["categories"][c]["caveat"])

    def add_peer_note() -> None:
        notes.append(
            f"Similar customers: {profile['peer_count']} S-Pankki customers in the same "
            f"group ({profile['peer_group']}). The figure is the median: half spend more, "
            "half spend less."
        )

    if q["measure"] != "spending":
        trend = finance.get_monthly_trend(customer_id, months)["months"]
        by_month = {m["month"]: m for m in trend}
        field = {"income": "income", "saved": "net", "balance": "end_balance"}[q["measure"]]
        values = [by_month.get(m, {}).get(field) for m in labels]
        if q["measure"] == "saved":
            values = [
                round(by_month[m]["income"] - by_month[m]["spending"], 2) if m in by_month else 0.0
                for m in labels
            ]
        values = [v if v is not None else 0.0 for v in values]
        title = LABELS[q["measure"]]
        if q["measure"] == "balance":
            visual = {"type": "line", "title": "Your balance",
                      "subtitle": f"End of each month, {period}", "labels": labels,
                      "values": values}
            change = values[-1] - values[0]
            summary = (f"Your balance went {'up' if change >= 0 else 'down'} by "
                       f"{_eur(abs(change))} over {the_period}.")
            questions = ["Is my balance growing?", "How much do I save each month?"]
        else:
            avg = sum(values) / len(values)
            visual = {"type": "columns", "title": title, "subtitle": f"{period[0].upper() + period[1:]}, average",
                      "total": round(avg, 2), "labels": labels,
                      "series": [{"name": title.split(" (")[0], "values": values}]}
            if q["measure"] == "income":
                summary = f"You earned {_eur(avg)} a month on average over {the_period}."
                questions = ["How has my income changed?", "How much of my income do I keep?"]
            else:
                good = sum(v > 0 for v in values)
                summary = (f"You kept {_eur(avg)} a month on average, and came out ahead in "
                           f"{good} of {len(values)} months.")
                questions = ["How much do I save each month?",
                             "In which months did I spend more than I earned?"]
        table = {"columns": ["Month", title], "rows": [[m, v] for m, v in zip(labels, values)]}

    elif q["group_by"] == "month":
        sel = tx[tx["category"].isin(cats)]
        mine = (-sel["tx_amount_eur"]).groupby(sel["tx_date"].dt.to_period("M").astype(str)).sum()
        values = [round(float(mine.get(m, 0.0)), 2) for m in labels]
        avg = sum(values) / len(values)
        series = [{"name": "You", "values": values}]
        table = {"columns": ["Month", "You"], "rows": [[m, v] for m, v in zip(labels, values)]}
        summary = f"Your {scope} averaged {_eur(avg)} a month over {the_period}."
        questions = [f"How has my {scope} changed over {the_period}?"]
        colors = ["s1"]
        if q["compare"] == "peers":
            peers = _peer_median(_peer_ids(customer_id), tuple(cats), months, "month", month)
            pv = [peers[m] for m in labels]
            series.append({"name": peer_label, "values": pv})
            colors.append("peer")
            table["columns"].append("Typical similar customer")
            for row, v in zip(table["rows"], pv):
                row.append(v)
            above = sum(a > b for a, b in zip(values, pv))
            summary += f" You were above the typical similar customer in {above} of {months} months."
            questions.insert(0, _peer_question(scope, all_cats))
            add_peer_note()
        elif q["compare"] == "finland":
            used = [c for c in cats if national["categories"].get(c, {}).get("comparable")]
            skipped = [c for c in cats if c in national["categories"]
                       and not national["categories"][c]["comparable"]]
            if used:
                level = round(sum(national["categories"][c]["eur"] for c in used), 2)
                series.append({"name": fin_label, "values": [level] * len(labels)})
                colors.append("s2")
                table["columns"].append("Finnish average")
                for row in table["rows"]:
                    row.append(level)
                # Compare like with like: only comparable categories, per person.
                series[0]["values"] = per_person_by_month(used)
                if home and any(factor(c) != 1 for c in used):
                    series[0]["name"] = "You, per person"
                    table["columns"][1] = "You, per person"
                for row, v in zip(table["rows"], series[0]["values"]):
                    row[1] = v
                my_avg = sum(series[0]["values"]) / len(labels)
                diff = my_avg - level
                summary = (
                    f"You spend {_eur(abs(diff))} {'more' if diff > 0 else 'less'} a month than "
                    f"the Finnish average for {national['group']} ({_eur(my_avg)} vs "
                    f"{_eur(level)})."
                )
                questions.insert(0, _finland_question(used, all_cats))
            add_finland_notes(used, skipped)
        visual = {
            "type": "columns",
            "title": f"{scope.capitalize()} by month",
            "subtitle": f"{period[0].upper() + period[1:]}, your average",
            "total": round(sum(series[0]["values"]) / len(labels), 2),
            "labels": labels,
            "series": series,
            "colors": colors,
        }
        if q["compare"] == "none":
            # The customer's own normal, to read a heavy or light month against.
            normal = round(sum(costs.usual(customer_id)[c] for c in cats), 2)
            visual["reference"] = {"label": "Your usual month (12-month average)",
                                   "value": normal}

    elif q["group_by"] in ("category", "type"):
        by_type = q["group_by"] == "type"
        usual = costs.usual(customer_id)  # the customer's 12-month average per category
        if month:
            # Inside one month the real amounts are the point. "usual" lets a
            # heavy month be read against the customer's own normal.
            sel = tx[tx["category"].isin(cats)]
            sums = (-sel["tx_amount_eur"]).groupby(sel["category"], observed=True).sum()
            monthly = {c: round(float(sums.get(c, 0.0)), 2) for c in cats}
            basis = {c: 1 for c in cats}
            unit = "total"
        else:
            # Per month, each category on the basis that makes sense for it:
            # essentials that vary are always the 12-month average.
            figures = costs.monthly_figures(customer_id, months)
            monthly = {c: figures[c]["eur"] for c in cats}
            basis = {c: figures[c]["basis_months"] for c in cats}
            unit = "a month"
            smoothed = [c for c in cats if costs.uses_yearly_average(c)]
            if smoothed and months != costs.YEAR:
                notes.append(
                    f"Essentials that vary ({', '.join(c.lower() for c in smoothed)}) are your "
                    "12-month average, whatever period you pick, so one heavy month doesn't "
                    "distort the picture. Other costs are the average of the selected period."
                )
        total = round(sum(monthly.values()), 2)
        groups = [
            {"key": key, "label": info["label"], "description": info["description"],
             "value": round(sum(monthly[c] for c in info["categories"] if c in monthly), 2),
             "categories": [c for c in info["categories"] if c in monthly]}
            for key, info in costs.COST_TYPES.items()
        ]
        groups = [g for g in groups if g["categories"]]
        when = f"in {period}" if month else "in an average month"

        if q["compare"] == "none" and by_type:
            visual = {"type": "bars", "title": f"{scope.capitalize()} by cost type",
                      "subtitle": f"{period if month else 'An average month'}, total".capitalize(),
                      "total": total,
                      "items": [{"label": g["label"], "value": g["value"], "key": g["key"],
                                 "categories": g["categories"], "note": g["description"]}
                                for g in groups]}
            table = {"columns": ["Cost type", "Per month" if not month else "Total", "Categories"],
                     "rows": [[g["label"], g["value"], ", ".join(g["categories"])] for g in groups]}
            parts = ", ".join(f"{_eur(g['value'])} on {g['label'].lower()}" for g in groups)
            summary = f"You {'spent' if month else 'spend'} {_eur(total)} {when}: {parts}."
            free = next((g for g in groups if g["key"] == "free"), None)
            questions = ["How is my spending split between needs and wants?"]
            if free and free["value"] > 0:
                questions.append("How could I reduce my free-choice spending?")
        elif q["compare"] == "none":
            items = []
            for g in groups:
                for c in sorted(g["categories"], key=lambda c: -monthly[c]):
                    item = {"label": c, "value": monthly[c], "group": g["key"]}
                    if month and usual.get(c):
                        item["usual"] = usual[c]
                    items.append(item)
            visual = {"type": "bars", "title": f"{scope.capitalize()} by category",
                      "subtitle": f"{period if month else 'An average month'}, total".capitalize(),
                      "total": total,
                      "groups": [{k: g[k] for k in ("key", "label", "value")} for g in groups],
                      "items": [i for i in items if i["value"] > 0 or not month]}
            if month:
                table = {"columns": ["Category", "Cost type", f"Total, {period}", "Your usual month"],
                         "rows": [[i["label"], costs.COST_TYPES[i["group"]]["label"], i["value"],
                                   usual.get(i["label"], 0.0)] for i in items]}
                normal = round(sum(usual[c] for c in cats), 2)
                diff = total - normal
                summary = (
                    f"You spent {_eur(total)} in {period}, {_eur(abs(diff))} "
                    f"{'more' if diff > 0 else 'less'} than your usual month ({_eur(normal)})."
                )
                heavy = max(items, key=lambda i: i["value"] - usual.get(i["label"], 0.0), default=None)
                if heavy and heavy["value"] - usual.get(heavy["label"], 0.0) > 50:
                    summary += (
                        f" {heavy['label']} stood out: {_eur(heavy['value'])} against a usual "
                        f"{_eur(usual[heavy['label']])}."
                    )
                questions = [f"What did I spend on in {period}?",
                             f"Was {period} a normal month for me?"]
            else:
                table = {"columns": ["Category", "Cost type", "Per month", "Averaged over"],
                         "rows": [[i["label"], costs.COST_TYPES[i["group"]]["label"], i["value"],
                                   f"{basis[i['label']]} months"] for i in items]}
                parts = ", ".join(f"{_eur(g['value'])} on {g['label'].lower()}" for g in groups)
                summary = f"You spend {_eur(total)} {when}"
                summary += f": {parts}." if len(groups) > 1 else f" on {scope.replace(' spending', '')}."
                questions = ["Where does my money go?" if all_cats
                             else f"Tell me about my {scope}.",
                             "Where could I save the most?"]
        else:
            if q["compare"] == "peers":
                peers = _peer_ids(customer_id)
                if month:
                    bench = _peer_median(peers, tuple(cats), months, "category", month)
                else:
                    # Same basis on both sides: 12 months for essentials that vary.
                    bench = {}
                    for n in sorted(set(basis.values())):
                        group_cats = tuple(c for c in cats if basis[c] == n)
                        bench.update(_peer_median(peers, group_cats, n, "category"))
                bench_label, cls, short = peer_label, "peer", "Typical similar customer"
                them = "the typical similar customer"
                add_peer_note()
                used = cats
                questions = [_peer_question(scope, all_cats), "Where could I save the most?"]
            else:
                used = [c for c in cats if national["categories"].get(c, {}).get("comparable")]
                skipped = [c for c in cats if c in national["categories"]
                           and not national["categories"][c]["comparable"]]
                bench = {c: national["categories"][c]["eur"] for c in used}
                monthly = {c: round(v * factor(c), 2) for c, v in monthly.items()}
                if home and any(factor(c) != 1 for c in used):
                    you_label = "You, per person in your household"
                bench_label, cls, short = fin_label, "s2", "Finnish average"
                them = "the Finnish average"
                add_finland_notes(used, skipped)
                questions = [_finland_question(used or cats, all_cats)]
            versus = "finland" if q["compare"] == "finland" else "peers"
            items = [
                {"label": c, "you": monthly[c], "peers": bench[c],
                 # What to ask about this row (never "why do I spend less").
                 "question": question_for(c, "more" if monthly[c] > bench[c] else "less", versus)}
                for c in used
            ]
            items.sort(key=lambda i: -abs(i["you"] - i["peers"]))
            visual = {"type": "compare", "title": f"{scope.capitalize()}: you and others",
                      "subtitle": (f"{period}" if month else "An average month"),
                      "you_label": you_label, "peer_label": bench_label, "peer_class": cls,
                      "items": items}
            table = {"columns": ["Category", "You / month", f"{short} / month", "Difference"],
                     "rows": [[i["label"], i["you"], i["peers"], round(i["you"] - i["peers"], 2)]
                              for i in items]}
            more = [i for i in items if i["you"] > i["peers"]]
            if items:
                big = items[0]
                d = big["you"] - big["peers"]
                summary = (
                    f"You spend more than {them} in {len(more)} of {len(items)} "
                    f"{'category' if len(items) == 1 else 'categories'}. The biggest difference "
                    f"is {big['label'].lower()}: {_eur(abs(d))} {'more' if d > 0 else 'less'} a month."
                )
            else:
                summary = "There is no comparable benchmark for this selection."

    elif q["group_by"] == "merchant":
        sel = tx[tx["category"].isin(cats) & tx["merchant_id"].notna()]
        totals = (-sel["tx_amount_eur"]).groupby(sel["merchant_id"], observed=True).agg(
            ["sum", "count"]).sort_values("sum", ascending=False)
        top = totals.head(10)
        total = float(totals["sum"].sum())
        visual = {"type": "bars", "title": f"{scope.capitalize()} by merchant",
                  "subtitle": f"Top {len(top)} of {len(totals)} merchants, {period}. All merchants",
                  "total": round(total, 2),
                  "items": [{"label": str(m), "value": round(float(r["sum"]), 2)}
                            for m, r in top.iterrows()]}
        table = {"columns": ["Merchant", "Total", "Purchases"],
                 "rows": [[str(m), round(float(r["sum"]), 2), int(r["count"])]
                          for m, r in top.iterrows()]}
        notes.append("Merchants only have codes in this data, not names. Housing and utility "
                     "payments have no merchant.")
        if len(top):
            m, r = next(top.iterrows())
            summary = (f"You bought from {len(totals)} merchants in {the_period}. The biggest, "
                       f"{m}, got {_eur(r['sum'])} over {int(r['count'])} "
                       f"purchase{'' if int(r['count']) == 1 else 's'}.")
        else:
            summary = f"No card purchases in {the_period} for this selection."
        questions = [f"Which merchants do I use most for {' and '.join(c.lower() for c in cats)}?"
                     if not all_cats else "Which merchants do I spend the most at?"]

    else:  # weekday
        sel = tx[tx["category"].isin(cats) & (tx["transaction_type"] == "purchase")]
        days = pd.date_range(start, end)
        n_days = days.dayofweek.value_counts()
        sums = (-sel["tx_amount_eur"]).groupby(sel["tx_date"].dt.dayofweek).sum()
        values = [round(float(sums.get(d, 0.0)) / max(int(n_days.get(d, 1)), 1), 2)
                  for d in range(7)]
        visual = {"type": "bars", "title": f"{scope.capitalize()} by weekday",
                  "subtitle": f"Card purchases on an average day, {period}. Average day",
                  "total": round(sum(values) / 7, 2), "show_share": False,
                  "items": [{"label": WEEKDAYS[d], "value": values[d]} for d in range(7)]}
        table = {"columns": ["Weekday", "Average per day"],
                 "rows": [[WEEKDAYS[d], values[d]] for d in range(7)]}
        best = max(range(7), key=lambda d: values[d])
        summary = (f"{WEEKDAYS[best]} is your biggest spending day: {_eur(values[best])} on "
                   f"an average {WEEKDAYS[best]} in {the_period}.")
        notes.append("Card purchases only. Housing and utility payments are left out, they "
                     "would hide the pattern.")
        questions = ["On which days do I spend the most?"]

    return {
        "query": q,
        "visual": visual,
        "table": table,
        "summary": summary,
        "notes": notes,
        "source": source,
        "questions": questions,
        "household": household.as_dict(home),
        # Comparisons are fairer with household details: invite, never require.
        "household_hint": home is None and q["compare"] != "none",
        "options": {
            "measures": [{"id": m, "label": LABELS[m].split(" (")[0]} for m in MEASURES],
            "group_by": GROUPS,
            "periods": PERIODS,
            "categories": SPENDING_CATEGORIES,
            "compare": COMPARES,
        },
    }


def export(customer_id: str) -> pd.DataFrame:
    """All of the customer's transactions, for 'download my data'."""
    tx = finance._tx(customer_id).sort_values("tx_timestamp")
    return tx.assign(tx_date=tx["tx_date"].dt.date)
