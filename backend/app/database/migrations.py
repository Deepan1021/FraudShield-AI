"""Ordered, forward-only schema migrations. Add new entries; never edit applied ones."""

MIGRATION_1 = """
CREATE TABLE users (
    user_id TEXT PRIMARY KEY,
    display_name TEXT,
    baseline_json TEXT,
    is_synthetic INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE TABLE transactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    transaction_id TEXT NOT NULL UNIQUE,
    user_id TEXT NOT NULL REFERENCES users(user_id),
    amount REAL NOT NULL,
    currency TEXT NOT NULL,
    channel TEXT,
    transaction_time TEXT NOT NULL,
    device_trust TEXT NOT NULL,
    device_id TEXT,
    location TEXT NOT NULL,
    login_behavior TEXT NOT NULL,
    transaction_frequency INTEGER NOT NULL,
    account_activity TEXT NOT NULL,
    merchant_category TEXT,
    session_id TEXT,
    input_snapshot_json TEXT NOT NULL,
    is_synthetic INTEGER NOT NULL DEFAULT 0,
    status TEXT NOT NULL DEFAULT 'ANALYZED',
    submitted_at TEXT NOT NULL
);
CREATE INDEX idx_tx_user ON transactions(user_id);
CREATE INDEX idx_tx_submitted ON transactions(submitted_at);
CREATE INDEX idx_tx_location ON transactions(location);
CREATE INDEX idx_tx_device_trust ON transactions(device_trust);
CREATE INDEX idx_tx_status ON transactions(status);
CREATE TABLE transaction_features (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    transaction_pk INTEGER NOT NULL REFERENCES transactions(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    category TEXT,
    kind TEXT,
    value_json TEXT NOT NULL,
    description TEXT
);
CREATE INDEX idx_features_tx ON transaction_features(transaction_pk);
CREATE TABLE facts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    transaction_pk INTEGER NOT NULL REFERENCES transactions(id) ON DELETE CASCADE,
    seq INTEGER NOT NULL,
    predicate TEXT NOT NULL,
    entity TEXT NOT NULL,
    text TEXT NOT NULL,
    kind TEXT NOT NULL,
    source TEXT NOT NULL,
    derivation_rule TEXT,
    parents_json TEXT NOT NULL,
    supported_by_json TEXT NOT NULL,
    confidence REAL NOT NULL DEFAULT 1.0,
    created_at TEXT NOT NULL
);
CREATE INDEX idx_facts_tx ON facts(transaction_pk);
CREATE INDEX idx_facts_predicate ON facts(predicate);
CREATE INDEX idx_facts_kind ON facts(kind);
CREATE TABLE rules (
    rule_id TEXT NOT NULL,
    rulebase_version TEXT NOT NULL,
    name TEXT NOT NULL,
    category TEXT NOT NULL,
    priority INTEGER NOT NULL,
    severity TEXT NOT NULL,
    status TEXT NOT NULL,
    version TEXT NOT NULL,
    description TEXT NOT NULL,
    definition_json TEXT NOT NULL,
    PRIMARY KEY (rule_id, rulebase_version)
);
CREATE TABLE inference_results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    evaluation_id TEXT NOT NULL UNIQUE,
    transaction_pk INTEGER NOT NULL UNIQUE REFERENCES transactions(id) ON DELETE CASCADE,
    risk_level TEXT NOT NULL,
    risk_rank INTEGER NOT NULL,
    severity_index INTEGER NOT NULL,
    summary TEXT,
    decisive_rules_json TEXT NOT NULL,
    validation_json TEXT NOT NULL,
    constraints_json TEXT NOT NULL,
    behaviour_json TEXT NOT NULL,
    pipeline_json TEXT NOT NULL,
    explanation_json TEXT NOT NULL,
    result_json TEXT NOT NULL,
    processing_time_ms REAL NOT NULL,
    cycles INTEGER NOT NULL,
    firings INTEGER NOT NULL,
    engine_version TEXT NOT NULL,
    rulebase_version TEXT NOT NULL,
    app_version TEXT NOT NULL,
    schema_version INTEGER NOT NULL,
    created_at TEXT NOT NULL
);
CREATE INDEX idx_inf_risk ON inference_results(risk_level);
CREATE INDEX idx_inf_created ON inference_results(created_at);
CREATE TABLE rule_executions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    transaction_pk INTEGER NOT NULL REFERENCES transactions(id) ON DELETE CASCADE,
    inference_id INTEGER NOT NULL REFERENCES inference_results(id) ON DELETE CASCADE,
    seq INTEGER NOT NULL,
    cycle INTEGER NOT NULL,
    rule_id TEXT NOT NULL,
    rule_version TEXT NOT NULL,
    rulebase_version TEXT NOT NULL,
    rule_name TEXT NOT NULL,
    category TEXT NOT NULL,
    priority INTEGER NOT NULL,
    severity TEXT NOT NULL,
    bindings_json TEXT NOT NULL,
    matched_facts_json TEXT NOT NULL,
    derived_fact TEXT NOT NULL,
    new_fact INTEGER NOT NULL,
    conflict_set_size INTEGER NOT NULL,
    selected_because TEXT NOT NULL
);
CREATE INDEX idx_exec_tx ON rule_executions(transaction_pk);
CREATE INDEX idx_exec_rule ON rule_executions(rule_id);
CREATE TABLE recommendations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    transaction_pk INTEGER NOT NULL UNIQUE REFERENCES transactions(id) ON DELETE CASCADE,
    inference_id INTEGER NOT NULL REFERENCES inference_results(id) ON DELETE CASCADE,
    action TEXT NOT NULL,
    label TEXT NOT NULL,
    urgency TEXT NOT NULL,
    rationale TEXT NOT NULL,
    escalated_by_json TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE INDEX idx_rec_action ON recommendations(action);
CREATE TABLE audit_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    event_type TEXT NOT NULL,
    actor TEXT NOT NULL,
    transaction_id TEXT,
    risk_level TEXT,
    rule_id TEXT,
    description TEXT NOT NULL,
    metadata_json TEXT,
    engine_version TEXT NOT NULL,
    rulebase_version TEXT NOT NULL,
    app_version TEXT NOT NULL
);
CREATE INDEX idx_audit_ts ON audit_logs(timestamp);
CREATE INDEX idx_audit_event ON audit_logs(event_type);
CREATE INDEX idx_audit_tx ON audit_logs(transaction_id);
CREATE TABLE reports (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    report_id TEXT NOT NULL UNIQUE,
    transaction_pk INTEGER NOT NULL REFERENCES transactions(id) ON DELETE CASCADE,
    format TEXT NOT NULL,
    filename TEXT,
    file_path TEXT,
    size_bytes INTEGER,
    status TEXT NOT NULL,
    error TEXT,
    created_at TEXT NOT NULL
);
CREATE INDEX idx_reports_tx ON reports(transaction_pk);
"""

# (version, description, script). The script runs inside one transaction together with the version row.
MIGRATIONS = [
    (1, "Initial schema: users, transactions, features, facts, rules, inference, recommendations, audit, reports", MIGRATION_1),
]
LATEST_SCHEMA_VERSION = MIGRATIONS[-1][0]
