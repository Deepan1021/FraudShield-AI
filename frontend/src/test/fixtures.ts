import type { AnalysisResult, DashboardSummary, TraceGraphData, TransactionRow } from '../types/api';

export const GRAPH: TraceGraphData = {
  nodes: [
    { id: 'HighAmount(TXN001)', type: 'fact', label: 'HighAmount', kind: 'observed', layer: 0, decisive: true },
    { id: 'UntrustedDevice(TXN001)', type: 'fact', label: 'UntrustedDevice', kind: 'observed', layer: 0, decisive: true },
    { id: 'R01@1', type: 'rule', label: 'R01', name: 'Untrusted device is unverified', kind: 'rule', layer: 1, decisive: true },
    { id: 'UnverifiedDevice(TXN001)', type: 'fact', label: 'UnverifiedDevice', kind: 'indicator', layer: 2, decisive: true },
    { id: 'R30@2', type: 'rule', label: 'R30', name: 'High amount from unverified device', kind: 'rule', layer: 3, decisive: true },
    { id: 'HighRisk(TXN001)', type: 'fact', label: 'HighRisk', kind: 'risk', layer: 4, decisive: true },
    { id: 'NewLocation(TXN001)', type: 'fact', label: 'NewLocation', kind: 'behavioural', layer: 0, decisive: false },
  ],
  edges: [
    { from: 'UntrustedDevice(TXN001)', to: 'R01@1', decisive: true },
    { from: 'R01@1', to: 'UnverifiedDevice(TXN001)', decisive: true },
    { from: 'HighAmount(TXN001)', to: 'R30@2', decisive: true },
    { from: 'UnverifiedDevice(TXN001)', to: 'R30@2', decisive: true },
    { from: 'R30@2', to: 'HighRisk(TXN001)', decisive: true },
  ],
  max_layer: 4,
};

export const RESULT = {
  evaluation_id: 'EVAL-TEST00000001',
  transaction_id: 'TXN001',
  user_id: 'USER001',
  risk_level: 'HIGH',
  recommendation: { action: 'TEMPORARILY_BLOCK', label: 'Temporarily block transaction', urgency: 'IMMEDIATE', rationale: 'Policy: HIGH risk maps to temporarily block transaction.', escalated_by_rules: [] },
  assessment: { risk_level: 'HIGH', decisive_fact: 'HighRisk(TXN001)', decisive_rules: ['R30'], candidates: [], overridden_levels: [], rationale: 'HighRisk(TXN001) is the highest derived risk conclusion.', policy: [] },
  severity_index: { name: 'Rule-based Risk Severity Index', value: 30, max: 100, note: 'Not a probability.', breakdown: [] },
  input_snapshot: { transaction_id: 'TXN001', amount: 85000, location: 'Delhi' },
  validation: { passed: true, errors: [], normalisations: [] },
  constraints: [], behavioural_analysis: { baseline_available: true, anomaly_count: 0, deviations: [] }, features: [],
  facts: [], initial_facts: [], derived_facts: [], rules_evaluated: ['R01', 'R30'],
  triggered_rules: [{ rule_id: 'R30', rule_name: 'High amount from unverified device', category: 'Composite Risk', priority: 70, severity: 'HIGH', formula: 'HighAmount(x) ∧ UnverifiedDevice(x) → HighRisk(x)', times_fired: 1, derived_facts: ['HighRisk(TXN001)'], tags: [], explanation: '', rule_version: '1.0.0' }],
  reasoning_trace: [{ seq: 1, cycle: 1, rule_id: 'R01', rule_name: 'Untrusted device is unverified', rule_version: '1.0.0', category: 'Evidence Normalisation', priority: 90, severity: 'LOW', formula: '', bindings: { x: 'TXN001' }, matched_facts: ['UntrustedDevice(TXN001)'], derived_fact: 'UnverifiedDevice(TXN001)', new_fact: true, conflict_set_size: 2, selected_because: 'highest priority (90 > 70)', tags: [] }],
  inference: { cycles: 2, firings: 2, terminated_by: 'FIXPOINT', conflict_resolution_strategy: [] },
  explanation: {
    question: 'Why is this transaction HIGH?', narrative: 'Transaction TXN001 is classified HIGH.', risk_level: 'HIGH',
    drivers: [{ fact: 'HighAmount(TXN001)', predicate: 'HighAmount', text: 'High-value transaction', role: 'risk_driver', kind: 'observed', category: 'Transaction Risk' },
      { fact: 'UntrustedDevice(TXN001)', predicate: 'UntrustedDevice', text: 'Untrusted device', role: 'risk_driver', kind: 'observed', category: 'Device Risk' }],
    observed_evidence: [], derived_evidence: [], behavioural_deviations: [], violated_constraints: [], logical_inference: [],
    final_decision: { risk_level: 'HIGH', decisive_fact: 'HighRisk(TXN001)', decisive_rules: ['R30'], resolution: 'x', recommendation: 'Temporarily block transaction', recommendation_rationale: '' },
    why_chain: null, graph: GRAPH,
  },
  pipeline: [], metadata: { timestamp: '2026-10-01T10:00:00Z', processing_time_ms: 1.2, engine_version: '1.0.0', rulebase_version: '1.0.0', rulebase_name: 'FraudShield Expert Rule Base', app_version: '1.0.0', thresholds: {} },
} as unknown as AnalysisResult;

