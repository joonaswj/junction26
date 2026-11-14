# junction26
MixedSignals-tiimin projekti


# Ohjeet tarvittavien työkalujen lataamiseen ja projektin alustamiseen tietokoneellasi:

1) Avaa pääte laitteessasi.
2) lataa GIT:
    [GIT asennus](https://www.google.com/url?sa=t&source=web&rct=j&opi=89978449&url=https://git-scm.com/install/&ved=2ahUKEwiir7axrfaXAxW_JxAIHSBJIksQFnoECBEQAQ&usg=AOvVaw1piXI91x_chH4u0QiwVJRs)


4) Tee lokaali kansio  esim. "junction" nimellä (ei väliä, näkyy vaan sulle)

5) Kopioi SSH-linkki täältä GitHubin reposta leikepöydälle: mene repositoryyn -> klikkaa code -> kopioi ssh-linkki

6) Nyt kun GIT on ladattuna, voit käyttää git-komentoja. Aja ```git clone <ssh-linkki>```
   tekemässäsi lokaalissa kansiossa -> Nyt sulla on meidän yhteinen projekti ja voit tehdä siihen muutoksia. (Älä kuitenkaan vielä tee)

8) Lataa uv (environment manager):

   Windows powershellissä: ```irm https://astral.sh/uv/install.ps1 | iex ```

   Linux ja macOS terminaalissa: ```curl -LsSf https://astral.sh/uv/install.sh | sh```

9) Lataa python virtuaaliympäristöön ja synkronisoi environment manager. Aja komennot `backend`-kansiossa (siellä on `pyproject.toml`), ei projektin juuressa. Älä tee virtuaaliympäristöä käsin (`python -m venv`), uv tekee sen `backend/.venv`-kansioon:
   ```
   cd backend

   uv python install
   
   uv sync --locked
   ```

# Workflow yleisesti:
 - Käytetään [git](https://git-scm.com/)tiä versionhallintajärjestelmänä ja koodin jakamisessa keskenämme
 - Käytetään pythonin riippuvuuksien ja virtuaalikoneen konfiguroinnissa eli environment managerina [uv](https://docs.astral.sh/uv/):ta
   
 - Tehdään projektissa vastuualueet projektin eri vaiheille jo suunnitteluvaiheessa
 - Jokainen työstää projektia omalla branchillaan ja kun projektissa on toimiva osakokonaisuus, yhdistetään branchit main-branchiin
 - Jos lisäät kirjaston projektii, niin kerro siitä muille! Tuo dependency muutos täytyy syncronisoida jokaisen erikseen. Komennot cheatsheetissä.
 - Tähän tarvitaan muutama git- ja uv-komento, jotka käydään läpi seuraavaksi

# GIT-workflow:

1) Alussa on ajettu git clone. Sitä ei enää tehdä.

2) Luo oma branch:

   ```git checkout -b uusi_branch main``` // tietyssä brancheissa tehdyt muutokset näkyy vain siinä branchissa

4) Kun olet saanut jotain aikaan, ne siirretään GitHubiin seuraavasti:
   
   I) ```git add muutettu_tiedosto1 muutettu_tiedosto2 ...```
   
   II) ```git status```
   
   II) ```git commit -m  "moromoro"```
   
   III) ```git push origin branchin_nimi```
   
6) 
    Jos tarvitset jonkun toisen vastuualueen koodia, täytyy ajaa:

   I) ```git switch oma_branch``` // vaihda omaan brachiin

   II) ```git pull --no-rebase origin haluttu_branch``` // hae viimeiset pushatut muutokset toisen branchista ja mergaa ne omaan

8) Merge main branchiin:
   
   Pidetään huolta, että merge main branchiin on aina yhdessä sovittu, eli käytännössä kun yksi vaihe projektia on saatu tehtyä. Tällä tavoin pystymme yrittää välttää merge conflicteja. Niiden ratkominen vie yleensä aikaa. Käytännössä kaikki pushaa omat branchinsa GitHubiin, tekee GitHubissa pull requestit mainiin ja ne hyväksytään manuaalisesti GitHubissa.

9) Kun siirrytään seuraavaan vaiheeseen, aletaan työstää mergattua mainia. Nyt se täytyy pullata:
 
    I) ```git switch main``` //vaihda mainiin

    II) ```git pull --no-rebase origin main``` // pullaa main


