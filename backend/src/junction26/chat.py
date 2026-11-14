"""Chatbot that answers questions about one customer's finances.

The model (OpenAI, Chat Completions with tool calling) never sees raw data.
It calls the functions in TOOLS, which run finance.py for the logged-in
customer and return small JSON. customer_id is always filled in by the
server, never by the model, so it can only see that customer's data.

Setup: put OPENAI_API_KEY=sk-... in backend/.env (gitignored).
Optional: OPENAI_MODEL (default below).
"""

from __future__ import annotations

import json
import os
from collections.abc import Callable, Iterator
from functools import lru_cache
from pathlib import Path
from typing import Any

from . import finance

try:
    from dotenv import load_dotenv

    # backend/src/junction26/chat.py -> backend/.env
    load_dotenv(Path(__file__).resolve().parents[2] / ".env")
except ImportError:  # python-dotenv comes with fastapi[standard]
    pass

DEFAULT_MODEL = "gpt-5.4-mini"
MAX_TOOL_ROUNDS = 6

SYSTEM_PROMPT = """\
You are the S-Pankki money assistant in a mobile banking app. You are talking \
to a customer about their own finances.

Rules:
- Base every number on the tools. Never guess or invent figures. If you need \
data, call a tool first.
- "Today" is {today}: the data ends there. "Last month" means the last full \
month before that date.
- Amounts are in euros. Write them like €1,234 (round to whole euros unless \
cents matter).
- "Similar users" means customers in the same age and income group \
({peer_group}). Say who they are compared to when you compare.
- Be short and friendly: a few sentences or a short list. The customer reads \
this on a phone.
- You can explain, point out patterns and suggest practical ways to save. Do \
not recommend specific investment products or give legal or tax advice.
- Merchants only have codes like MRC-RES-0042 (RES = restaurants), no names.
{low_activity_note}
Customer: {customer_id}, age {age}.
"""

LOW_ACTIVITY_NOTE = (
    "- This customer makes few card purchases from this account, so they "
    "probably also pay with another bank's card. Low spending here may not be "
    "real. Mention that when it matters.\n"
)

# Tools: schema for the model + the function that runs it.
_CATEGORY = {
    "type": "string",
    "description": "Spending category, e.g. Groceries, Restaurants, Transportation, "
    "Entertainment, Health, Home & Tech, Lifestyle, Travel, Housing, Utilities.",
}


def _tool(name: str, description: str, properties: dict, required: list[str] | None = None):
    return {
        "type": "function",
        "function": {
            "name": name,
            "description": description,
            "parameters": {
                "type": "object",
                "properties": properties,
                "required": required or [],
                "additionalProperties": False,
            },
        },
    }


TOOLS = [
    _tool(
        "get_overview",
        "Headline numbers: current balance, average monthly income and spending, "
        "savings rate, top spending categories.",
        {},
    ),
    _tool(
        "get_spending",
        "Spending per category over the last N months. With a category: that "
        "category's month-by-month totals and top merchants.",
        {
            "months": {"type": "integer", "description": "1-24, default 3"},
            "category": _CATEGORY,
        },
    ),
    _tool(
        "get_monthly_trend",
        "Month-by-month income, spending, investing, net cash flow and end-of-month balance.",
        {"months": {"type": "integer", "description": "1-24, default 12"}},
    ),
    _tool(
        "compare_to_peers",
        "Compare monthly spending (last 12 months) to similar users. Without a "
        "category: the biggest differences. With one: that category in detail, "
        "including the percentile.",
        {"category": _CATEGORY},
    ),
    _tool(
        "find_transactions",
        "Search individual transactions.",
        {
            "category": _CATEGORY,
            "merchant_id": {"type": "string"},
            "start": {"type": "string", "description": "YYYY-MM-DD"},
            "end": {"type": "string", "description": "YYYY-MM-DD"},
            "min_amount_eur": {"type": "number"},
            "sort": {"type": "string", "enum": ["recent", "largest"]},
            "limit": {"type": "integer", "description": "1-50, default 20"},
        },
    ),
    _tool(
        "get_mortgage_status",
        "The customer's mortgage application, if any: decision, property price, "
        "loan, equity, loan-to-value, required income, recent events.",
        {},
    ),
]

_FUNCTIONS: dict[str, Callable[..., dict]] = {
    "get_overview": finance.get_overview,
    "get_spending": finance.get_spending,
    "get_monthly_trend": finance.get_monthly_trend,
    "compare_to_peers": finance.compare_to_peers,
    "find_transactions": finance.find_transactions,
    "get_mortgage_status": finance.get_mortgage_status,
}

