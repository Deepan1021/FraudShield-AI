# Architecture

```
React UI (Vite, TypeScript, Tailwind)        presentation only - never touches SQLite
        |  HTTP /api (JSON, envelope {success,data} | {success:false,error})
FastAPI routes + Pydantic schemas             api/, schemas/    thin: validate transport, call services
        |
Application services                          services/         orchestration, transactions, audit, reports
        |                          \
Preprocessing                        Repositories / Unit of work   repositories/, database/
validation, constraints,                       |
behaviour, features, facts                  SQLite (database/fraudshield.db, versioned schema)
        |
Expert system (pure Python, no web/DB imports)  expert_system/
 predicates -> knowledge base -> matcher -> forward chaining -> conflict resolution -> classifier
 -> recommendation -> explainability (explanation, proof tree, trace graph)
```

## Principles

* **Layering.** The AI engine imports nothing from the web or database layers; `app.pipeline.analyze_transaction()` runs it standalone. Services are the only code that combines the engine with persistence.
* **Rules are data.** `expert_system/rules/rulebase_v1.json` is parsed by a structural parser (regex-validated atoms, predicate registry, arity, variable-safety, cycle detection). Nothing is evaluated as code.
* **Single sources of truth.** Risk levels and actions live in `domain/enums.py`; versions in `core/version.py` and the rule base file; colours only in the frontend.
* **Atomic persistence.** One `UnitOfWork` writes transaction, features, facts, rule executions, result, recommendation and audit events; any failure rolls back everything.
* **Failure isolation.** Domain errors map to structured API errors; unexpected errors are logged and returned without stack traces; a failed report is recorded without touching the analysis; the React app has an error boundary.

## Analysis flow (`pipeline.py`, `AnalysisService`)

1. Validate and normalise (reject credentials, unknown fields, bad enums/times/amounts)
2. Constraint evaluation (channel limit, plausible frequency, device/login consistency -> `SessionIntegrityConcern`)
3. Load the user baseline (service) and analyse behaviour (amount, frequency, device, location, hour)
4. Feature extraction (structured, no scoring)
5. Fact generation (boolean features -> `Fact(predicate, entity, kind, source, ...)`); optional `FactProvider` extensions
6. Knowledge base + working memory
7. Rule matching (unification, m-of-n rules) -> forward chaining with refraction -> conflict resolution
8. Risk classification (security-first resolution), recommendation (separate engine, tag-based escalation)
9. Explanation (observed / derived / logical inference / final decision), proof tree, trace graph
10. Persist (atomic) + audit trail; return the full result

See `docs/ai-engine.md` for the rule semantics and `docs/database.md` for the schema.

## Extensibility

* New evidence sources (IP reputation, device fingerprinting, ML anomaly scores) implement `FactProvider` and emit facts with registered predicates; rules then use them. The symbolic core stays the decision maker.
* New rule versions are new rule base files with a new `rulebase_version`; every result stores the version it was produced with.
* Another database: implement `Database.unit_of_work()` and the repositories (all SQL lives there).
