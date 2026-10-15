# Security

FraudShield AI is a risk-analysis demonstrator, **not** a certified banking security system and **not** a payment processor.

## Implemented controls

| Area | Control |
|---|---|
| Input | Pydantic type/length limits at the edge; strict domain validation (regex-validated IDs, enum parsing, finite positive amounts, time parsing); unknown fields rejected |
| Privacy | Credential fields (card, cvv, pin, otp, password, secret...) are rejected; none are stored; log filter redacts card-like digit runs |
| Code execution | No `eval`/`exec`; rules are JSON data parsed structurally; a test scans the source for these calls |
| SQL | Parameterised queries only; sort columns come from a whitelist; LIKE wildcards are escaped; injection tests in `test_database.py` |
| Files | Report/backup names are sanitised, written only inside configured directories, never overwrite; downloads resolve through the database and are checked against the reports directory |
| API | Explicit CORS origins (no `*`); GET/POST only; `Content-Length` limit (413); `nosniff`, `X-Frame-Options: DENY`, `no-referrer`; structured errors with no stack traces; OpenAPI disabled in production |
| Frontend | React escapes all output; no `dangerouslySetInnerHTML`; no secrets in the bundle |
| Config | Environment variables / `.env` (git-ignored); startup refuses an empty rule base or an invalid schema |
| Spreadsheet export | CSV cells starting with `= + - @` are neutralised |

## Not implemented (by design for a local demonstrator)

* **Authentication / authorisation.** There are no user accounts, so none were faked. Bind to `127.0.0.1` (the default) or put an authenticating reverse proxy in front before exposing the service.
* TLS termination, rate limiting, and body-size enforcement for chunked uploads - use a reverse proxy.
* Rule editing through the UI (the rule explorer is read-only, which avoids an unsafe-expression surface).

## Dependency pinning

Python packages are pinned in `backend/requirements.txt` and JavaScript packages in `frontend/package.json`. Run `pip list --outdated` / `npm audit` periodically.
