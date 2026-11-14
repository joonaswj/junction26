"""Suggested questions, tailored to the customer's profile.

Every suggestion is a question the assistant can answer from the data. Each
one is picked because of something in this customer's own situation (their
savings rate, biggest difference to similar customers, mortgage status...),
and carries a short `why` so the customer can see the reason: no hidden
profiling.

    starters(customer_id, lang)        opening questions with reasons
    follow_ups(customer_id, ...)       what to ask next, by topic
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from . import costs, finance, household, opendata

_FINNISH = re.compile(
    r"[äöÄÖ]|\b(mitä|miten|paljonko|kuinka|minun|rahaa|olen|onko|voinko|kerro|asuntolaina"
    r"|miksi|mihin|mikä)\b",
    re.IGNORECASE,
)

_FI_CATEGORY = {
    # (illative "spend on X", partitive/elative for "X spending")
    "Groceries": ("ruokaostoksiin", "ruokaostokseni"),
    "Restaurants": ("ravintoloihin", "ravintolamenoni"),
    "Transportation": ("liikkumiseen", "liikkumismenoni"),
    "Entertainment": ("viihteeseen", "viihdemenoni"),
    "Health": ("terveyteen", "terveysmenoni"),
    "Home & Tech": ("kotiin ja tekniikkaan", "koti- ja tekniikkamenoni"),
    "Lifestyle": ("vaatteisiin ja hyvinvointiin", "vaate- ja hyvinvointimenoni"),
    "Travel": ("matkailuun", "matkailumenoni"),
    "Housing": ("asumiseen", "asumismenoni"),
    "Utilities": ("sähköön ja veteen", "sähkö- ja vesimenoni"),
}
_MONTHS_EN = ["January", "February", "March", "April", "May", "June", "July", "August",
              "September", "October", "November", "December"]
_MONTHS_FI = ["tammikuussa", "helmikuussa", "maaliskuussa", "huhtikuussa", "toukokuussa",
              "kesäkuussa", "heinäkuussa", "elokuussa", "syyskuussa", "lokakuussa",
              "marraskuussa", "joulukuussa"]


# "restaurant spending", not "restaurants spending".
_ADJECTIVE = {"Restaurants": "restaurant", "Groceries": "grocery", "Utilities": "utility"}


def adjective(category: str) -> str:
    """The category as it reads before a noun: 'grocery spending', 'utility costs'."""
    return _ADJECTIVE.get(category, category.lower())


# Costs you can't change much from month to month. Asking how to "spend less"
# on these is unhelpful (or, for health, insensitive).
FIXED_COSTS = {"Housing", "Utilities", "Health"}


def question_for(category: str, direction: str, versus: str = "peers", lang: str = "en") -> str:
    """A sensible question about one category where the customer differs from others.

    More on something they control -> how to cut it. More on a fixed cost ->
    how it has developed. Less -> just how they compare (no "why": nobody asks
    why they spend less, and the data couldn't say).
    """
    cat = category.lower()
    if direction == "more" and category not in FIXED_COSTS:
        if lang == "fi":
            return f"Miten voisin käyttää vähemmän rahaa {_FI_CATEGORY[category][0]}?"
        return f"How could I spend less on {cat}?"
    if direction == "more":
        if lang == "fi":
            return f"Miten {_FI_CATEGORY[category][1]} ovat muuttuneet vuoden aikana?"
        return f"How have my {adjective(category)} costs changed over the year?"
    if versus == "finland":
        if lang == "fi":
            return f"Miten {_FI_CATEGORY[category][1]} vertautuvat suomalaisten keskiarvoon?"
        return f"How does my {adjective(category)} spending compare with the Finnish average?"
    if lang == "fi":
        return f"Miten {_FI_CATEGORY[category][1]} vertautuvat samankaltaisiin asiakkaisiin?"
    return f"How does my {adjective(category)} spending compare with similar customers?"


def lang_of(text: str) -> str:
    return "fi" if _FINNISH.search(text or "") else "en"


def _eur(amount: float) -> str:
    return f"{amount:,.0f}".replace(",", " ") + " €"


@dataclass(frozen=True)
class Suggestion:
    id: str
    topic: str  # spending | peers | trend | mortgage | finland
    score: float  # higher = more relevant to this customer
    en: str
    fi: str
    why_en: str = ""
    why_fi: str = ""

    def text(self, lang: str) -> str:
        return self.fi if lang == "fi" else self.en

    def as_dict(self, lang: str) -> dict:
        return {
            "text": self.text(lang),
            "why": self.why_fi if lang == "fi" else self.why_en,
            "topic": self.topic,
        }


def candidates(customer_id: str) -> list[Suggestion]:
    """Every question that makes sense for this customer, scored by relevance."""
    overview = finance.get_overview(customer_id)
    insights = finance.get_insights(customer_id, limit=10)["insights"]
    mortgage = finance.get_mortgage_status(customer_id)
    trend = finance.get_monthly_trend(customer_id, 12)["months"]
    income = overview["avg_monthly_income_eur"] or 1.0
    rate = overview["savings_rate_pct"]
    kept = income - overview["avg_monthly_spending_eur"]
    out: list[Suggestion] = []
    add = out.append

    add(Suggestion("overview", "spending", 50, "Where does my money go?",
                   "Mihin rahani menevät?", "A good place to start", "Hyvä paikka aloittaa"))
    add(Suggestion("purchases", "spending", 35, "What were my biggest purchases last month?",
                   "Mitkä olivat suurimmat ostokseni viime kuussa?"))

    # --- Compared with similar customers
    # Nobody asks why they spend LESS than others, and the data can't say why
    # anyway. So: ask how to cut what you overspend on and can control, ask
    # how a fixed cost has developed, and only mention "less" as good news.
    # Differences their household already explains are left out.
    insights = [i for i in insights if not i.get("expected_because")]
    more = [i for i in insights if i["direction"] == "more"]
    less = [i for i in insights if i["direction"] == "less"]
    flexible = [i for i in more if i["category"] not in FIXED_COSTS]
    fixed = [i for i in more if i["category"] in FIXED_COSTS]
    for group, base in ((flexible, 80), (fixed, 62)):
        if not group:
            continue
        top = group[0]
        cat = top["category"]
        # A small difference isn't worth leading with.
        big = top["diff_eur"] >= 50 and (top["diff_pct"] or 0) >= 20
        add(Suggestion(
            "peer_more" if group is flexible else "peer_fixed", "peers", base if big else base - 22,
            question_for(cat, "more"), question_for(cat, "more", lang="fi"),
            f"You spend {_eur(top['diff_eur'])} more a month than similar customers",
            f"Käytät {_eur(top['diff_eur'])} enemmän kuussa kuin samankaltaiset asiakkaat",
        ))
    if flexible:
        add(Suggestion("save_most", "peers", 65, "Where could I save the most?",
                       "Mistä voisin säästää eniten?",
                       f"You are above similar customers in {len(flexible)} "
                       f"{'category' if len(flexible) == 1 else 'categories'} you can influence",
                       f"Olet samankaltaisten asiakkaiden yläpuolella {len(flexible)} luokassa, "
                       "joihin voit vaikuttaa"))
    if less and not flexible:
        add(Suggestion("peer_less", "peers", 52, "Where do I spend less than others?",
                       "Missä kulutan vähemmän kuin muut?",
                       f"You are below similar customers in {len(less)} "
                       f"{'category' if len(less) == 1 else 'categories'}",
                       f"Olet samankaltaisten asiakkaiden alapuolella {len(less)} luokassa"))
    add(Suggestion("peers", "peers", 45, "How do I compare with similar customers?",
                   "Miten vertaudun samankaltaisiin asiakkaisiin?"))

    # --- Saving and balance
    if rate is not None and rate < 0:
        add(Suggestion("overspend", "trend", 95, "How can I stop spending more than I earn?",
                       "Miten saisin menoni pienemmiksi kuin tuloni?",
                       f"You spend {_eur(-kept)} more than you earn in an average month",
                       f"Kulutat keskimäärin {_eur(-kept)} enemmän kuin tienaat kuussa"))
    elif rate is not None and rate < 10:
        add(Suggestion("save_more", "trend", 85, "How could I save a little more each month?",
                       "Miten voisin säästää hieman enemmän kuukaudessa?",
                       f"You keep {rate:.0f} % of your income",
                       f"Tuloistasi jää säästöön {rate:.0f} %"))
    else:
        add(Suggestion("savings", "trend", 48, "How much do I save each month?",
                       "Paljonko säästän kuukaudessa?",
                       f"You keep about {_eur(kept)} a month" if rate is not None else "",
                       f"Sinulle jää noin {_eur(kept)} kuussa" if rate is not None else ""))

    housing = next((c["avg_monthly_eur"] for c in overview["top_categories_last_12_months"]
                    if c["category"] == "Housing"), 0.0)
    if housing / income > 0.35:
        share = round(housing / income * 100)
        add(Suggestion("housing_share", "spending", 75, "Is my housing cost high for my income?",
                       "Ovatko asumismenoni suuret tuloihini nähden?",
                       f"Housing takes {share} % of your income",
                       f"Asuminen vie {share} % tuloistasi"))

    if len(trend) >= 2:
        change = trend[-1]["end_balance"] - trend[0]["end_balance"]
        if change < -0.05 * max(abs(trend[0]["end_balance"]), 1):
            add(Suggestion("balance_down", "trend", 90, "What made my balance go down this year?",
                           "Mikä laski saldoani tänä vuonna?",
                           f"Your balance is down {_eur(-change)} in 12 months",
                           f"Saldosi on laskenut {_eur(-change)} 12 kuukaudessa"))
        else:
            add(Suggestion("balance", "trend", 40, "Is my balance growing?", "Kasvaako saldoni?",
                           f"Your balance is up {_eur(change)} in 12 months",
                           f"Saldosi on kasvanut {_eur(change)} 12 kuukaudessa"))
        spends = [m["spending"] for m in trend]
        avg = sum(spends) / len(spends)
        peak = max(trend, key=lambda m: m["spending"])
        if avg and peak["spending"] > 1.35 * avg:
            month = int(peak["month"][5:7]) - 1
            extra = peak["spending"] - avg
            add(Suggestion("spike", "trend", 60,
                           f"What did I spend so much on in {_MONTHS_EN[month]}?",
                           f"Mihin käytin niin paljon rahaa {_MONTHS_FI[month]}?",
                           f"You spent {_eur(extra)} more than usual that month",
                           f"Käytit silloin {_eur(extra)} tavallista enemmän"))
    add(Suggestion("income_spending", "trend", 38, "How has my income and spending changed?",
                   "Miten tuloni ja menoni ovat muuttuneet?"))

    # --- Compared with Finland (Statistics Finland)
    home = household.get(customer_id)
    national = opendata.national_spending(
        overview["age"], (home.partner, home.children) if home else None
    )
    mine = {c: v / 3 * household.per_person_factor(c, home) for c, v in
            finance.get_spending(customer_id, 3)["by_category_eur"].items()}
    ratios = [(mine[c] / n["eur"], c, n["eur"]) for c, n in national["categories"].items()
              if n["comparable"] and n["eur"] > 0 and c in mine]
    if ratios and max(ratios)[0] > 1.3:
        _, cat, eur = max(ratios)
        add(Suggestion(
            "finland_cat", "finland", 66,
            f"How does my {adjective(cat)} spending compare with the Finnish average?",
            f"Miten {_FI_CATEGORY[cat][1]} vertautuvat suomalaisten keskiarvoon?",
            f"People your age in Finland spend about {_eur(eur)} a month on this",
            f"Ikäisesi suomalaiset käyttävät tähän noin {_eur(eur)} kuussa",
        ))
    if home:
        add(Suggestion("finland", "finland", 72,
                       "How does my household compare with similar households in Finland?",
                       "Miten kotitalouteni vertautuu vastaaviin suomalaisiin kotitalouksiin?",
                       f"Compared with {national['group']}, using what you told us",
                       "Vertailu kaltaisiisi kotitalouksiin kertomasi perusteella"))
    else:
        add(Suggestion("finland", "finland", 46,
                       "How do I compare with the Finnish average for my age?",
                       "Miten vertaudun ikäisteni suomalaisten keskiarvoon?",
                       "Open data from Statistics Finland", "Tilastokeskuksen avointa dataa"))

    # --- Investing, only when it is relevant for this customer
    investing = finance.get_investing_summary(customer_id)
    left = investing["avg_monthly_left_on_account_eur"]
    covers = investing["balance_covers_months_of_spending"] or 0
    if investing["invests_from_this_account"]:
        invested = investing["invested_last_12_months_eur"]
        add(Suggestion("inv_how_much", "investing", 60, "How much have I invested this year?",
                       "Paljonko olen sijoittanut tänä vuonna?",
                       f"You moved {_eur(invested)} into investments in the last 12 months",
                       f"Siirsit sijoituksiin {_eur(invested)} viimeisen 12 kuukauden aikana"))
        add(Suggestion("inv_share", "investing", 50, "What share of my income do I invest?",
                       "Kuinka suuren osan tuloistani sijoitan?"))
    elif covers >= 6 and left > 0:
        add(Suggestion("inv_start", "investing", 74, "What should I know before I start investing?",
                       "Mitä minun pitäisi tietää ennen kuin alan sijoittaa?",
                       f"Your balance covers about {covers:.0f} months of your spending",
                       f"Saldosi kattaa noin {covers:.0f} kuukauden menosi"))
        add(Suggestion("inv_room", "investing", 56,
                       "How much could I set aside for investing each month?",
                       "Paljonko voisin laittaa sivuun sijoittamiseen kuukaudessa?",
                       f"About {_eur(left)} is left on your account each month",
                       f"Tilillesi jää noin {_eur(left)} kuussa"))
    elif left >= 200:
        add(Suggestion("inv_room", "investing", 54,
                       "How much could I set aside for investing each month?",
                       "Paljonko voisin laittaa sivuun sijoittamiseen kuukaudessa?",
                       f"About {_eur(left)} is left on your account each month",
                       f"Tilillesi jää noin {_eur(left)} kuussa"))

    # --- Needs and wants
    plan = costs.budget(customer_id, 12)
    free = next(s for s in plan["segments"] if s["key"] == "free")
    if free["share_pct"] and free["share_pct"] >= 25:
        add(Suggestion("free_choice", "spending", 68, "How could I reduce my free-choice spending?",
                       "Miten voisin vähentää vapaavalintaista kulutustani?",
                       f"Free-choice spending takes {free['share_pct']} % of your income",
                       f"Vapaavalintainen kulutus vie {free['share_pct']} % tuloistasi"))
    add(Suggestion("needs_wants", "spending", 44,
                   "How is my spending split between needs and wants?",
                   "Miten kulutukseni jakautuu välttämättömiin ja vapaavalintaisiin menoihin?"))

    # --- Home and mortgage
    if mortgage["has_mortgage_application"]:
        if mortgage["final_decision"] == "rejected":
            add(Suggestion("mtg_why", "mortgage", 100,
                           "Why was my mortgage application rejected?",
                           "Miksi asuntolainahakemukseni hylättiin?",
                           "Your application was not approved",
                           "Hakemustasi ei hyväksytty"))
            add(Suggestion("mtg_improve", "mortgage", 85,
                           "What could improve my chances next time?",
                           "Mikä parantaisi mahdollisuuksiani ensi kerralla?"))
        else:
            add(Suggestion("mtg_look", "mortgage", 62,
                           "Can you walk me through my mortgage application?",
                           "Voitko käydä asuntolainahakemukseni läpi?",
                           "Your application was approved", "Hakemuksesi hyväksyttiin"))
            add(Suggestion("mtg_payment", "mortgage", 58,
                           "What would my monthly loan payment be?",
                           "Mikä olisi lainani kuukausierä?"))
        add(Suggestion("mtg_ltv", "mortgage", 52,
                       "What does loan-to-value mean in my application?",
                       "Mitä luototusaste tarkoittaa hakemuksessani?"))
    else:
        # A price that fits their income, not a fixed example.
        max_price = income / finance.REQUIRED_INCOME_PER_LOAN_EUR / finance.LTV_LIMIT
        price = max(50_000, round(max_price * 0.9 / 10_000) * 10_000)
        price_txt = f"{price:,}".replace(",", " ")
        young = overview["age"] < 35
        add(Suggestion("mtg_afford", "mortgage", 78 if young else 64,
                       f"Could I afford a {price_txt} € home?",
                       f"Olisiko minulla varaa {price_txt} €:n asuntoon?",
                       "A price range that fits your income",
                       "Tuloihisi sopiva hintaluokka"))
        add(Suggestion("mtg_down", "mortgage", 60 if young else 50,
                       f"How much down payment would I need for a {price_txt} € home?",
                       f"Paljonko omaa rahaa tarvitsisin {price_txt} €:n asuntoon?",
                       f"You have {_eur(overview['current_balance_eur'])} on your account",
                       f"Tililläsi on {_eur(overview['current_balance_eur'])}"))
        add(Suggestion("mtg_max", "mortgage", 54, "How big a home loan could my income support?",
                       "Kuinka suuren asuntolainan tuloni kestävät?"))
    return sorted(out, key=lambda s: -s.score)


def starters(customer_id: str, lang: str = "en", count: int = 4) -> list[dict]:
    """The most relevant opening questions: one per topic, always one about a home."""
    picked: list[Suggestion] = []
    for s in candidates(customer_id):
        if all(s.topic != p.topic for p in picked):
            picked.append(s)
    picked = picked[:count]
    if all(s.topic != "mortgage" for s in picked):
        home = next(s for s in candidates(customer_id) if s.topic == "mortgage")
        picked = picked[: count - 1] + [home]
    return [s.as_dict(lang) for s in picked]


# After talking about a topic, these topics are natural next steps.
_NEXT_TOPICS = {
    "spending": ["peers", "finland", "trend", "spending"],
    "peers": ["finland", "spending", "trend", "peers"],
    "finland": ["peers", "spending", "trend"],
    "trend": ["investing", "spending", "peers", "trend"],
    "mortgage": ["mortgage", "trend", "spending"],
    "investing": ["trend", "spending", "investing"],
}
# A question the tool has just answered isn't worth suggesting again.
_ANSWERED_BY = {
    "get_mortgage_status": {"mtg_why", "mtg_look"},
    "mortgage_calculator": {"mtg_afford"},
    "compare_to_finland": {"finland"},
    "get_overview": {"savings"},
    "get_investing_overview": {"inv_how_much", "inv_start"},
}


def follow_ups(
    customer_id: str,
    topics: list[str],
    asked: list[str],
    tools_used: list[str] | None = None,
    user_text: str = "",
    count: int = 3,
) -> list[str]:
    """Next questions that fit what was just discussed and this customer.

    Never repeats a question that was asked, always includes one about a
    home or mortgage, and follows the customer's language.
    """
    lang = lang_of(user_text)
    asked_set = {a.strip().lower() for a in asked}
    answered = {i for t in tools_used or [] for i in _ANSWERED_BY.get(t, ())}
    if "finland" in (topics or []):
        answered |= {"finland", "finland_cat"}  # just discussed
    if "peers" in (topics or []):
        answered |= {"peers"}
    pool = [s for s in candidates(customer_id)
            if s.id not in answered and s.en.lower() not in asked_set
            and s.fi.lower() not in asked_set]

    order: list[str] = []
    for topic in topics or []:
        order += [t for t in _NEXT_TOPICS.get(topic, []) if t not in order]
    order += [t for t in ("spending", "peers", "trend", "finland", "investing", "mortgage")
              if t not in order]

    picked: list[Suggestion] = []
    # One question per topic first, walking the topics in order.
    for topic in order:
        match = next((s for s in pool if s.topic == topic and s not in picked), None)
        if match:
            picked.append(match)
    picked = picked[:count]
    home = next((s for s in pool if s.topic == "mortgage"), None)
    if home and all(s.topic != "mortgage" for s in picked):
        picked = picked[: count - 1] + [home]
    return [s.text(lang) for s in picked]