Tämän jälkeen iteroidaan vaiheita 2-6.

# Cheatsheet:
<table> <thead> <tr> <th>Situation</th> <th>Command</th> </tr> </thead> <tbody> <tr> <td>Clone repository (first time only)</td> <td><code>git clone &lt;ssh-link&gt;</code></td> </tr> <tr> <td>Install required Python version</td> <td><code>uv python install</code></td> </tr> <tr> <td>Set up / synchronize Python environment</td> <td><code>uv sync --locked</code></td> </tr> <tr> <td>Check local changes</td> <td><code>git status</code></td> </tr> <tr> <td>See actual unstaged changes</td> <td><code>git diff</code></td> </tr> <tr> <td>See staged changes</td> <td><code>git diff --staged</code></td> </tr> <tr> <td>List local branches</td> <td><code>git branch</code></td> </tr> <tr> <td>Create new branch and switch to it</td> <td><code>git checkout -b oma_branch main</code></td> </tr> <tr> <td>Stage specific files</td> <td><code>git add file1 file2 ...</code></td> </tr> <tr> <td>Commit changes</td> <td><code>git commit -m "Description"</code></td> </tr> <tr> <td>Push your branch to GitHub</td> <td><code>git push origin oma_branch</code></td> </tr> <tr> <td>Pull another person's branch into your own</td> <td> <code>git switch oma_branch</code><br> <code>git pull --no-rebase origin wanted_branch</code> </td> </tr> <tr> <td>Switch to main</td> <td><code>git switch main</code></td> </tr> <tr> <td>Update main from GitHub</td> <td><code>git pull --no-rebase origin main</code></td> </tr> <tr> <td>Merge updated main into your own branch</td> <td> <code>git switch oma_branch</code><br> <code>git merge main</code> </td> </tr> <tr> <td>Add a new Python library</td> <td><code>uv add library_name</code></td> </tr> <tr> <td>Add a specific library version</td> <td><code>uv add "library_name==version"</code></td> </tr> <tr> <td>Save and push dependency changes to GitHub</td> <td> <code>git add pyproject.toml uv.lock</code><br> <code>git commit -m "Add numpy"</code><br> <code>git push origin oma_branch</code> </td> </tr> <tr> <td>Synchronize dependencies after pulling changes</td> <td><code>uv sync --locked</code></td> </tr> <tr> <td>Remove a Python library</td> <td><code>uv remove library_name</code></td> </tr> </tbody> </table>

# Ohjeet koodin testaukseen:

- Kun teet funktioita tai luokkia pythonissa ja haluat testata niitä, kirjoita testi-koodi seuraavasti tiedoston loppuun:
 ```python
if __name__ == "__main__":
    testaa(funktio1())
```

  Tällöin python ajaa testikoodin vain kun ajat kyseisen tiedoston python-interpreterillä. Jos tiedostoa käytetään kirjastona toisessa ohjelmassa, testikoodia ei ajeta.

Junction26 – Development Environment Setup

This guide explains how to set up and run Junction26 on Windows, macOS and Ubuntu/Linux.

1. Prerequisites

You need to install:

Git – Version control.
Python 3.11+ – Backend.
uv – Python package manager.
Node.js (LTS) – JavaScript runtime.
npm – Frontend package manager (included with Node.js).
2. Install the prerequisites
Windows
A. Install Git

Download and install:

https://git-scm.com/downloads/win

B. Install Python

Download Python 3.11 or newer:

https://www.python.org/downloads/

During installation, enable Add Python to PATH.

Verify:

powershell
python --version

C. Install uv

Open PowerShell:

powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"


Restart PowerShell and verify:

powershell
uv --version

D. Install Node.js

Download the LTS version:

https://nodejs.org/

Verify:

powershell
node -v
npm -v

macOS
A. Install Homebrew (if not already installed)

Open Terminal:

bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"


Follow the installation instructions.

B. Install Git and Python
bash
brew install git python

C. Install uv
bash
curl -LsSf https://astral.sh/uv/install.sh | sh


Restart Terminal or reload your shell:

bash
source ~/.zshrc


Verify:

bash
uv --version

D. Install Node.js
bash
brew install node


Verify:

bash
node -v
npm -v

Ubuntu / Linux
A. Install Git, Python and other requirements
bash
sudo apt update

sudo apt install -y git curl python3 python3-venv

