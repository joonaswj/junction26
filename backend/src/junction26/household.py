"""Optional household details a customer can add for better insights.

A bank account shows one person's payments, not a household's life. Someone
whose partner buys the groceries looks like they barely eat. So the customer
can tell us, if they want:

    partner                 do they live with a partner
    children                children living at home (0-6)
    partner_housing_pct     how much of the housing costs the partner pays
    partner_groceries_pct   how much of the groceries the partner pays

The two shares are separate sliders (0-90 %), because couples often split
them differently: rent half and half, but one of them does the shopping.
Only housing and groceries are treated as shared. Everything else counts as
the customer's own spending.

This is the customer's own, self-reported data: optional, editable, and
deletable at any time. It is stored in backend/data/household.json (not in
git). It changes three things:

1. The Finnish benchmark becomes "households like yours" (Statistics Finland
   publishes the survey by household type) instead of "people your age".
2. A shared cost is scaled to the whole household using the partner's share,
   then divided by household size, so both sides of a comparison are "per
   person". See per_person_factor().
3. Insights and the assistant take it into account ("your partner pays most
   of the groceries, so low grocery spending here is expected").
"""

from __future__ import annotations

import json
import threading
from dataclasses import asdict, dataclass

from .data import data_dir

# The costs a couple typically shares, each with its own slider.
SHARED_CATEGORIES = ["Housing", "Groceries"]
MAX_PARTNER_SHARE = 90  # above this the account says too little to scale from
MAX_CHILDREN = 6

_lock = threading.Lock()


@dataclass(frozen=True)
class Household:
    partner: bool = False
    children: int = 0
    partner_housing_pct: int = 0  # only meaningful with a partner
    partner_groceries_pct: int = 0

    def partner_share_pct(self, category: str) -> int:
        """How much of this category the partner pays, in percent."""
        if not self.partner:
            return 0
        return {"Housing": self.partner_housing_pct,
                "Groceries": self.partner_groceries_pct}.get(category, 0)

    def my_share(self, category: str) -> float:
        """Share of the household's cost in this category that goes through this account."""
        return 1 - self.partner_share_pct(category) / 100

    @property
    def consumption_units(self) -> float:
        """Household size the way Statistics Finland counts it (OECD modified
        scale): first adult 1.0, second adult 0.5, each child 0.3."""
        return 1.0 + (0.5 if self.partner else 0.0) + 0.3 * self.children

    def describe(self) -> str:
        who = "You and your partner" if self.partner else "You"
        if self.children:
            who += f" with {self.children} {'child' if self.children == 1 else 'children'}"
        elif not self.partner:
            who = "You live alone"
        if self.partner:
            who += (f". Your partner pays about {self.partner_housing_pct} % of housing and "
                    f"{self.partner_groceries_pct} % of groceries")
        return who + "."


def _file():
    return data_dir().parent / "household.json"


def _load_all() -> dict[str, dict]:
    try:
        return json.loads(_file().read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def get(customer_id: str) -> Household | None:
    """The customer's household details, or None if they haven't given any."""
    raw = _load_all().get(customer_id)
    if not raw:
        return None
    if "partner_share_pct" in raw:  # saved before the sliders were split in two
        old = raw.pop("partner_share_pct")
        raw.setdefault("partner_housing_pct", old)
        raw.setdefault("partner_groceries_pct", old)
    return Household(**raw)


def _clamp(pct: int) -> int:
    return max(0, min(int(pct), MAX_PARTNER_SHARE))


def save(customer_id: str, partner: bool, children: int, partner_housing_pct: int,
         partner_groceries_pct: int) -> Household:
    children = max(0, min(int(children), MAX_CHILDREN))
    household = Household(
        bool(partner),
        children,
        _clamp(partner_housing_pct) if partner else 0,
        _clamp(partner_groceries_pct) if partner else 0,
    )
    with _lock:
        everyone = _load_all()
        everyone[customer_id] = asdict(household)
        _file().parent.mkdir(parents=True, exist_ok=True)
        _file().write_text(json.dumps(everyone, indent=1), encoding="utf-8")
    return household


def delete(customer_id: str) -> None:
    with _lock:
        everyone = _load_all()
        if everyone.pop(customer_id, None) is not None:
            _file().write_text(json.dumps(everyone, indent=1), encoding="utf-8")


def household_total_factor(category: str, household: Household | None) -> float:
    """Multiply the account's spending by this to estimate the whole household's."""
    if household is None or category not in SHARED_CATEGORIES:
        return 1.0
    return 1 / household.my_share(category)


def per_person_factor(category: str, household: Household | None) -> float:
    """Multiply the account's spending by this to get "per person in the household".

    A shared cost is scaled up to the whole household (divided by the share
    paid from this account), then divided by household size. Other costs are
    already one person's spending.
    """
    if household is None or category not in SHARED_CATEGORIES:
        return 1.0
    return household_total_factor(category, household) / household.consumption_units


def expectation(category: str, direction: str, household: Household | None) -> str | None:
    """Why a difference to similar customers may be expected, given the household.

    Similar customers are grouped by age and income only, so their households
    differ. This turns a possibly alarming insight into an explained one.
    """
    if household is None or category not in SHARED_CATEGORIES:
        return None
    name = category.lower()
    share = household.partner_share_pct(category)
    if direction == "less" and household.partner and share >= 40:
        return (
            f"Your partner pays about {share} % of your {name}, so this account shows only "
            f"part of what your household spends on it."
        )
    if direction == "more" and household.children and category == "Groceries":
        n = household.children
        return (
            f"With {n} {'child' if n == 1 else 'children'} at home, higher grocery spending "
            "than similar customers is to be expected."
        )
    if direction == "more" and household.partner and share <= 25:
        return (
            f"You pay most of your household's {name}, so this covers more than one person."
        )
    return None


def as_dict(household: Household | None) -> dict | None:
    if household is None:
        return None
    return {
        **asdict(household),
        "description": household.describe(),
        "consumption_units": round(household.consumption_units, 2),
    }
