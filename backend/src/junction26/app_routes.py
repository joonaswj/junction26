"""Routes the mobile app uses: demo login, dashboard data, chat."""

from __future__ import annotations

import json
from typing import Literal

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from . import chat as chatbot
from . import finance, guardrails, visuals

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
        "income_vs_spending": visuals.income_vs_spending(customer_id, 6),
        "spending": visuals.spending(customer_id, 3),
        "peers": visuals.peers(customer_id),
        "mortgage": visuals.mortgage(customer_id),
    }


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
