"""Chatbot that teaches a customer about their own finances.

The LLM (Featherless or OpenAI, see featherless.py) gets:
- a short snapshot of the customer's numbers in the system prompt, so it can
  answer common questions straight away,
- tools (functions in finance.py) to look up more detail, and
- a menu of chart tags like [[chart:spending]]. The charts themselves are
  built from the real data in visuals.py, the model never writes their numbers.

Guardrails (see guardrails.py): messages are screened before the LLM is
called, the model marks out-of-scope questions with [[off_topic]], and
customer_id is always filled in by the server, so the model can only see the
logged-in customer's data. Every reply comes with suggested next questions.

If the model doesn't support tool calling, the request is retried without
tools and the model answers from the snapshot only.
"""

from __future__ import annotations

import json
from collections.abc import Callable, Iterator
from typing import Any

import openai

from . import finance, guardrails, opendata, visuals
from .featherless import get_llm

MAX_TOOL_ROUNDS = 6
MAX_TOKENS = 1500
MAX_VISUALS = 2

SYSTEM_PROMPT = """\
You are the S-Pankki money assistant in a mobile banking app. You help one \
customer understand their own finances. You are a patient teacher: the goal \
is that they understand their money better after every answer.

{scope_rules}
Facts:
- All spending figures in the snapshot are per month. Only compare monthly \
figures with monthly figures, never a multi-month total with a monthly average.
- Base every number on the snapshot below or on tool results. Never guess or \
invent figures, and never do loan maths yourself: use mortgage_calculator. If \
you don't have the data, say so.
- Only state what the data shows. Never say what banks or lenders \
"typically" or "usually" accept, and never add rules of thumb, market facts \
or "most people" claims of your own. The only lending rules you may mention \
are the ones in tool results: the 90% loan cap, the required income and the \
stress test. The mortgage statistics are about all applicants in the data, \
not the customer's peer group.
- Don't guess at causes, habits or reasons you cannot see in the data. If \
the data doesn't show why, say what it does show.
- "Today" is {today}: the data ends there. "Last month" means the last full \
month before that date.
- "Similar customers" means customers in the same age and income group \
({peer_group}). Say who you compare with when you compare.
- The Finnish average comes from Statistics Finland's Household Budget \
Survey 2022 (spending per person, by age group). When you use it, name the \
source and say it is an approximate match. Housing is not compared with it.
- Merchants only have codes like MRC-RES-0042 (RES = restaurants), no names.
{low_activity_note}
How to answer:
- Short and friendly, for a phone screen: lead with the answer in one \
sentence, then at most 3 short bullet points (start each with "- ") or 2 \
more sentences. Stay under 90 words. Plain text. You may use **bold** for \
one or two key numbers. No tables, no headings, no emojis.
- Don't announce what you are about to do, and don't end by asking whether \
they want more: the app shows suggested next questions by itself.
- Check the numbers before you write. Never correct yourself in the middle \
of an answer: the customer only sees the final text.
- Write amounts like 1 234 € (whole euros unless cents matter).
- Teach: explain the "why" in plain words, and explain a finance term in a \
few words the first time you use it (for example: loan-to-value = the loan \
as a share of the home's value). End with one practical tip when it fits.
- {language_rule}
- Mortgage answers are estimates for learning, not a loan offer or a \
decision: say so in a few words, and suggest talking to an S-Pankki advisor \
for a real application.
- Don't recommend specific investment products.

Charts:
- When a picture helps understanding, end your answer with ONE tag on its \
own line. The app draws the chart from the customer's real data:
  [[chart:spending]]             spending by category, last 3 months
  [[chart:category:Groceries]]   one category month by month
  [[chart:income_vs_spending]]   income and spending per month
  [[chart:balance]]              balance over the last 12 months
  [[chart:peers]]                you vs similar customers, biggest differences
  [[chart:peers:Groceries]]      you vs similar customers in one category
  [[chart:mortgage]]             the customer's own mortgage application
  [[chart:finland]]              you vs the Finnish average for your age
  [[chart:finland:Groceries]]    the same for one category
- explore_data shows its own chart automatically, add no tag for it.
- mortgage_calculator shows its own chart automatically, add no tag for it.
- Never ask whether they want a chart: if it helps, just add the tag.
- Don't describe the chart or list every number in it. Say what it shows \
and the takeaway.

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
            },
        },
    }


TOOLS = [
    _tool(
        "explore_data",
        "Flexible look at the customer's data, shown to them as a chart. Use it "
        "for any question about spending by month, category, merchant or "
        "weekday, for income, savings or balance over time, and for comparing "
        "with similar customers or with the Finnish average (Statistics Finland).",
        {
            "measure": {"type": "string", "enum": ["spending", "income", "saved", "balance"]},
            "group_by": {
                "type": "string",
                "enum": ["month", "category", "merchant", "weekday"],
                "description": "Spending only. Other measures are always by month.",
            },
            "months": {"type": "integer", "description": "1-24, how far back. Default 3"},
            "month": {
                "type": "string",
                "description": "One specific month as YYYY-MM (e.g. 2026-01), to look inside "
                "it by category, merchant or weekday. Use this for 'what did I spend in "
                "January' questions instead of several lookups.",
            },
            "categories": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Spending categories to include. Leave out for all.",
            },
            "compare": {
                "type": "string",
                "enum": ["none", "peers", "finland"],
                "description": "Spending by month or category only.",
            },
        },
    ),
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
        "Compare monthly spending (last 12 months) to similar customers. Without a "
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
        "The customer's own mortgage application, if any: decision, the reason "
        "explained, property price, loan, down payment, loan-to-value, required "
        "income, recent events, and how other applicants did.",
        {},
    ),
    _tool(
        "mortgage_calculator",
        "What-if estimate for buying a home: loan, loan-to-value against the 90% "
        "cap, monthly payment, stress-tested payment, required income vs the "
        "customer's income, and whether their savings cover the down payment. "
        "Use for any 'could I afford', 'how much could I borrow' or 'what would "
        "the payment be' question.",
        {
            "property_price_eur": {"type": "number"},
            "down_payment_eur": {
                "type": "number",
                "description": "Own money. Leave out to assume their savings, at least 10%.",
            },
            "years": {"type": "integer", "description": "Loan time, default 25"},
            "interest_rate_pct": {"type": "number", "description": "Default 4.0 (example)"},
        },
        ["property_price_eur"],
    ),
]

def _explore_data(customer_id: str, **kwargs) -> dict:
    from .explore import explore

    result = explore(customer_id, **kwargs)
    return {k: result[k] for k in ("query", "summary", "table", "notes", "source", "visual",
                                   "options")}


_FUNCTIONS: dict[str, Callable[..., dict]] = {
    "explore_data": _explore_data,
    "get_overview": finance.get_overview,
    "get_spending": finance.get_spending,
    "get_monthly_trend": finance.get_monthly_trend,
    "compare_to_peers": finance.compare_to_peers,
    "find_transactions": finance.find_transactions,
    "get_mortgage_status": finance.get_mortgage_details,
    "mortgage_calculator": finance.mortgage_calculator,
}

# Short labels the app shows while a tool runs.
TOOL_LABELS = {
    "get_overview": "Looking at your account",
    "get_spending": "Adding up your spending",
    "get_monthly_trend": "Checking your monthly trend",
    "compare_to_peers": "Comparing with similar customers",
    "find_transactions": "Searching your transactions",
    "get_mortgage_status": "Checking your mortgage application",
    "mortgage_calculator": "Calculating a home loan estimate",
    "explore_data": "Exploring your data",
}

# What a tool call or chart is about, for choosing follow-up suggestions.
_TOPICS = {
    "get_spending": "spending",
    "find_transactions": "spending",
    "get_overview": "trend",
    "get_monthly_trend": "trend",
    "compare_to_peers": "peers",
    "get_mortgage_status": "mortgage",
    "mortgage_calculator": "mortgage",
    "explore_data": "spending",
    "bars": "spending",
    "columns": "trend",
    "line": "trend",
    "compare": "peers",
    "mortgage": "mortgage",
    "calc": "mortgage",
}

def _topic_of(visual: dict) -> str:
    if (visual.get("explore") or {}).get("compare") == "finland":
        return "finland"
    return _TOPICS[visual["type"]]


# Set to False the first time the model rejects tools, so we stop sending them.
_tools_supported: bool | None = None


def _parse_args(arguments: str | dict | None) -> dict:
    args = json.loads(arguments or "{}") if isinstance(arguments, str) else (arguments or {})
    args = {k: v for k, v in args.items() if v is not None}
    args.pop("customer_id", None)  # never let the model pick the customer
    return args


def run_tool(customer_id: str, name: str, arguments: str | dict) -> dict:
    """Run one tool for this customer. Errors are returned to the model as JSON."""
    if name not in _FUNCTIONS:
        return {"error": f"Unknown tool {name}"}
    try:
        return _FUNCTIONS[name](customer_id, **_parse_args(arguments))
    except (ValueError, TypeError, KeyError) as e:
        return {"error": str(e)}


def _snapshot(customer_id: str) -> dict:
    """Compact summary of the customer's data for the system prompt."""
    overview = finance.get_overview(customer_id)
    insights = finance.get_insights(customer_id, limit=5)
    mortgage = finance.get_mortgage_details(customer_id)
    national = opendata.national_spending(overview["age"])
    from .explore import explore

    finland = explore(customer_id, group_by="category", months=12, compare="finland")
    snap: dict[str, Any] = {
        "overview": {k: v for k, v in overview.items() if k not in ("customer_id", "age")},
        # Monthly averages everywhere, so figures can be compared with each other.
        "avg_monthly_spending_last_3_months_eur": {
            c: round(v / 3, 2)
            for c, v in finance.get_spending(customer_id, 3)["by_category_eur"].items()
        },
        "vs_similar_customers_monthly": [
            {k: i[k] for k in ("category", "you_eur", "peer_median_eur", "diff_eur",
                               "percentile")}
            for i in insights["insights"]
        ],
        "peer_group_size": insights["peer_count"],
        # Already compared, with the direction spelled out, so the model
        # doesn't have to work out which number is bigger.
        "vs_finnish_average": {
            "source": "Statistics Finland, Household Budget Survey 2022, per person, "
            f"age group {national['age_group']}. Approximate category match.",
            "period": "your monthly average over the last 12 months",
            "summary": finland["summary"],
            "by_category": [
                {
                    "category": cat,
                    "you_eur": you,
                    "finnish_average_eur": avg,
                    "you_spend": f"{abs(diff):.0f} EUR {'MORE' if diff > 0 else 'LESS'} than average",
                }
                for cat, you, avg, diff in finland["table"]["rows"]
            ],
            "housing_not_compared": "The statistics leave out loan repayments, so the "
            "national housing figure says little about a customer's housing payments. Do "
            "not compare housing or total spending with the Finnish average.",
        },
        "home_loan_basics": {
            "loan_cap_ltv": finance.LTV_LIMIT,
            "max_loan_for_their_income_eur": round(
                overview["avg_monthly_income_eur"] / finance.REQUIRED_INCOME_PER_LOAN_EUR
            ),
            "all_applicants_in_data": finance.mortgage_benchmarks(),
        },
    }
    if mortgage.get("has_mortgage_application"):
        snap["mortgage_application"] = {
            k: mortgage.get(k)
            for k in ("final_decision", "rejection_reason", "rejection_explained",
                      "final_property_price_eur", "final_requested_loan_eur",
                      "final_equity_amount_eur", "final_loan_to_value",
                      "required_monthly_income_eur", "application_started")
        }
        snap["mortgage_application"]["note"] = (
            "The bank assessed income when the customer applied. Their 12-month "
            "average income above may differ from what the bank used."
        )
    else:
        snap["mortgage_application"] = None
    return snap


