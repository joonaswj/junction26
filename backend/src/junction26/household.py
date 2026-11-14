"""Optional household details a customer can add for better insights.

A bank account shows one person's payments, not a household's life. Someone
whose partner buys the groceries looks like they barely eat. So the customer
can tell us, if they want:

    partner             do they live with a partner
    children            children living at home (0-6)
    partner_share_pct   how much of the shared costs the partner pays (0-90),
                        estimated with a slider

This is the customer's own, self-reported data: optional, editable, and
deletable at any time. It is stored in backend/data/household.json (not in
git). It changes three things:

1. The Finnish benchmark becomes "households like yours" (Statistics Finland
   publishes the survey by household type) instead of "people your age".
2. Shared costs are scaled to the whole household using the partner's share,
   then divided by household size, so both sides of a comparison are "per
   person". See per_person_factor().
3. Insights and the assistant take it into account ("your partner pays most
   shared costs, so low grocery spending here is expected").
"""

from __future__ import annotations

import json
import threading
from dataclasses import asdict, dataclass

from .data import data_dir

# Costs a household typically pays together. Everything else is personal.
SHARED_CATEGORIES = ["Groceries", "Housing", "Utilities", "Home & Tech"]
MAX_PARTNER_SHARE = 90  # above this the account says too little to scale from
MAX_CHILDREN = 6

_lock = threading.Lock()


@dataclass(frozen=True)
class Household:
    partner: bool = False
    children: int = 0
    partner_share_pct: int = 0  # of shared costs; only meaningful with a partner

    @property
    def my_share(self) -> float:
        """Share of the household's shared costs that goes through this account."""
        return 1 - self.partner_share_pct / 100 if self.partner else 1.0

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
            who += f". Your partner pays about {self.partner_share_pct} % of shared costs"
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
    return Household(**raw) if raw else None


def save(customer_id: str, partner: bool, children: int, partner_share_pct: int) -> Household:
    children = max(0, min(int(children), MAX_CHILDREN))
    share = max(0, min(int(partner_share_pct), MAX_PARTNER_SHARE)) if partner else 0
    household = Household(bool(partner), children, share)
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


def per_person_factor(category: str, household: Household | None) -> float:
    """Multiply the account's spending by this to get "per person in the household".

    Shared costs: scale up to the whole household (divide by the share paid
    from this account), then divide by household size. Personal costs are
    already one person's spending.
    """
    if household is None or category not in SHARED_CATEGORIES:
        return 1.0
    return 1 / household.my_share / household.consumption_units


def expectation(category: str, direction: str, household: Household | None) -> str | None:
    """Why a difference to similar customers may be expected, given the household.

    Similar customers are grouped by age and income only, so their households
    differ. This turns a possibly alarming insight into an explained one.
    """
    if household is None or category not in SHARED_CATEGORIES:
        return None
    name = category.lower()
    if direction == "less" and household.partner and household.partner_share_pct >= 40:
        return (
            f"Your partner pays about {household.partner_share_pct} % of your shared costs, "
            f"so this account shows only part of your household's {name}."
        )
    if direction == "more" and household.children:
        n = household.children
        return (
            f"With {n} {'child' if n == 1 else 'children'} at home, higher {name} spending "
            "than similar customers is to be expected."
        )
    if direction == "more" and household.partner and household.partner_share_pct <= 25:
        return (
            f"You pay most of your household's shared costs, so your {name} covers more "
            "than one person."
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
