# Testing

## Layout

| Level | Location | Tooling | Needs |
|---|---|---|---|
| Unit | `backend/tests/test_validation.py`, `test_preprocessing.py`, `test_expert_system.py` | `unittest` (pytest-compatible) | Python only |
| Scenario / acceptance | `test_scenarios.py` (A Low, B Medium, C High, D Critical/TXN001, TXN002, monotonicity, graph/proof checks, extension provider) | `unittest` | Python only |
| Persistence | `test_database.py` (migrations, FKs, rollback, search filters, SQL-injection safety, cascade) | `unittest` + sqlite3 | Python only |
| Integration | `test_services.py` (transaction -> analysis service -> engine -> database, reports, backup, seed, analytics) | `unittest` | Python (+ reportlab for PDF) |
| API | `test_api.py` (envelopes, status codes, validation, CORS, limits, no stack traces, report flow) | FastAPI `TestClient` | `pip install -r backend/requirements.txt` |
| Frontend component | `frontend/src/**/*.test.tsx` | Vitest + Testing Library | `npm install` |
| End-to-end | `frontend/e2e/fraudshield.spec.ts` | Playwright | `npm install`, `npx playwright install chromium`, activated venv |
| Static | `scripts/verify_project.py` | Python | none |

## Commands

```bat
cd backend
python -m unittest discover -s tests -t .      :: all backend tests (API tests are skipped if fastapi/httpx are missing)
python -m pytest                               :: same tests with pytest
cd ..\frontend
npm test                                       :: component tests
npm run typecheck                              :: full TypeScript check (needs npm install)
npm run e2e                                    :: Playwright (starts API on :8000 with an isolated DB and UI on :5173)
cd .. && python scripts\verify_project.py
```

## Coverage

No coverage percentage is claimed. To measure it: `pip install coverage && cd backend && coverage run -m unittest discover -s tests -t . && coverage report`.

## What was actually executed

See `VERIFICATION_REPORT.md` - it records the real results of the build environment and lists everything that could not be executed there.
