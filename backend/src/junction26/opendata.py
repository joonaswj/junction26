"""Open data benchmarks: how much people in Finland spend, by age group.

Source: Statistics Finland, Household Budget Survey, table 14q4 "Household
consumption expenditure by age of reference person" (StatFin, CC BY 4.0).
We use consumption per consumption unit per month, in euros. A consumption
unit is roughly "one adult's share of a household", so it is comparable to
one person's spending.

The figures are saved in opendata_statfi.json so the app works offline.
Refresh them from the API with (in the backend directory):

    uv run python -m junction26.opendata

Statistics Finland's categories (COICOP) don't match the bank's exactly.
CATEGORY_MAP says which COICOP groups we add up for each bank category, and
`caveat` says where the match is weak. The app shows these to the customer.
"""

from __future__ import annotations

import json
import urllib.request
from datetime import date
from functools import lru_cache
from pathlib import Path

TABLE_URL = "https://pxdata.stat.fi/PXWeb/api/v1/en/StatFin/ktutk/14q4.px"
SOURCE_PAGE = "https://pxdata.stat.fi/PxWeb/pxweb/en/StatFin/StatFin__ktutk/14q4.px/"
MEASURE = "kulukk_kt_hk_2_1"  # per consumption unit, current prices, EUR per month
YEAR = "2022"
DATA_FILE = Path(__file__).with_name("opendata_statfi.json")

# Bank category -> COICOP groups that are added together.
CATEGORY_MAP: dict[str, dict] = {
    "Groceries": {
        "coicop": ["01"],
        "label": "Food and non-alcoholic beverages",
    },
    "Restaurants": {
        "coicop": ["111"],
        "label": "Restaurants and cafés",
    },
    "Transportation": {
        "coicop": ["072", "073"],
        "label": "Running a vehicle and public transport",
        "caveat": "Buying a vehicle is not included.",
    },
    "Entertainment": {
        "coicop": ["092", "094", "095", "096", "097"],
        "label": "Recreation, culture, books and hobbies",
    },
    "Health": {
        "coicop": ["06"],
        "label": "Health",
    },
    "Home & Tech": {
        "coicop": ["05", "081", "082"],
        "label": "Furnishings, appliances and electronics",
    },
    "Lifestyle": {
        "coicop": ["03", "131", "132"],
        "label": "Clothing and personal care",
    },
    "Travel": {
        "coicop": ["098", "112"],
        "label": "Package holidays and accommodation",
        "caveat": "Flights bought separately are counted under transport in the statistics.",
    },
    "Housing": {
        "coicop": ["041", "043", "046"],
        "label": "Rent, maintenance charges and repairs",
        # Not compared: loan repayments and the value of living in a home you
        # own are not in this figure, so it says little about a bank
        # customer's housing payments.
        "comparable": False,
        "caveat": "Housing is not compared: the statistics don't count loan repayments, "
        "so the average says little about your housing payments.",
    },
    "Utilities": {
        "coicop": ["044", "045", "083"],
        "label": "Electricity, water and phone/internet",
    },
}

AGE_GROUPS = ["17-24", "25-34", "35-44", "45-54", "55-64", "65-74", "75-84", "85-"]


def age_group(age: int) -> str:
    """Statistics Finland age group for a customer's age."""
    for group in AGE_GROUPS:
        low, _, high = group.partition("-")
        if int(low) <= age <= (int(high) if high else 200):
            return group
    return AGE_GROUPS[0]  # under 17: use the youngest group


def fetch() -> dict:
    """Download the figures from Statistics Finland's open API."""
    codes = sorted({c for m in CATEGORY_MAP.values() for c in m["coicop"]} | {"0"})
    query = {
        "query": [
            {"code": "timeperiod_y", "selection": {"filter": "item", "values": [YEAR]}},
            {"code": "coicop_46_20231201", "selection": {"filter": "item", "values": codes}},
            {
                "code": "ikaryhma_10_20180101",
                "selection": {"filter": "item", "values": ["SSS", *AGE_GROUPS]},
            },
            {"code": "contentscode", "selection": {"filter": "item", "values": [MEASURE]}},
        ],
        "response": {"format": "json"},
    }
    request = urllib.request.Request(
        TABLE_URL,
        data=json.dumps(query).encode(),
        headers={"Content-Type": "application/json", "User-Agent": "junction26-hackathon-app"},
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        raw = json.load(response)

    # Rows look like {"key": [year, coicop, age], "values": ["123.4"]}.
    by_age: dict[str, dict[str, float]] = {}
    for row in raw["data"]:
        _, coicop, age = row["key"]
        value = row["values"][0]
        if value not in ("", ".", "..", "..."):  # missing-value markers
            by_age.setdefault(age, {})[coicop] = float(value)

    return {
        "source": "Statistics Finland, Household Budget Survey",
        "table": "14q4: Household consumption expenditure by age of reference person",
        "measure": "Consumption expenditure per consumption unit, EUR per month, current prices",
        "year": int(YEAR),
        "url": SOURCE_PAGE,
        "license": "CC BY 4.0",
        "retrieved": date.today().isoformat(),
        "coicop_eur_per_month_by_age": by_age,
    }


@lru_cache(maxsize=1)
def _data() -> dict:
    return json.loads(DATA_FILE.read_text(encoding="utf-8"))


def source() -> dict:
    """Attribution to show next to any figure from this data."""
    d = _data()
    return {k: d[k] for k in ("source", "table", "measure", "year", "url", "license")}


def national_spending(age: int) -> dict:
    """Average monthly spending per bank category for the customer's age group.

    Returns {"age_group", "total_eur", "categories": {name: {"eur", "label", "caveat"}}}.
    A category is left out if Statistics Finland has no figure for a part of it.
    """
    group = age_group(age)
    figures = _data()["coicop_eur_per_month_by_age"][group]
    categories = {}
    for name, mapping in CATEGORY_MAP.items():
        if all(c in figures for c in mapping["coicop"]):
            categories[name] = {
                "eur": round(sum(figures[c] for c in mapping["coicop"]), 2),
                "label": mapping["label"],
                "caveat": mapping.get("caveat"),
                "comparable": mapping.get("comparable", True),
            }
    return {
        "age_group": group.replace("-", "–") if not group.endswith("-") else "85+",
        "total_eur": figures.get("0"),
        "categories": categories,
    }


if __name__ == "__main__":
    data = fetch()
    DATA_FILE.write_text(json.dumps(data, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    _data.cache_clear()
    print(f"Saved {DATA_FILE.name}: {data['table']} ({data['year']})")
    for age in (22, 30, 50, 70):
        n = national_spending(age)
        print(age, n["age_group"], "total", n["total_eur"],
              {k: v["eur"] for k, v in n["categories"].items()})
