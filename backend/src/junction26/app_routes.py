"""Routes the mobile app uses: demo login, dashboard data, chat."""

from __future__ import annotations

import json
from typing import Literal

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import Response, StreamingResponse
from pydantic import BaseModel, Field

from . import chat as chatbot
from . import explore as explorer
from . import costs, finance, guardrails, household, opendata, visuals
from .data import load_transactions
from .insights import SPENDING_CATEGORIES

router = APIRouter()


def _call(fn, customer_id: str, *args, **kwargs):
    try:
        return fn(customer_id, *args, **kwargs)
    except (finance.CustomerNotFound, KeyError):
        raise HTTPException(404, f"Customer {customer_id} not found") from None
    except ValueError as e:
        raise HTTPException(400, str(e)) from None


@router.get("/demo-customers", tags=["app"])
def demo_customers(limit: int = Query(10, ge=1, le=50)):
    """Customers with full histories to "log in" as. Half have a mortgage application."""
    return finance.demo_customers(limit)


@router.get("/customers/{customer_id}/overview", tags=["app"])
def overview(customer_id: str):
    """Dashboard headline numbers."""
    return _call(finance.get_overview, customer_id)


@router.get("/customers/{customer_id}/spending", tags=["app"])
def spending(
    customer_id: str,
    months: int = Query(3, ge=1, le=24),
    category: str | None = None,
):
    """Spending per category over the last N months, or one category in detail."""
    return _call(finance.get_spending, customer_id, months, category)


@router.get("/customers/{customer_id}/trend", tags=["app"])
def trend(customer_id: str, months: int = Query(12, ge=1, le=24)):
    """Month-by-month income, spending, net and balance (for a chart)."""
    return _call(finance.get_monthly_trend, customer_id, months)


@router.get("/customers/{customer_id}/mortgage", tags=["app"])
def mortgage(customer_id: str):
    """The customer's mortgage application and recent events, if any."""
    return _call(finance.get_mortgage_status, customer_id)


@router.get("/customers/{customer_id}/visuals", tags=["app"])
def dashboard_visuals(customer_id: str):
    """Chart specs for the overview screen (same format as charts in chat replies)."""
    _call(finance.get_profile, customer_id)
    return {
        # 12 months, so it adds up to the overview's headline figures.
        "budget": visuals.budget(customer_id, 12),
        "income_vs_spending": visuals.income_vs_spending(customer_id, 6),
        "spending": visuals.spending(customer_id, 3),
        "peers": visuals.peers(customer_id),
        "mortgage": visuals.mortgage(customer_id),
    }


def _split(categories: str | None) -> list[str] | None:
    return [c.strip() for c in categories.split(",") if c.strip()] if categories else None


@router.get("/customers/{customer_id}/explore", tags=["explore"])
def explore_data(
    customer_id: str,
    measure: str = "spending",
    group_by: str = "category",
    months: int = Query(3, ge=1, le=24),
    categories: str | None = Query(None, description="Comma-separated, e.g. Groceries,Travel"),
    compare: str = "none",
    month: str | None = Query(None, description="One month, YYYY-MM, to look inside it"),
):
    """Explore your own data freely: pick what to look at, how to slice it and
    who to compare with. Returns a chart spec, the same numbers as a table, a
    one-sentence takeaway, notes on the benchmarks and questions for the assistant."""
    return _call(explorer.explore, customer_id, measure, group_by, months,
                 _split(categories), compare, month)


