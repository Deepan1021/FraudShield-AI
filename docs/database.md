# Database

SQLite (`database/fraudshield.db`), WAL mode, `PRAGMA foreign_keys=ON`. One thread-local connection per worker thread.
Schema is created by forward-only migrations (`app/database/migrations.py`) tracked in `schema_version`; an application
refuses to start against a newer schema.

## Entities

| Table | Purpose |
|---|---|
| `users` | user id, optional behavioural baseline (JSON), synthetic flag |
| `transactions` | one row per analysed transaction; `transaction_id` UNIQUE; input snapshot; decision status |
| `transaction_features` | extracted features (value as JSON) |
| `facts` | all initial and derived facts with provenance (source, derivation rule, parents) |
| `rules` | rule definitions per `(rule_id, rulebase_version)` so historical reasoning stays auditable |
| `rule_executions` | forward-chaining trace (cycle, bindings, matched facts, derived fact, selection reason) |
| `inference_results` | risk level/rank, severity index, validation/constraint/behaviour/pipeline/explanation JSON, full `result_json`, durations, engine/rule base/app/schema versions |
| `recommendations` | action, label, urgency, rationale, escalating rules |
| `audit_logs` | timestamped events with actor, transaction, risk, rule, versions |
| `reports` | generated report files (status, size, path) |

Relationships: `transactions 1-1 inference_results 1-1 recommendations`; `transactions 1-N features / facts / rule_executions / reports`; all child tables use `ON DELETE CASCADE`. Indexes cover user, submitted_at, location, device trust, status, risk level, rule id, audit timestamp/event/transaction and fact predicate/kind.

## Transaction lifecycle

`AnalysisService.analyze` runs the pipeline (read-only), then opens **one** unit of work (`BEGIN IMMEDIATE ... COMMIT`) that inserts the user (if new), transaction, features, facts, result, rule executions, recommendation and audit events. Any exception triggers `ROLLBACK`, so a failed analysis leaves no partial data. Validation and duplicate rejections are recorded in the audit log in their own small unit of work.

## Audit trail

Events: `TRANSACTION_RECEIVED`, `ANALYSIS_COMPLETED`, `RECOMMENDATION_ISSUED`, `HIGH_RISK_ALERT`, `VALIDATION_REJECTED`, `DUPLICATE_REJECTED`, `REPORT_GENERATED`, `REPORT_FAILED`, `DATABASE_BACKUP`, `DEMO_DATA_SEEDED`, `SYSTEM_STARTUP`. `result_json` stores the complete result so any decision can be reconstructed exactly.

## Migrating to PostgreSQL

All SQL is isolated in `app/repositories/*` and `app/database/database.py`. To migrate: add a `PostgresDatabase` exposing `unit_of_work()`, `read()`, `initialize()`, `schema_version()`; port the repositories (parameter style `?` -> `%s`; the schema is portable - replace `AUTOINCREMENT` with `GENERATED ... AS IDENTITY` and `date(...)` with `::date`); point `DATABASE_URL` at it. Services, the AI engine and the API need no changes. (An ORM such as SQLAlchemy can be introduced behind the same repository interfaces; it was not used here because it could not be installed and tested in the build environment.)

## Backup and reset

`POST /api/system/backup` (Settings page) uses SQLite's online backup API to write `backups/fraudshield_backup_<timestamp>.db` (never overwritten). `python scripts/reset_dev_db.py --yes` deletes the local database and only runs when `APP_ENV=development`.