def system_prompt(customer_id: str, user_text: str = "") -> str:
    profile = finance.get_profile(customer_id)  # raises KeyError if unknown
    return SYSTEM_PROMPT.format(
        scope_rules=guardrails.SCOPE_RULES,
        language_rule=guardrails.language_rule(user_text),
        today=finance.data_end_date().isoformat(),
        peer_group=profile["peer_group"],
        age=profile["age"],
        low_activity_note=LOW_ACTIVITY_NOTE if profile["low_activity"] else "",
        snapshot=json.dumps(_snapshot(customer_id), ensure_ascii=False, default=str),
    )


def _clean_history(history: list[dict]) -> list[dict[str, str]]:
    msgs = [
        {"role": m["role"], "content": str(m["content"])}
        for m in history
        if m.get("role") in ("user", "assistant") and m.get("content")
    ]
    return msgs[-guardrails.MAX_HISTORY_MESSAGES:]


class _StreamFilter:
    """Hides <think>...</think> and collects [[tags]] from streamed text.

    feed() returns the text that is safe to show so far. Tags can be split
    across chunks, so a possible start of a tag is held back until it's clear.
    """

    _PAIRS = (("<think>", "</think>"), ("[[", "]]"))
    _MAX_TAG = 80  # longer than this and "[[" was just text

    def __init__(self) -> None:
        self.buffer = ""
        self.inside: tuple[str, str] | None = None
        self.tags: list[str] = []

    def feed(self, text: str) -> str:
        self.buffer += text
        out = ""
        while self.buffer:
            if self.inside:
                opener, closer = self.inside
                end = self.buffer.find(closer)
                if end == -1:
                    if opener == "[[" and len(self.buffer) > self._MAX_TAG:
                        out += opener + self.buffer  # not a tag after all
                        self.buffer, self.inside = "", None
                    elif opener == "<think>":
                        self.buffer = self.buffer[-len(closer):]  # drop thoughts
                    return out
                if opener == "[[":
                    self.tags.append(self.buffer[:end].strip())
                self.buffer = self.buffer[end + len(closer):]
                self.inside = None
                continue
            starts = [(self.buffer.find(o), o, c) for o, c in self._PAIRS]
            starts = [s for s in starts if s[0] != -1]
            if not starts:
                # Hold back a possible partial opener at the end.
                keep = max(
                    (i for o, _ in self._PAIRS for i in range(1, len(o))
                     if self.buffer.endswith(o[:i])),
                    default=0,
                )
                cut = len(self.buffer) - keep
                out += self.buffer[:cut]
                self.buffer = self.buffer[cut:]
                return out
            pos, opener, closer = min(starts)
            out += self.buffer[:pos]
            self.buffer = self.buffer[pos + len(opener):]
            self.inside = (opener, closer)
        return out

    def flush(self) -> str:
        rest = "" if self.inside else self.buffer
        if self.inside and self.inside[0] == "[[":
            rest = "[[" + self.buffer
        self.buffer, self.inside = "", None
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