# Short labels the app can show while a tool runs.
TOOL_LABELS = {
    "get_overview": "Looking at your accounts",
    "get_spending": "Adding up your spending",
    "get_monthly_trend": "Checking your monthly trend",
    "compare_to_peers": "Comparing with similar users",
    "find_transactions": "Searching your transactions",
    "get_mortgage_status": "Checking your mortgage application",
}


def run_tool(customer_id: str, name: str, arguments: str | dict) -> dict:
    """Run one tool for this customer. Errors are returned to the model as JSON."""
    try:
        args = json.loads(arguments or "{}") if isinstance(arguments, str) else arguments
        args = {k: v for k, v in args.items() if v is not None}
        args.pop("customer_id", None)  # never let the model pick the customer
        return _FUNCTIONS[name](customer_id, **args)
    except KeyError:
        return {"error": f"Unknown tool {name}"}
    except (ValueError, TypeError) as e:
        return {"error": str(e)}


def system_prompt(customer_id: str) -> str:
    profile = finance.get_profile(customer_id)  # raises KeyError if unknown
    return SYSTEM_PROMPT.format(
        today=finance.data_end_date().isoformat(),
        peer_group=profile["peer_group"],
        customer_id=customer_id,
        age=profile["age"],
        low_activity_note=LOW_ACTIVITY_NOTE if profile["low_activity"] else "",
    )


@lru_cache(maxsize=1)
def _client():
    from openai import OpenAI

    if not os.environ.get("OPENAI_API_KEY"):
        raise RuntimeError("OPENAI_API_KEY is not set. Add it to backend/.env.")
    return OpenAI()


def _model() -> str:
    return os.environ.get("OPENAI_MODEL", DEFAULT_MODEL)


def _start(customer_id: str, history: list[dict]) -> list[dict[str, Any]]:
    messages: list[dict[str, Any]] = [{"role": "system", "content": system_prompt(customer_id)}]
    for m in history:
        if m.get("role") in ("user", "assistant") and m.get("content"):
            messages.append({"role": m["role"], "content": str(m["content"])})
    return messages


def stream_chat(customer_id: str, history: list[dict], client=None) -> Iterator[dict]:
    """Run the chat, yielding events as they happen:

    {"type": "tool", "name": ..., "label": ...}   a tool started
    {"type": "text", "delta": ...}               part of the answer
    {"type": "done", "reply": ..., "tools_used": [...]}
    {"type": "error", "message": ...}
    """
    try:
        messages = _start(customer_id, history)
        client = client or _client()
    except KeyError:
        yield {"type": "error", "message": f"Customer {customer_id} not found"}
        return
    except RuntimeError as e:
        yield {"type": "error", "message": str(e)}
        return

    tools_used: list[str] = []
    reply = ""
    try:
        for _ in range(MAX_TOOL_ROUNDS + 1):
            stream = client.chat.completions.create(
                model=_model(), messages=messages, tools=TOOLS, stream=True
            )
            text, calls = "", {}
            for chunk in stream:
                if not chunk.choices:
                    continue
                delta = chunk.choices[0].delta
                if delta.content:
                    text += delta.content
                    yield {"type": "text", "delta": delta.content}
                for tc in delta.tool_calls or []:
                    call = calls.setdefault(tc.index, {"id": "", "name": "", "arguments": ""})
                    if tc.id:
                        call["id"] = tc.id
                    if tc.function and tc.function.name:
                        call["name"] += tc.function.name
                    if tc.function and tc.function.arguments:
                        call["arguments"] += tc.function.arguments
            reply += text
            if not calls:
                yield {"type": "done", "reply": reply, "tools_used": tools_used}
                return

            messages.append(
                {
                    "role": "assistant",
                    "content": text or None,
                    "tool_calls": [
                        {
                            "id": c["id"],
                            "type": "function",
                            "function": {"name": c["name"], "arguments": c["arguments"]},
                        }
                        for c in calls.values()
                    ],
                }
            )
            for c in calls.values():
                yield {"type": "tool", "name": c["name"], "label": TOOL_LABELS.get(c["name"], "")}
                tools_used.append(c["name"])
                result = run_tool(customer_id, c["name"], c["arguments"])
                messages.append(
                    {"role": "tool", "tool_call_id": c["id"], "content": json.dumps(result)}
                )
        yield {"type": "error", "message": "Too many tool calls, try a simpler question."}
    except Exception as e:  # API errors: bad key, rate limit, network
        yield {"type": "error", "message": f"Chat failed: {e}"}


def chat(customer_id: str, history: list[dict], client=None) -> dict:
    """Non-streaming version: returns {"reply", "tools_used"} or raises."""
    for event in stream_chat(customer_id, history, client):
        if event["type"] == "done":
            return {"reply": event["reply"], "tools_used": event["tools_used"]}
        if event["type"] == "error":
            raise RuntimeError(event["message"])
    raise RuntimeError("Chat ended without a reply")
