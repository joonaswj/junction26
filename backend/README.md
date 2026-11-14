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
uv run python -m junction26.data.download
```

This saves them to `backend/data/raw/` (gitignored) and checks that the large file downloaded correctly. No git-lfs needed.

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

## API endpoints

Start the backend (`uv run fastapi dev src/main.py` in `backend`) and see http://localhost:8000/docs.

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