@router.get("/customers/{customer_id}/explore/transactions", tags=["explore"])
def explore_transactions(
    customer_id: str,
    months: int = Query(3, ge=1, le=24),
    categories: str | None = None,
    month: str | None = None,
    limit: int = Query(20, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    """The raw transactions behind an explore view, newest first."""
    tx = _call(finance._tx, customer_id)
    if month := explorer._valid_month(month):
        tx = tx[tx["tx_date"].dt.strftime("%Y-%m") == month]
    else:
        tx = finance._last_months(tx, months)
    cats = _split(categories)
    if cats:
        tx = tx[tx["category"].isin([_call(lambda _c, c=c: finance._match_category(c), customer_id)
                                     for c in cats])]
    tx = tx.sort_values("tx_timestamp", ascending=False)
    page = tx.iloc[offset : offset + limit]
    cols = ["tx_date", "category", "tx_amount_eur", "merchant_id", "balance_after_eur"]
    rows = page[cols].assign(tx_date=page["tx_date"].dt.date.astype(str))
    return {
        "total": len(tx),
        "items": rows.astype(object).where(rows.notna(), None).to_dict(orient="records"),
    }


@router.get("/customers/{customer_id}/export", tags=["explore"])
def export_my_data(customer_id: str, format: Literal["csv", "json"] = "csv"):
    """Download all of your transactions (data portability)."""
    df = _call(explorer.export, customer_id)
    name = f"s-pankki-my-data-{customer_id}"
    if format == "json":
        body, media = df.to_json(orient="records", date_format="iso"), "application/json"
    else:
        body, media = df.to_csv(index=False), "text/csv; charset=utf-8"
    return Response(
        body,
        media_type=media,
        headers={"Content-Disposition": f'attachment; filename="{name}.{format}"'},
    )


@router.get("/customers/{customer_id}/my-data", tags=["explore"])
def my_data(customer_id: str):
    """What data the app holds about you and how it is used (transparency)."""
    profile = _call(finance.get_profile, customer_id)
    tx = finance._tx(customer_id)
    return {
        "transactions": len(tx),
        "first_date": tx["tx_date"].min().date().isoformat(),
        "last_date": tx["tx_date"].max().date().isoformat(),
        "categories": SPENDING_CATEGORIES,
        "peer_group": profile["peer_group"],
        "peer_count": profile["peer_count"],
        "customers_in_dataset": int(load_transactions()["customer_id"].nunique()),
        "open_data": opendata.source(),
    }


class HouseholdIn(BaseModel):
    partner: bool = False
    children: int = Field(0, ge=0, le=household.MAX_CHILDREN)
    partner_housing_pct: int = Field(
        0, ge=0, le=household.MAX_PARTNER_SHARE,
        description="How much of the housing costs the partner pays, estimated",
    )
    partner_groceries_pct: int = Field(
        0, ge=0, le=household.MAX_PARTNER_SHARE,
        description="How much of the groceries the partner pays, estimated",
    )


def _household_response(customer_id: str) -> dict:
    usual = costs.usual(customer_id)
    return {
        "household": household.as_dict(household.get(customer_id)),
        "shared_categories": household.SHARED_CATEGORIES,
        "max_partner_share_pct": household.MAX_PARTNER_SHARE,
        # What this account pays in a usual month, so the form can show what
        # a slider position means in euros for the whole household.
        "my_monthly_eur": {c: usual[c] for c in household.SHARED_CATEGORIES},
    }


@router.get("/customers/{customer_id}/household", tags=["household"])
def get_household(customer_id: str):
    """Optional household details the customer has given (null if none)."""
    _call(finance.get_profile, customer_id)
    return _household_response(customer_id)


@router.put("/customers/{customer_id}/household", tags=["household"])
def put_household(customer_id: str, body: HouseholdIn):
    """Save household details. Optional, used for fairer comparisons."""
    _call(finance.get_profile, customer_id)
    household.save(customer_id, body.partner, body.children, body.partner_housing_pct,
                   body.partner_groceries_pct)
    return _household_response(customer_id)


@router.delete("/customers/{customer_id}/household", tags=["household"])
def delete_household(customer_id: str):
    """Remove the household details again."""
    _call(finance.get_profile, customer_id)
    household.delete(customer_id)
    return _household_response(customer_id)


@router.get("/customers/{customer_id}/chat/starters", tags=["chat"])
def chat_starters(customer_id: str, lang: Literal["en", "fi"] = "en"):
    """Personalised opening questions for the chat screen."""
    _call(finance.get_profile, customer_id)
    return {
        "suggestions": guardrails.starters(customer_id, lang),
        "max_message_chars": guardrails.MAX_MESSAGE_CHARS,
    }


class Message(BaseModel):
    role: Literal["user", "assistant"]
    content: str


class ChatRequest(BaseModel):
    customer_id: str = Field(examples=["CUST02868"])
    messages: list[Message] = Field(
        min_length=1,
        description="The whole conversation so far, oldest first. The app keeps it.",
        examples=[[{"role": "user", "content": "Where does my money go?"}]],
    )


def _json_default(value):
    """numpy numbers -> plain Python for json.dumps."""
    return value.item() if hasattr(value, "item") else str(value)


def _history(req: ChatRequest) -> list[dict]:
    _call(finance.get_profile, req.customer_id)  # 404 if unknown
    return [m.model_dump() for m in req.messages]


@router.post("/chat", tags=["chat"])
def chat(req: ChatRequest):
    """Ask the assistant. Returns when the answer is complete:

    - `reply`: the text
    - `visuals`: chart specs to draw under it (built from the customer's data)
    - `suggestions`: next questions to offer as buttons
    - `guard`: null, or why the message was redirected instead of answered
      (`off_topic`, `injection`, `other_customer`, `too_long`)
    """
    history = _history(req)
    try:
        return chatbot.chat(req.customer_id, history)
    except RuntimeError as e:
        raise HTTPException(503, str(e)) from None


@router.post("/chat/stream", tags=["chat"])
def chat_stream(req: ChatRequest):
    """Same as /chat, streamed as server-sent events (one JSON object per `data:` line).

    Event types: `tool` (a lookup started, with a label to show), `text`
    (part of the answer), `done` (same fields as /chat), `error`.
    """
    history = _history(req)

    def events():
        for event in chatbot.stream_chat(req.customer_id, history):
            yield f"data: {json.dumps(event, ensure_ascii=False, default=_json_default)}\n\n"

    return StreamingResponse(events(), media_type="text/event-stream")