B. Install uv
bash
curl -LsSf https://astral.sh/uv/install.sh | sh


Reload your terminal:

bash
source ~/.bashrc


Verify:

bash
uv --version

C. Install Node.js

We recommend using NVM.

Install NVM:

bash
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.40.3/install.sh | bash


Reload your terminal:

bash
source ~/.bashrc


Install the latest LTS version:

bash
nvm install --lts
nvm use --lts


Verify:

bash
node -v
npm -v

3. Clone the GitHub repository

The following steps are identical for all operating systems.

Open a terminal (PowerShell on Windows, Terminal on macOS/Linux).

bash
git clone <GITHUB_REPOSITORY_URL>


Navigate into the project:

bash
cd junction26


Replace <GITHUB_REPOSITORY_URL> with the actual repository URL.

4. Install backend dependencies

pyproject.toml and uv.lock are in the backend directory, so run uv from there:

bash
cd backend
uv sync


This automatically:

Creates a virtual environment (backend/.venv).
Installs the Python dependencies.
Uses uv.lock to maintain consistent dependency versions.

Important: You do not need to run uv init, create a venv yourself (python -m venv) or manually install FastAPI. The dependencies are already defined in the repository.

In VS Code, pick backend/.venv/bin/python as the interpreter (Command Palette → Python: Select Interpreter), otherwise imports show as errors.

5. Install frontend dependencies

From the project root, navigate into the frontend directory:

bash
cd frontend


Install dependencies:

bash
npm install


This installs all dependencies specified in package.json and uses package-lock.json to maintain consistent versions.

6. Run the application

You need TWO terminals running simultaneously.

Terminal 1 – FastAPI Backend

From the backend directory:

bash
cd backend
uv run fastapi dev src/main.py --host 0.0.0.0


The backend will run at:

API: http://localhost:8000
Swagger documentation: http://localhost:8000/docs
Terminal 2 – React Frontend

Navigate into the frontend:

bash
cd frontend


Start Vite:

bash
npm run dev


The frontend will run at:

http://localhost:5173

7. Verify the installation

Open your browser and check:

Service	URL
React frontend	http://localhost:5173
FastAPI backend	http://localhost:8000
Swagger API docs	http://localhost:8000/docs

If everything works, the React frontend should be able to communicate with FastAPI.

8. Working with Git

Before starting development, get the latest changes:

bash
git pull


Create a feature branch:

bash
git checkout -b feature/your-feature-name


After making changes:

bash
git add .
git commit -m "Describe your changes"
git push origin feature/your-feature-name


Then create a Pull Request on GitHub.

When dependencies change
Python dependencies

If someone adds a Python dependency using (in the backend directory):

bash
cd backend
uv add package-name


They should commit both:

backend/pyproject.toml
backend/uv.lock

Other teammates run:

bash
cd backend
uv sync

Frontend dependencies

If someone installs a frontend dependency:

bash
cd frontend
npm install package-name


They should commit both:

package.json
package-lock.json

Other teammates run:

bash
cd frontend
npm install

9. Common problems
Port 8000 is already in use

Another FastAPI instance might already be running.

Stop the previous server with Ctrl+C.

Alternatively, use another port:

bash
uv run fastapi dev src/main.py --port 8001

npm command not found

Node.js is not installed or isn't available in your PATH.

Reinstall Node.js and restart your terminal.

uv command not found

Restart your terminal. If necessary, ensure the uv installation directory is included in your PATH.

Frontend cannot connect to backend

Check that:

Both servers are running.
FastAPI is running on port 8000.
The frontend API URL is http://localhost:8000.
FastAPI CORS allows http://localhost:5173.
10. Quick Start (After Initial Setup)

Whenever you want to work on Junction26:

Terminal 1 – Backend:

bash
cd junction26/backend
uv run fastapi dev src/main.py --host 0.0.0.0


Terminal 2 – Frontend:

bash
cd junction26/frontend
npm run dev


Open http://localhost:5173.

You're ready to develop!

Happy hacking! 🚀
# S-Pankki data

The challenge data comes from https://github.com/hackjunction/Junction-2026-S-pankki. The CSVs are **not** committed to this repo (the transactions file is ~350 MB). Download them once, from the `backend` directory:

```bash
cd backend
uv run python -m junction26.data.download
```