def _redirect(customer_id: str, reason: str, user_text: str, asked: list[str],
              sentence: str = "") -> dict:
    return {
        "type": "done",
        "reply": guardrails.redirect_message(reason, user_text, sentence),
        "visuals": [],
        "suggestions": guardrails.follow_ups(customer_id, [], asked, [], user_text),
        "guard": reason,
        "tools_used": [],
    }


def _pick_visuals(customer_id: str, tags: list[str], tool_visuals: list[dict]) -> list[dict]:
    """Charts for the reply: the calculator's own chart, then the model's tags,
    else charts that go with the tools it used. No duplicates, at most MAX_VISUALS."""
    picked = [v for v in tool_visuals if v["type"] == "calc"][-1:]
    if picked:
        return picked  # the estimate card is the whole story for a what-if
    # A chart the model deliberately explored beats a generic tag.
    explored = [v for v in tool_visuals if v.get("explore") and "notes" in v][-1:]
    if explored:
        return explored
    tagged = [visuals.from_tag(customer_id, t[len("chart:"):])
              for t in tags if t.lower().startswith("chart:")]
    tagged = [v for v in tagged if v]
    for v in tagged or [v for v in tool_visuals if v["type"] != "calc"][-MAX_VISUALS:]:
        if all(v["title"] != p["title"] for p in picked):
            picked.append(v)
    return picked[:MAX_VISUALS]


