"""Chatbot that answers questions about one customer's finances.

The LLM (Featherless or OpenAI, see featherless.py) gets:
- a short snapshot of the customer's numbers in the system prompt, so it can
  answer common questions straight away, and
- tools (functions in finance.py) to look up more detail. customer_id is
  always filled in by the server, never by the model, so it can only see the
  logged-in customer's data.

If the model doesn't support tool calling, the request is retried without
tools and the model answers from the snapshot only.
"""

from __future__ import annotations

import json
from collections.abc import Callable, Iterator
from typing import Any

import openai

from . import finance
from .featherless import get_llm

MAX_TOOL_ROUNDS = 6
MAX_TOKENS = 1500

SYSTEM_PROMPT = """\
You are the S-Pankki money assistant in a mobile banking app. You are talking \
to a customer about their own finances.

Rules:
- Base every number on the data below or on tool results. Never guess or \
invent figures. If you need more detail and have tools, call them. If you \
don't have the data, say so.
- "Today" is {today}: the data ends there. "Last month" means the last full \
month before that date.
- Amounts are in euros. Write them like 1 234 € (round to whole euros unless \
cents matter).
- "Similar users" means customers in the same age and income group \
({peer_group}). Say who they are compared to when you compare.
- Be short and friendly: a few sentences or a short list. The customer reads \
this on a phone. Plain text, no tables, no headings.
- Answer in the language the customer writes in.
- You can explain, point out patterns and suggest practical ways to save. Do \
not recommend specific investment products or give legal or tax advice.
- Merchants only have codes like MRC-RES-0042 (RES = restaurants), no names.
{low_activity_note}
Customer: age {age}.

Snapshot of the customer's data (JSON):
{snapshot}
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


def _tool(name: str, description: str, properties: dict) -> dict:
    return {
        "type": "function",
        "function": {
            "name": name,
            "description": description,
            "parameters": {"type": "object", "properties": properties, "required": []},
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

# Set to False the first time the model rejects tools, so we stop sending them.
_tools_supported: bool | None = None


def run_tool(customer_id: str, name: str, arguments: str | dict) -> dict:
    """Run one tool for this customer. Errors are returned to the model as JSON."""
    if name not in _FUNCTIONS:
        return {"error": f"Unknown tool {name}"}
    try:
        args = json.loads(arguments or "{}") if isinstance(arguments, str) else arguments
        args = {k: v for k, v in (args or {}).items() if v is not None}
        args.pop("customer_id", None)  # never let the model pick the customer
        return _FUNCTIONS[name](customer_id, **args)
    except (ValueError, TypeError, KeyError) as e:
        return {"error": str(e)}


def _snapshot(customer_id: str) -> dict:
    """Compact summary of the customer's data for the system prompt."""
    overview = finance.get_overview(customer_id)
    insights = finance.get_insights(customer_id, limit=5)
    mortgage = finance.get_mortgage_status(customer_id)
    snap: dict[str, Any] = {
        "overview": {k: v for k, v in overview.items() if k not in ("customer_id", "age")},
        "spending_last_3_months_eur": finance.get_spending(customer_id, 3)["by_category_eur"],
        "vs_similar_users_monthly": [
            {k: i[k] for k in ("category", "you_eur", "peer_median_eur", "diff_eur",
                               "percentile")}
            for i in insights["insights"]
        ],
        "peer_group_size": insights["peer_count"],
    }
    if mortgage.get("has_mortgage_application"):
        snap["mortgage_application"] = {
            k: mortgage.get(k)
            for k in ("final_decision", "rejection_reason", "final_property_price_eur",
                      "final_requested_loan_eur", "final_equity_amount_eur",
                      "final_loan_to_value", "required_monthly_income_eur",
                      "application_started")
        }
    return snap


def system_prompt(customer_id: str) -> str:
    profile = finance.get_profile(customer_id)  # raises KeyError if unknown
    return SYSTEM_PROMPT.format(
        today=finance.data_end_date().isoformat(),
        peer_group=profile["peer_group"],
        age=profile["age"],
        low_activity_note=LOW_ACTIVITY_NOTE if profile["low_activity"] else "",
        snapshot=json.dumps(_snapshot(customer_id), ensure_ascii=False, default=str),
    )


def _start(customer_id: str, history: list[dict]) -> list[dict[str, Any]]:
    messages: list[dict[str, Any]] = [{"role": "system", "content": system_prompt(customer_id)}]
    for m in history:
        if m.get("role") in ("user", "assistant") and m.get("content"):
            messages.append({"role": m["role"], "content": str(m["content"])})
    return messages