This saves them to `backend/data/raw/` (gitignored) and checks that the large file downloaded correctly. No git-lfs needed.

# Ohjelman backendin ja frontendin ajaminen
```bash
cd backend 

uv run uvicorn main:app --reload
```

```bash
cd frontend
npm run dev

```

Web GUI (Vite): `cd frontend && npm run dev`, then open http://localhost:5173. On a phone in the same network, run `npm run dev -- --host` and open `http://<laptop IP>:5173`. Start the backend with `--host 0.0.0.0` too.

## Using the data in Python

```python
from junction26.data import (
    load_transactions,       # ~3.6M rows: customer_id, tx_date, category, tx_amount_eur, ...
    load_customers,          # customer_id, customer_postal_code, customer_age
    load_mortgage_events,    # mortgage application event history (mortgage_customer_id)
    load_mortgage_outcomes,  # links mortgage_customer_id -> customer_id + final decision
)

tx = load_transactions(["CUST04457"])  # or load_transactions() for everything
```

The first `load_transactions()` takes a few seconds; after that a cached copy in `backend/data/cache/` loads instantly.

## Raw data endpoints

All endpoints are listed at http://localhost:8000/docs when the backend is running.

| Endpoint | Returns |
|---|---|
| `GET /data/summary` | Counts, date range, categories |
| `GET /customers?limit=&offset=&has_mortgage=` | Customers |
| `GET /customers/{customer_id}` | One customer + their mortgage applications |
| `GET /customers/{customer_id}/transactions?start=&end=&category=&limit=&offset=` | Their transactions |
| `GET /mortgages?decision=approved\|rejected` | Mortgage application outcomes |
| `GET /mortgages/{mortgage_customer_id}/events` | Event history for one application |

## Spending insights vs similar users

`junction26/insights.py` compares each customer's spending (last 12 months, EUR per month) to similar users: same age band and income band, or same income band only if that group has fewer than 20 people. Customers with fewer than 12 card purchases a month are flagged `low_activity` (they probably use another card too). They are left out of peer stats and don't get "you spend less" insights.

| Endpoint | Returns |
|---|---|
| `GET /customers/{customer_id}/insights?limit=5` | Biggest differences vs peers, with ready-made text like "You spend €222 more per month on groceries than similar users…" |
| `GET /customers/{customer_id}/peer-comparison` | Every category: you vs peer median, difference, percentile |

In Python: `from junction26.insights import get_insights, get_comparison`. The first call takes a few seconds, then it's cached.

## App endpoints (dashboard)

| Endpoint | Returns |
|---|---|
| `GET /demo-customers?limit=10` | Customers with full histories to "log in" as, half with a mortgage application |
| `GET /customers/{customer_id}/overview` | Balance, average monthly income and spending, savings rate, top categories |
| `GET /customers/{customer_id}/spending?months=3&category=` | Spending per category, or one category per month + top merchants |
| `GET /customers/{customer_id}/trend?months=12` | Month by month: income, spending, invested, net, end balance |
| `GET /customers/{customer_id}/mortgage` | Mortgage application outcome and recent events |

"Today" in the data is 2026-09-30, the last transaction date. "Last 3 months" means up to that date.

## Chatbot