def stream_chat(customer_id: str, history: list[dict], llm=None) -> Iterator[dict]:
    """Run the chat, yielding events as they happen:

    {"type": "tool", "name": ..., "label": ...}   a lookup started
    {"type": "text", "delta": ...}               part of the answer
    {"type": "done", "reply", "visuals", "suggestions", "guard", "tools_used"}
    {"type": "error", "message": ...}

    `guard` is None for a normal answer, or why the message was redirected:
    "off_topic", "injection", "other_customer" or "too_long".
    """
    global _tools_supported
    history = _clean_history(history)
    if not history or history[-1]["role"] != "user":
        yield {"type": "error", "message": "The last message must be from the user."}
        return
    user_text = history[-1]["content"]
    asked = [m["content"] for m in history if m["role"] == "user"]

    try:
        prompt = system_prompt(customer_id, user_text)
    except KeyError:
        yield {"type": "error", "message": f"Customer {customer_id} not found"}
        return

    # Layer 1: instant checks, no LLM call.
    if reason := guardrails.screen(customer_id, user_text):
        yield _redirect(customer_id, reason, user_text, asked)
        return

    try:
        llm = llm or get_llm()
    except RuntimeError as e:
        yield {"type": "error", "message": str(e)}
        return

    messages: list[dict[str, Any]] = [{"role": "system", "content": prompt}, *history]
    tools_used: list[str] = []
    tool_visuals: list[dict] = []
    tags: list[str] = []
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

            flt = _StreamFilter()
            text, calls = "", {}
            for chunk in stream:
                if not chunk.choices:
                    continue
                delta = chunk.choices[0].delta
                if delta.content:
                    visible = flt.feed(delta.content)
                    # Hold the text back once the model has flagged off-topic:
                    # the redirect message is sent whole in the done event.
                    if visible and "off_topic" not in flt.tags:
                        text += visible
                        yield {"type": "text", "delta": visible}
                    elif visible:
                        text += visible
                for tc in delta.tool_calls or []:
                    call = calls.setdefault(tc.index, {"id": "", "name": "", "arguments": ""})
                    if tc.id:
                        call["id"] = tc.id
                    if tc.function and tc.function.name:
                        call["name"] += tc.function.name
                    if tc.function and tc.function.arguments:
                        call["arguments"] += tc.function.arguments
            if rest := flt.flush():
                text += rest
                if "off_topic" not in flt.tags:
                    yield {"type": "text", "delta": rest}
            tags += flt.tags
            # Text written before a tool call ("Let me check...") is not part
            # of the answer: the reply is the last round only.
            reply = text

            # Layer 2: the model says the question is out of scope.
            if "off_topic" in tags:
                yield _redirect(customer_id, "off_topic", user_text, asked, reply)
                return

            if not calls:
                if use_tools:
                    _tools_supported = True
                reply = reply.strip()
                if not reply:
                    yield {"type": "error", "message": "The assistant gave an empty answer."}
                    return
                shown = _pick_visuals(customer_id, tags, tool_visuals)
                topics = [_topic_of(v) for v in shown] + [
                    _TOPICS[t] for t in tools_used if t in _TOPICS
                ]
                yield {
                    "type": "done",
                    "reply": reply,
                    "visuals": shown,
                    "suggestions": guardrails.follow_ups(
                        customer_id, topics, asked, tools_used, user_text
                    ),
                    "guard": None,
                    "tools_used": tools_used,
                }
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
                try:
                    visual = visuals.from_tool(
                        customer_id, c["name"], _parse_args(c["arguments"]), result
                    )
                except ValueError:
                    visual = None
                if visual:
                    tool_visuals.append(visual)
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": ids[i],
                        # The chart goes to the app, not back to the model.
                        "content": json.dumps(
                            {k: v for k, v in result.items() if k not in ("visual", "options")},
                            ensure_ascii=False, default=str,
                        ),
                    }
                )
        yield {"type": "error", "message": "Too many lookups, try a simpler question."}
    except openai.AuthenticationError:
        yield {"type": "error", "message": "The LLM API key is invalid. Check backend/.env."}
    except openai.APIError as e:
        yield {"type": "error", "message": f"The assistant is unavailable: {e}"}


def chat(customer_id: str, history: list[dict], llm=None) -> dict:
    """Non-streaming version: returns the `done` event without its type, or raises."""
    for event in stream_chat(customer_id, history, llm):
        if event["type"] == "done":
            return {k: v for k, v in event.items() if k != "type"}
        if event["type"] == "error":
            raise RuntimeError(event["message"])
    raise RuntimeError("Chat ended without a reply")
