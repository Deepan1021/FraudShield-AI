# API

Base path `/api`. Interactive documentation: `/docs` (Swagger) and `/redoc` (disabled when `APP_ENV=production`).

Success: `{"success": true, "data": ...}`. Error: `{"success": false, "error": {"code", "message", "field?", "details?"}}`.

| Method | Path | Purpose | Status |
|---|---|---|---|
| GET | `/health` | Live API / database / rule engine / knowledge base status | 200 |
| GET | `/system/info`, `/system/startup-report` | Versions, read-only configuration, thresholds, startup checks | 200 |
| POST | `/system/backup` | Write a database snapshot (never overwrites) | 201 |
| POST | `/system/seed-demo` | Seed synthetic demonstration data (idempotent) | 201 |
| POST | `/transactions/analyze` | Run the full pipeline and persist the result | 201 / 409 / 422 |
| GET | `/transactions` | Search: `q, risk, recommendation, location, device_trust, rule, status, user_id, date_from, date_to, sort, order, page, page_size` | 200 |
| GET | `/transactions/{id}` | Full forensic detail (result + audit events) | 200 / 404 |
| GET | `/transactions/{id}/facts` `/rules` `/trace` `/explanation` `/report` | Facts, rules evaluated/triggered, trace + graph, XAI explanation, report document | 200 / 404 |
| GET | `/dashboard/summary` | Dashboard metrics | 200 |
| GET | `/analytics`, `/analytics/risk-distribution` | Analytics (also `/analytics/summary`) | 200 |
| GET | `/rules`, `/knowledge-base` | Rule base (read-only), predicates and dependencies | 200 |
| GET | `/audit-logs` | Searchable audit trail | 200 |
| POST | `/reports` | Generate + export (`json`, `csv`, `pdf`) | 201 / 404 / 422 |
| GET | `/reports`, `/reports/{id}`, `/reports/{id}/download` | List, viewer document, file download | 200 / 404 |

## Analyze request

```json
{"transaction_id": "TXN001", "user_id": "USER001", "amount": 85000, "transaction_time": "02:15",
 "device_trust": "UNTRUSTED", "location": "Delhi", "login_behavior": "SUSPICIOUS",
 "transaction_frequency": 12, "account_activity": "ACTIVE",
 "device_id": "DEV-X91", "channel": "UPI", "currency": "INR"}
```

Unknown fields and credential-like fields (`card_number`, `cvv`, `pin`, `otp`, `password`, ...) are rejected with 422.

## Error codes

`VALIDATION_ERROR`, `UNKNOWN_FIELD`, `SENSITIVE_FIELD_REJECTED`, `NOT_FOUND`, `DUPLICATE_TRANSACTION` (409),
`REQUEST_TOO_LARGE` (413), `REPORT_ERROR`, `DATABASE_ERROR`, `RULE_BASE_ERROR`, `INTERNAL_ERROR` (500, no internals exposed).

Response bodies are documented with a generic `ApiResponse` envelope; request bodies use full Pydantic schemas
(`TransactionIn`, `ReportRequest`). The frontend contract is mirrored in `frontend/src/types/api.ts`.
