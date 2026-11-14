"""Compare each customer's spending to similar customers ("peers").

    from junction26.insights import get_insights, get_comparison

    get_insights("CUST04457")    # biggest differences, with ready-made text
    get_comparison("CUST04457")  # every category vs peers

How it works:
- Uses the last 12 months of data, averaged per month.
- Peers = same age band and same income band. If that group has fewer than
  MIN_PEERS people, peers = same income band only.
- Peer stats use the median, and a percentile ("you spend more than X% of
  similar users").
- Customers with few card purchases probably use another bank's card too, so
  their low spending isn't real. They are flagged low_activity, left out of
  peer stats, and get no "you spend less" insights.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache

import numpy as np
import pandas as pd

from .data import load_customers, load_transactions

WINDOW_MONTHS = 12
MIN_PEERS = 20
# ~6% of customers make fewer card purchases than this per month.
LOW_ACTIVITY_PURCHASES_PER_MONTH = 12
# Ignore differences smaller than this, they aren't worth mentioning.
MIN_INSIGHT_EUR = 10
MIN_INSIGHT_PCT = 10

SPENDING_CATEGORIES = [
    "Groceries",
    "Restaurants",
    "Transportation",
    "Entertainment",
    "Health",
    "Home & Tech",
    "Lifestyle",
    "Travel",
    "Housing",
    "Utilities",
]
INCOME_CATEGORIES = ["Salary", "Other Income"]

AGE_BINS = [0, 25, 35, 45, 55, 65, 200]
AGE_LABELS = ["under 25", "25-34", "35-44", "45-54", "55-64", "65+"]
INCOME_LABELS = ["low", "lower-middle", "upper-middle", "high"]


@dataclass(frozen=True)
class PeerData:
    profiles: pd.DataFrame  # one row per customer
    comparisons: pd.DataFrame  # one row per customer x category


def _monthly(tx: pd.DataFrame, categories: list[str]) -> pd.DataFrame:
    """Average EUR per month per customer and category, as positive numbers."""
    sel = tx[tx["category"].isin(categories)]
    totals = (
        sel.groupby(["customer_id", "category"], observed=True)["tx_amount_eur"]
        .sum()
        .unstack(fill_value=0.0)
    )
    return (totals.abs() / WINDOW_MONTHS).reindex(columns=categories, fill_value=0.0)


def _build_profiles() -> pd.DataFrame:
    tx = load_transactions()
    end = tx["tx_date"].max()
    tx = tx[tx["tx_date"] > end - pd.DateOffset(months=WINDOW_MONTHS)]

    spend = _monthly(tx, SPENDING_CATEGORIES)
    income = _monthly(tx, INCOME_CATEGORIES).sum(axis=1).rename("monthly_income")
    purchases = (
        tx[tx["transaction_type"] == "purchase"].groupby("customer_id", observed=True).size()
        / WINDOW_MONTHS
    ).rename("purchases_per_month")

    df = (
        load_customers()
        .set_index("customer_id")
        .join([income, purchases, spend])
        .fillna({"monthly_income": 0.0, "purchases_per_month": 0.0})
        .fillna({c: 0.0 for c in SPENDING_CATEGORIES})
    )
    df["low_activity"] = df["purchases_per_month"] < LOW_ACTIVITY_PURCHASES_PER_MONTH

    df["age_band"] = pd.cut(df["customer_age"], AGE_BINS, labels=AGE_LABELS, right=False)
    # Income quartiles, measured on active customers only.
    edges = df.loc[~df["low_activity"], "monthly_income"].quantile([0.25, 0.5, 0.75]).tolist()
    df["income_band"] = pd.cut(
        df["monthly_income"], [-np.inf, *edges, np.inf], labels=INCOME_LABELS
    )

    # Peer group: age x income, falling back to income only if too small.
    active = df[~df["low_activity"]]
    sizes = active.groupby(["age_band", "income_band"], observed=True).size()
    big_enough = {k for k, n in sizes.items() if n >= MIN_PEERS}
    use_age = [
        (a, i) in big_enough for a, i in zip(df["age_band"], df["income_band"], strict=True)
    ]
    df["peer_uses_age"] = use_age
    df["peer_group"] = np.where(
        use_age,
        "age " + df["age_band"].astype(str) + ", " + df["income_band"].astype(str) + " income",
        df["income_band"].astype(str) + " income",
    )
    df["peer_count"] = [len(_peers(df, row)) for _, row in df.iterrows()]
    return df


def _peers(profiles: pd.DataFrame, member: pd.Series) -> pd.DataFrame:
    """Active customers in the same peer group as `member`."""
    mask = ~profiles["low_activity"] & (profiles["income_band"] == member["income_band"])
    if member["peer_uses_age"]:
        mask &= profiles["age_band"] == member["age_band"]
    return profiles[mask]


def _build_comparisons(profiles: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for _, members in profiles.groupby("peer_group"):
        peers = _peers(profiles, members.iloc[0])
        for cat in SPENDING_CATEGORIES:
            peer_values = np.sort(peers[cat].to_numpy())
            you = members[cat].to_numpy()
            # Share of peers spending less than you (excluding yourself
            # doesn't matter at these group sizes).
            pct = np.searchsorted(peer_values, you, side="left") / len(peer_values) * 100
            median = float(np.median(peer_values))
            rows.append(
                pd.DataFrame(
                    {
                        "customer_id": members.index,
                        "category": cat,
                        "you_eur": you,
                        "peer_median_eur": median,
                        "percentile": pct,
                    }
                )
            )
    df = pd.concat(rows, ignore_index=True)
    df["diff_eur"] = df["you_eur"] - df["peer_median_eur"]
    df["diff_pct"] = np.where(
        df["peer_median_eur"] > 0, df["diff_eur"] / df["peer_median_eur"] * 100, np.nan
    )
    return df.round({"you_eur": 2, "peer_median_eur": 2, "diff_eur": 2, "diff_pct": 1,
                     "percentile": 0})


@lru_cache(maxsize=1)
def peer_data() -> PeerData:
    profiles = _build_profiles()
    return PeerData(profiles, _build_comparisons(profiles))


def get_profile(customer_id: str) -> dict:
    profiles = peer_data().profiles
    if customer_id not in profiles.index:
        raise KeyError(customer_id)
    p = profiles.loc[customer_id]
    return {
        "customer_id": customer_id,
        "age": int(p["customer_age"]),
        "monthly_income_eur": round(float(p["monthly_income"]), 2),
        "purchases_per_month": round(float(p["purchases_per_month"]), 1),
        "low_activity": bool(p["low_activity"]),
        "peer_group": p["peer_group"],
        "peer_count": int(p["peer_count"]),
        "window_months": WINDOW_MONTHS,
    }


def get_comparison(customer_id: str) -> pd.DataFrame:
    """Every spending category for this customer vs their peers."""
    comp = peer_data().comparisons
    rows = comp[comp["customer_id"] == customer_id]
    if rows.empty:
        raise KeyError(customer_id)
    return rows.drop(columns="customer_id").reset_index(drop=True)


def _eur(amount: float) -> str:
    """Finnish style: 1 234 €."""
    return f"{amount:,.0f}".replace(",", " ") + " €"


def _text(row: pd.Series) -> str:
    cat = row["category"].lower()
    amount = abs(row["diff_eur"])
    more = row["diff_eur"] > 0
    word = "more" if more else "less"
    text = (
        f"You spend {_eur(amount)} {word} per month on {cat} than similar customers "
        f"({_eur(row['you_eur'])} vs {_eur(row['peer_median_eur'])})"
    )
    if more:
        text += f". That adds up to {_eur(amount * 12)} a year"
    pct = min(row["percentile"] if more else 100 - row["percentile"], 99)
    text += f". You spend {word} than {pct:.0f}% of them."
    return text


def get_insights(customer_id: str, limit: int = 5) -> dict:
    """The biggest differences vs peers, largest first, with readable text."""
    profile = get_profile(customer_id)
    comp = get_comparison(customer_id)
    notable = comp[
        (comp["diff_eur"].abs() >= MIN_INSIGHT_EUR)
        & (comp["diff_pct"].abs() >= MIN_INSIGHT_PCT)
    ]
    if profile["low_activity"]:
        # Low spending here likely means they use another card.
        notable = notable[notable["diff_eur"] > 0]
    notable = notable.reindex(notable["diff_eur"].abs().sort_values(ascending=False).index)
    from . import household

    home = household.get(customer_id)
    items = []
    for _, row in notable.iterrows():
        direction = "more" if row["diff_eur"] > 0 else "less"
        items.append({
            **row.to_dict(),
            "direction": direction,
            "text": _text(row),
            # Why this difference may simply reflect their household.
            "expected_because": household.expectation(row["category"], direction, home),
        })
    # Differences the household explains are less newsworthy: show them last.
    items.sort(key=lambda i: i["expected_because"] is not None)
    return {**profile, "insights": items[:limit]}