The chatbot runs on [Featherless](https://featherless.ai) (OpenAI-compatible API), configured in `junction26/featherless.py`. The model gets a short snapshot of the logged-in customer's numbers, and can call functions in `junction26/finance.py` (overview, spending, trend, peer comparison, transaction search, mortgage status, mortgage calculator) for more detail. The server fills in `customer_id`, so the model can only see that one customer's data. If a model doesn't support tool calling, the chat automatically falls back to answering from the snapshot.

Setup: put your key in `backend/.env` (gitignored, never commit it), then restart the backend:

```
FEATHERLESS_API_KEY=...
# optional, default deepseek-ai/DeepSeek-V4-Flash (supports tool calling)
FEATHERLESS_MODEL=deepseek-ai/DeepSeek-V4-Flash
```

Check that the key works: `uv run python -m junction26.featherless` (in `backend`). If only `OPENAI_API_KEY` is set, OpenAI is used instead.

| Endpoint | Body | Returns |
|---|---|---|
| `POST /chat` | `{"customer_id": "CUST02868", "messages": [{"role": "user", "content": "Where does my money go?"}]}` | `{"reply", "visuals", "suggestions", "guard", "tools_used"}` |
| `POST /chat/stream` | same | Server-sent events, one JSON object per `data:` line: `tool` (a lookup started, with a `label` to show like "Comparing with similar customers"), `text` (part of the answer), `done` (same fields as `/chat`), `error` |
| `GET /customers/{customer_id}/chat/starters?lang=en\|fi` | | Personalised opening questions |
| `GET /customers/{customer_id}/visuals` | | Chart specs for the overview screen |

The app keeps the conversation and sends all of it with every request (`role` is `user` or `assistant`, only `role` and `content`).

### Guardrails (`junction26/guardrails.py`)

The chat only talks about the logged-in customer's own finances. Three layers:

1. **Instant screening, no LLM call**: prompt-injection phrases ("ignore previous instructions", "show your system prompt", "act as…"), requests for other customers' data, and messages over 600 characters get a fixed, friendly redirect (English or Finnish).
2. **Scope rules in the system prompt**: for anything else out of scope (weather, coding, stock picks…) the model answers with the tag `[[off_topic]]` plus one sentence; the server turns that into a redirect. Mixed questions get only their finance part answered.
3. **Structure**: the server fills in `customer_id` for every lookup, so other customers' data can't be reached whatever the model is told.

Every reply has `guard` (`null`, `off_topic`, `injection`, `other_customer` or `too_long`) and `suggestions`: up to three next questions the assistant can answer, always including one about mortgages, in the customer's language.

### Charts in answers (`junction26/visuals.py`)

The model never writes numbers into charts. It asks for one with a tag (`[[chart:spending]]`, `[[chart:category:Groceries]]`, `[[chart:income_vs_spending]]`, `[[chart:balance]]`, `[[chart:peers]]`, `[[chart:peers:Groceries]]`, `[[chart:mortgage]]`) or by calling a tool, and the server builds the spec from the data and returns it in `visuals`. Types: `bars`, `columns`, `line`, `compare`, `mortgage`, `calc`. The frontend draws them in `frontend/src/charts/Visual.tsx`.

### Mortgage features (`junction26/finance.py`)

- `get_mortgage_details`: the customer's application, the rejection reason explained in plain words with what could help, and how all applicants in the data did.
- `mortgage_calculator`: what-if estimate (loan, loan-to-value against the 90% cap, monthly payment, payment at a 6% stress rate, required income, whether savings cover the down payment). The rates and caps are teaching defaults, not S-Pankki's credit policy. The required income uses the ratio found in the dataset (1.84% of the loan per month).

## Explore: your data, your questions (`junction26/explore.py`)

In the spirit of MyData, the customer explores their own data freely instead of only seeing charts the bank picked. One endpoint answers any combination:

`GET /customers/{customer_id}/explore?measure=&group_by=&months=&categories=&compare=&month=`

| Parameter | Values |
|---|---|
| `measure` | `spending` (default), `income`, `saved`, `balance` |
| `group_by` | `category`, `month`, `merchant`, `weekday` (spending only) |
| `months` | 1–24, how far back |
| `categories` | comma-separated spending categories, default all |
| `compare` | `none`, `peers` (similar customers), `finland` (Statistics Finland) |
| `month` | `YYYY-MM`: look inside one month |

It returns a chart spec (`visual`), the same numbers as a `table`, a one-sentence `summary`, `notes` and `source` for any benchmark, and `questions` to hand over to the assistant about exactly this view. The assistant has the same power through its `explore_data` tool.

| Endpoint | Returns |
|---|---|
| `GET /customers/{customer_id}/explore/transactions?months=&categories=&month=&limit=&offset=` | The raw transactions behind a view |
| `GET /customers/{customer_id}/export?format=csv\|json` | Download all your transactions (data portability) |
| `GET /customers/{customer_id}/my-data` | What data is held and how it is used (transparency) |

### Open data: Statistics Finland (`junction26/opendata.py`)

The "Finnish average" benchmark is real open data: Statistics Finland's Household Budget Survey 2022, table 14q4 "Household consumption expenditure by age of reference person", consumption per consumption unit in EUR per month (CC BY 4.0). The figures are saved in `opendata_statfi.json`. Refresh them from the API with `uv run python -m junction26.opendata`.

Statistics Finland's categories (COICOP) are matched to the bank's approximately, see `CATEGORY_MAP`. Housing is deliberately not compared: the statistics leave out loan repayments, so the national figure says little about a customer's housing payments. The app shows the source and these caveats under every chart that uses the benchmark.

### Suggested questions (`junction26/suggestions.py`)

Suggestions are tailored to the customer's profile: savings rate, biggest differences to similar customers and to the Finnish average, balance trend, unusual months, housing share of income, mortgage status and age. Each starter comes with a `why` ("You spend 130 € more a month than similar customers"), so the customer can see why it was suggested. Home price examples are sized to the customer's income. Follow-ups after an answer move to related topics, never repeat a question, and always include one about a home or mortgage.

### From charts to chat and back (frontend)

Every chart is a starting point (`frontend/src/charts/Visual.tsx`): tapping a bar, a month or a comparison row offers "Ask about this" (sends a question about that exact element to the assistant) and a drill-down in Explore ("See month by month", "Look inside Jul", "See the merchants"). Charts in chat answers have an "Explore" button that opens the same view in the Explore tab.

### Cost types (`junction26/costs.py`)

Every spending category has a cost type:

| Type | Categories | How a "per month" figure is calculated |
|---|---|---|
| Fixed essentials | Housing | Average of the selected period |
| Essentials that vary | Groceries, Utilities, Health, Transportation, Home & Tech | Always the customer's **12-month average** |
| Free-choice spending | Restaurants, Entertainment, Lifestyle, Travel | Average of the selected period |

In the data, housing varies about 3 % from month to month, groceries about 80 % and health about 160 %, so one month of an essential that varies says little. Wherever such a cost is shown per month or compared with others, the 12-month average is used whatever period is selected, and similar customers are measured the same way. Looking inside a single month shows the real amounts, each next to the customer's usual month ("Groceries 1 224 €, usually 399 €").

`costs.budget()` gives the income split (fixed, varies, free choice, left over, of which invested). The overview draws it as the `budget` chart, Explore can slice by `group_by=type`, and category views are grouped by cost type. Month charts carry a `reference` line at the customer's usual month.

### Reflection (frontend `components/ReflectCard.tsx`)

The overview has "A moment to reflect": free-choice spending as a yearly amount, the three biggest free-choice categories per year, a "what if you trimmed it by X %" slider, and the question "Does this feel right for you?". "I'd change it" hands the chosen cut to the assistant.

### Investing

The assistant can talk about the customer's own saving and investing (`finance.get_investing_summary`: invested in the last 12 months, what is left each month, how many months of spending the balance covers) and the general basics of investing. It never names or recommends products, funds, stocks or crypto and never predicts returns; those questions are redirected. Investing questions are only suggested when relevant: the customer already invests, or has money left each month and a balance that covers at least six months of spending.

### Household details (`junction26/household.py`)

A bank account shows one person's payments, not a household's life: someone whose partner buys the groceries looks like they barely eat. So the customer can optionally say whether they live with a partner, how many children are at home, and with three sliders roughly how much of the **housing**, the **groceries** and the **utilities** the partner pays (couples often split these differently). Only those three count as shared. The form shows what each slider position means in euros for the whole household. It is self-reported, never required, editable and deletable, and stored in `backend/data/household.json` (not in git).

| Endpoint | Does |
|---|---|
| `GET /customers/{customer_id}/household` | The details (or `null`) and what this account pays for housing, groceries and utilities in a usual month |
| `PUT /customers/{customer_id}/household` | Save `{"partner": true, "children": 2, "partner_housing_pct": 50, "partner_groceries_pct": 80, "partner_utilities_pct": 50}` |
| `DELETE /customers/{customer_id}/household` | Remove them |

What it changes:

- **The Finnish benchmark** becomes "households like yours" (Statistics Finland table 14ph: people living alone, couples without children, single-parent households, two-parent families with children, over-64 households) instead of "people your age".
- **Groceries and utilities** are scaled up to the whole household using the partner's share, then divided by household size in consumption units (first adult 1, second adult 0.5, each child 0.3, the scale Statistics Finland uses). Both sides of the comparison are then per person. Housing is not compared with the Finnish average at all (see above), but its share is used to explain insights.
- **Insights** that the household explains get an `expected_because` note ("Your partner pays about 80 % of your groceries, so this account shows only part of what your household spends on it") and are shown after the others.
- **The assistant and the suggested questions** know the details. Without them, a comparison that would benefit shows an invitation to add them.
