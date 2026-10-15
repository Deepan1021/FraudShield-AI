# FraudShield AI

**Intelligent Digital Payment Risk Assessment System** - an explainable, rule-based fraud-risk analysis platform.

FraudShield AI evaluates a digital payment across seven security dimensions (amount, time, device trust, location,
login behaviour, transaction frequency, account activity). It turns the transaction into structured logical facts,
reasons over a versioned production-rule base with **forward chaining**, resolves conflicts deterministically and
returns a **LOW / MEDIUM / HIGH / CRITICAL** decision, a recommended action and a complete, auditable explanation.
The core is a genuine symbolic expert system - no black box, no hard-coded results, no `eval()`.

| Risk | Recommended action |
|---|---|
| LOW | Approve |
| MEDIUM | Request additional identity verification (MFA) |
| HIGH | Temporarily block |
| CRITICAL | Flag for cyber analyst review |

> **Verification status.** See `VERIFICATION_REPORT.md` for exactly what was executed and what was not.
> The backend core, database, services and reports were tested in a sandbox. The FastAPI, React and Playwright layers
> are fully implemented but could not be executed there (no network access to install their packages) - run the
> commands below on your machine to execute them.

## Quick start on Windows 10/11

1. **Install prerequisites** (once)
   * Python 3.10 - 3.12 from <https://www.python.org/downloads/> - tick **"Add python.exe to PATH"**.
   * Node.js 18+ (LTS) from <https://nodejs.org/>.
2. **Extract** `FraudShield_AI.zip` to any folder (for example `C:\Projects\FraudShield_AI`).
3. **Open the folder in VS Code** (`File > Open Folder`) and open a terminal (`Ctrl+``), or double-click the files below in Explorer.
4. **Run setup once** (creates the virtual environment, installs dependencies, initialises the database):
   ```bat
   setup.bat
   ```
5. **Start the application**:
   ```bat
   run.bat
   ```
   Two windows open (API and UI) and the browser opens <http://localhost:5173>.
6. **Load the demonstration data** (optional, labelled *synthetic*): on the Dashboard click **Seed demo data**, or run
   `run.bat seed`.

| What | URL |
|---|---|
| Web application (development) | <http://localhost:5173> |
| API | <http://127.0.0.1:8000/api/health> |
| Interactive API docs (OpenAPI) | <http://127.0.0.1:8000/docs> |

`run.bat prod` builds the UI and serves everything from <http://127.0.0.1:8000> (single process).

### Manual commands (equivalent to the scripts)

```bat
cd FraudShield_AI
py -3 -m venv .venv
.venv\Scripts\activate
pip install -r backend\requirements.txt
copy .env.example .env
python scripts\init_db.py
python scripts\seed_demo.py                                  :: optional demo data
uvicorn app.main:app --app-dir backend --reload              :: terminal 1 (API)

cd frontend
npm install
npm run dev                                                  :: terminal 2 (UI)
```

### Docker (optional)

```bash
docker compose up --build        # http://localhost:8000 - data persists in the fraudshield_data volume
```

### macOS / Linux

`./run.sh` (or `./run.sh prod`, `./run.sh seed`).

## Running the tests

```bat
:: Backend (activated venv, from the project root)
cd backend
python -m unittest discover -s tests -t .     :: or: python -m pytest

:: Frontend component tests
cd ..\frontend
npm test

:: End-to-end (starts its own API with an isolated database + the UI)
npx playwright install chromium
npm run e2e

:: Static project validation
cd ..
python scripts\verify_project.py
```

Details and the honest execution record are in `TESTING.md` and `VERIFICATION_REPORT.md`.

## What you can do in the console

Dashboard - Transaction Analysis (the seven inputs) - Analysis Result (decision, drivers, rule trace graph, facts,
behavioural deviations, audit metadata) - Transaction History (search, filters, sorting, pagination) - Transaction
Details (forensic tabs) - Rule Explorer - Knowledge Base - Analytics - Reports (in-app viewer, JSON/CSV/PDF export) -
Audit Logs - System Settings (status, database snapshot, demo data) - About.

Try the **Critical composite** quick scenario: `HighAmount(TXN001) + UntrustedDevice + NewLocation + NightTransaction
+ SuspiciousLogin + HighFrequency` yields `CRITICAL` through rules R01, R30, R40, R41, R43 ... and the page shows exactly why.

## Configuration

Environment variables (see `.env.example`): `APP_ENV`, `DATABASE_URL`, `LOG_LEVEL`, `API_HOST`, `API_PORT`,
`CORS_ORIGINS`, `MAX_REQUEST_BYTES`, `REPORTS_DIR`, `BACKUPS_DIR`, `SERVE_FRONTEND`, `AUTO_SEED_DEMO`.
No secrets are needed. The default database is `database/fraudshield.db`.

## Project structure

```
FraudShield_AI/
  backend/app/
    api/ (routes, dependencies)    schemas/ (Pydantic)         core/ (config, logging, errors, version)
    domain/ (enums, models)        preprocessing/ (validation, constraints, behaviour, features, facts)
    expert_system/ (predicates, rules + rulebase_v1.json, knowledge_base, inference, classification, explainability)
    services/ (analysis, transactions, analytics, reports, system, container)
    repositories/ + database/ (SQLite, migrations, unit of work)    reporting/ (JSON, CSV, PDF)
    pipeline.py (framework-free `analyze_transaction`)
  backend/tests/                   frontend/ (React + TypeScript + Vite + Tailwind, unit + e2e tests)
  data/ (synthetic demo data)      scripts/   docs/   database/   reports/   backups/   logs/
  run.bat  setup.bat  run.sh  Dockerfile  docker-compose.yml
```

## Using the engine without the web layer

```python
import sys; sys.path.insert(0, "backend")
from app.pipeline import analyze_transaction
result = analyze_transaction({"transaction_id": "TXN001", "user_id": "USER001", "amount": 85000,
    "transaction_time": "02:15 AM", "device_trust": "Untrusted", "location": "Delhi",
    "login_behavior": "Suspicious", "transaction_frequency": 12, "account_activity": "Active"})
print(result["risk_level"], result["recommendation"]["action"])
```

## Known limitations

* Decision-support demonstrator, not a certified banking control; rules and thresholds are illustrative, not calibrated on real fraud data.
* The persistence layer uses Python's built-in `sqlite3` behind a repository / unit-of-work interface (not SQLAlchemy); see `docs/database.md` for the PostgreSQL migration path.
* The Rule-based Risk Severity Index is a transparent weighted count, not a probability.
* No user authentication: the API is intended for local / trusted-network use (see `SECURITY.md`).
* Request-size limiting relies on the `Content-Length` header; put a reverse proxy in front for hostile networks.