class _ThinkFilter:
    """Drops <think>...</think> blocks that reasoning models put in the answer."""

    OPEN, CLOSE = "<think>", "</think>"

    def __init__(self) -> None:
        self.buffer = ""
        self.thinking = False

    def feed(self, text: str) -> str:
        self.buffer += text
        out = ""
        while self.buffer:
            if self.thinking:
                end = self.buffer.find(self.CLOSE)
                if end == -1:
                    # Keep the tail in case "</think>" is split across chunks.
                    self.buffer = self.buffer[-len(self.CLOSE):]
                    return out
                self.buffer = self.buffer[end + len(self.CLOSE):].lstrip()
                self.thinking = False
            else:
                start = self.buffer.find(self.OPEN)
                if start == -1:
                    # Hold back a possible partial "<think" at the end.
                    keep = max(
                        (i for i in range(1, len(self.OPEN)) if self.buffer.endswith(self.OPEN[:i])),
                        default=0,
                    )
                    cut = len(self.buffer) - keep
                    out += self.buffer[:cut]
                    self.buffer = self.buffer[cut:]
                    return out
                out += self.buffer[:start]
                self.buffer = self.buffer[start + len(self.OPEN):]
                self.thinking = True
        return out

    def flush(self) -> str:
        rest = "" if self.thinking else self.buffer
        self.buffer = ""
        return rest


def _create(llm, messages: list[dict[str, Any]], use_tools: bool):
    kwargs: dict[str, Any] = {
        "model": llm.model,
        "messages": messages,
        "max_tokens": MAX_TOKENS,
        "stream": True,
    }
    if use_tools:
        kwargs["tools"] = TOOLS
    return llm.client.chat.completions.create(**kwargs)


def stream_chat(customer_id: str, history: list[dict], llm=None) -> Iterator[dict]:
    """Run the chat, yielding events as they happen:

    {"type": "tool", "name": ..., "label": ...}   a tool started
    {"type": "text", "delta": ...}               part of the answer
    {"type": "done", "reply": ..., "tools_used": [...]}
    {"type": "error", "message": ...}
    """
    global _tools_supported
    try:
        messages = _start(customer_id, history)
        llm = llm or get_llm()
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
            use_tools = _tools_supported is not False
            try:
                stream = _create(llm, messages, use_tools)
            except openai.BadRequestError:
                if not use_tools:
                    raise
                # Model doesn't support tools: answer from the snapshot only.
                _tools_supported = False
                use_tools = False
                stream = _create(llm, messages, use_tools)

            think = _ThinkFilter()
            text, calls = "", {}
            for chunk in stream:
                if not chunk.choices:
                    continue
                delta = chunk.choices[0].delta
                if delta.content:
                    visible = think.feed(delta.content)
                    if visible:
                        text += visible
                        yield {"type": "text", "delta": visible}
                for tc in delta.tool_calls or []:
                    call = calls.setdefault(tc.index, {"id": "", "name": "", "arguments": ""})
                    if tc.id:
                        call["id"] = tc.id
                    if tc.function and tc.function.name:
                        call["name"] += tc.function.name
                    if tc.function and tc.function.arguments:
                        call["arguments"] += tc.function.arguments
            if rest := think.flush():
                text += rest
                yield {"type": "text", "delta": rest}
            reply += text

            if not calls:
                if use_tools:
                    _tools_supported = True
                reply = reply.strip()
                if not reply:
                    yield {"type": "error", "message": "The assistant gave an empty answer."}
                    return
                yield {"type": "done", "reply": reply, "tools_used": tools_used}
                return

            ids = {i: c["id"] or f"call_{i}" for i, c in calls.items()}
            messages.append(
                {
                    "role": "assistant",
                    "content": text or None,
                    "tool_calls": [
                        {
                            "id": ids[i],
                            "type": "function",
                            "function": {"name": c["name"], "arguments": c["arguments"] or "{}"},
                        }
                        for i, c in calls.items()
                    ],
                }
            )
            for i, c in calls.items():
                yield {"type": "tool", "name": c["name"], "label": TOOL_LABELS.get(c["name"], "")}
                tools_used.append(c["name"])
                result = run_tool(customer_id, c["name"], c["arguments"])
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": ids[i],
                        "content": json.dumps(result, ensure_ascii=False, default=str),
                    }
                )
        yield {"type": "error", "message": "Too many lookups, try a simpler question."}
    except openai.AuthenticationError:
        yield {"type": "error", "message": "The LLM API key is invalid. Check backend/.env."}
    except openai.APIError as e:
        yield {"type": "error", "message": f"The assistant is unavailable: {e}"}


def chat(customer_id: str, history: list[dict], llm=None) -> dict:
    """Non-streaming version: returns {"reply", "tools_used"} or raises."""
    for event in stream_chat(customer_id, history, llm):
        if event["type"] == "done":
            return {"reply": event["reply"], "tools_used": event["tools_used"]}
        if event["type"] == "error":
            raise RuntimeError(event["message"])
    raise RuntimeError("Chat ended without a reply")
