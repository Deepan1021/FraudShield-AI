# Verification report

Honest record of what was executed in the build environment and what was not.
The build sandbox had **no network access**, so FastAPI, Pydantic, React, Vite, Tailwind, Vitest and Playwright
could not be installed there. Python 3.12 (standard library + reportlab) and Node/TypeScript tooling were available.

## CORE TESTS (executed)

Command: `cd backend && python -m unittest discover -s tests -t .`

| Module | Tests | Result |
|---|---|---|
| test_validation | 10 | passed |
| test_preprocessing (constraints, behaviour, features, facts) | 13 | passed |
| test_expert_system (facts, rule base, matcher, forward chaining, conflict resolution, classifier, recommendation) | 39 | passed |
| test_scenarios (A Low, B Medium, C High, D Critical/TXN001, TXN002, explanation, graph, extension provider) | 15 | passed |
| test_database (migrations, FKs, rollback, filters, injection safety) | 11 | passed |
| test_services (integration: pipeline -> service -> SQLite, reports JSON/CSV/PDF, backup, seed, analytics) | 17 | passed |
| **Executed total** | **105** | **105 passed, 0 failed** |
| test_api (FastAPI TestClient) | 11 | **skipped** - fastapi/httpx not installed in the sandbox |

Acceptance scenario TXN001 (USER001 demo baseline) -> `CRITICAL` / `FLAG_FOR_ANALYST_REVIEW` through rules (R01, R03, R06, R12, R13, R30, R40, R41, R43, ...). TXN002 -> `LOW` / `APPROVE`. Scenario B -> `MEDIUM` / `REQUEST_MFA`, scenario C -> `HIGH` / `TEMPORARILY_BLOCK`; all produced by the rules (a test also asserts no source file special-cases a transaction id and none uses eval/exec).

Seeding the 74 synthetic transactions through the real pipeline produced LOW 39, MEDIUM 16, HIGH 11, CRITICAL 8 (classified by the engine, not stored in the CSV).

## FRESH-EXTRACTION CHECK (executed)

The ZIP was extracted to a clean directory and, from there: `verify_project.py` passed; the 116-test suite ran (105 passed, 11 skipped); `scripts/init_db.py` created the database and all six startup checks passed; `scripts/seed_demo.py` created 74 transactions; `reset_dev_db.py` refused without `--yes` and removed the database with it; the database re-initialised afterwards.

## STATIC VALIDATION (executed)

* `scripts/verify_project.py`: 37 required files present, all Python compiles, JSON valid, no TODO/FIXME markers, no `eval`/`exec`, no machine-specific paths, and all **17 frontend API calls match a backend route** (method + path).
* TypeScript: all 35 `.ts/.tsx` files (including tests, Playwright config and spec) parse with 0 syntax errors. A type-check with stubbed third-party typings reported no errors in project code other than one artefact of the stub (`ErrorBoundary` typed from `any`).

## WEB TESTS - NOT EXECUTED

Not executed in the current offline environment because required external packages could not be installed.

* FastAPI API tests (`backend/tests/test_api.py`) - skipped, written.
* Frontend component tests (Vitest + Testing Library: `frontend/src/**/*.test.tsx`, `utils.test.ts`) - written, not run.
* Playwright end-to-end tests (`frontend/e2e/fraudshield.spec.ts`: dashboard, critical flow, normal flow, validation + duplicate, history search/filter, details, rule explorer, report, audit, analytics, knowledge base) - written, not run.
* `npm install`, `vite build`, `tsc --noEmit` against the real typings, `docker compose build` - not run.
* The FastAPI application itself (startup, middleware, CORS, error handlers, OpenAPI) and the React UI were **not executed**; they have only been syntax/consistency checked. Expect that a first run on your machine may reveal small integration issues; run the commands in `README.md` / `TESTING.md` and report any failure.

## Deviations from the brief

* Persistence uses Python's built-in `sqlite3` behind repositories and a unit of work instead of SQLAlchemy (SQLAlchemy could not be installed and therefore could not be tested). See `docs/database.md` for the migration path.
* Response bodies are documented with a generic envelope schema; request bodies use full Pydantic models.
* `npm run build` uses `vite build` (no type-check gate); `npm run typecheck` runs `tsc --noEmit` separately.
* No authentication is implemented (documented in `SECURITY.md`).