export const DASHBOARD: DashboardSummary = {
  total_transactions: 120, risk_counts: { LOW: 70, MEDIUM: 30, HIGH: 19, CRITICAL: 1 }, low: 70, medium: 30, high: 19, critical: 1,
  blocked_or_flagged: 20, high_risk_percentage: 16.7, avg_processing_ms: 0.8,
  risk_distribution: [{ risk_level: 'LOW', count: 70 }, { risk_level: 'MEDIUM', count: 30 }, { risk_level: 'HIGH', count: 19 }, { risk_level: 'CRITICAL', count: 1 }],
  recent_alerts: [{ transaction_id: 'TXN777', user_id: 'USER001', amount: 85000, currency: 'INR', location: 'Delhi', submitted_at: '2026-10-01T10:00:00Z', risk_level: 'CRITICAL', severity_index: 74, summary: 'Suspicious login behaviour; High-value transaction', recommendation_action: 'FLAG_FOR_ANALYST_REVIEW', recommendation_label: 'Flag for cyber analyst review' }],
  recent_analyses: [], trend: { days: [], sufficient: false }, top_rules: [{ rule_id: 'R21', rule_name: 'New geographic location', category: 'Geographic Risk', firings: 22, transactions: 22 }], synthetic_transactions: 120,
};

export const ROWS: TransactionRow[] = [
  { pk: 1, transaction_id: 'TXN001', user_id: 'USER001', amount: 85000, currency: 'INR', transaction_time: '02:15', device_trust: 'UNTRUSTED', device_id: 'DEV-X91', location: 'Delhi', login_behavior: 'SUSPICIOUS', transaction_frequency: 12, account_activity: 'ACTIVE', channel: 'UPI', status: 'UNDER_REVIEW', is_synthetic: 1, submitted_at: '2026-10-01T02:15:00Z', evaluation_id: 'E1', risk_level: 'CRITICAL', severity_index: 90, summary: 's', processing_time_ms: 3, recommendation_action: 'FLAG_FOR_ANALYST_REVIEW', recommendation_label: 'Flag' },
  { pk: 2, transaction_id: 'TXN002', user_id: 'USER002', amount: 2500, currency: 'INR', transaction_time: '14:30', device_trust: 'TRUSTED', device_id: 'DEV002', location: 'Chennai', login_behavior: 'NORMAL', transaction_frequency: 2, account_activity: 'ACTIVE', channel: 'UPI', status: 'APPROVED', is_synthetic: 1, submitted_at: '2026-10-01T14:30:00Z', evaluation_id: 'E2', risk_level: 'LOW', severity_index: 0, summary: 's', processing_time_ms: 1, recommendation_action: 'APPROVE', recommendation_label: 'Approve' },
];
