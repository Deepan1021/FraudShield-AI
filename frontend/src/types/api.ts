// Contract mirrored from the FastAPI backend (backend/app/pipeline.py and backend/app/schemas/api.py).
export type RiskLevel = 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';
export type ActionCode = 'APPROVE' | 'REQUEST_MFA' | 'TEMPORARILY_BLOCK' | 'FLAG_FOR_ANALYST_REVIEW';
export type FactKind = 'observed' | 'behavioural' | 'constraint' | 'indicator' | 'risk' | 'external';

export interface TransactionInput {
  transaction_id: string;
  user_id: string;
  amount: number;
  transaction_time: string;
  device_trust: string;
  location: string;
  login_behavior: string;
  transaction_frequency: number;
  account_activity: string;
  currency?: string;
  channel?: string;
  device_id?: string;
  merchant_category?: string;
  session_id?: string;
}

export interface Recommendation {
  action: ActionCode;
  label: string;
  urgency: string;
  rationale: string;
  escalated_by_rules: string[];
}

export interface Fact {
  predicate: string;
  entity: string;
  args: string[];
  text: string;
  value: boolean;
  kind: FactKind;
  source: string;
  confidence: number;
  derivation_rule: string | null;
  parents: string[];
  supported_by: string[];
  seq: number;
  created_at: string;
}

export interface Feature { name: string; value: boolean | number | null; category: string; description: string; kind: string }
export interface Constraint { id: string; name: string; passed: boolean; severity: string; message: string }
export interface Deviation {
  dimension: string; label: string; evaluated: boolean; anomalous: boolean;
  observed: unknown; baseline: unknown; ratio: number | null; message: string;
}
export interface BehaviourAnalysis { baseline_available: boolean; anomaly_count: number; deviations: Deviation[] }

export interface RuleExecution {
  seq: number; cycle: number; rule_id: string; rule_name: string; rule_version: string; category: string;
  priority: number; severity: string; formula: string; bindings: Record<string, string>;
  matched_facts: string[]; derived_fact: string; new_fact: boolean; conflict_set_size: number;
  selected_because: string; tags: string[];
}
export interface TriggeredRule {
  rule_id: string; rule_name: string; category: string; priority: number; severity: string; formula: string;
  times_fired: number; derived_facts: string[]; tags: string[]; explanation: string; rule_version: string;
}
export interface PipelineStage { key: string; label: string; status: string; duration_ms: number; detail: string }

export interface Driver { fact: string; predicate: string; text: string; role: 'risk_driver' | 'mitigating'; kind: string; category: string }
export interface InferenceStep {
  step: number; cycle: number; rule_id: string; rule_name: string; statement: string; formula: string;
  new_fact: boolean; selected_because: string; explanation: string;
}
export interface ProofNode { fact: string; kind: string; rule: string | null; source: string; children: ProofNode[] }
export interface GraphNode { id: string; type: 'fact' | 'rule'; label: string; name?: string; kind: string; layer: number; decisive: boolean }
export interface GraphEdge { from: string; to: string; decisive: boolean }
export interface TraceGraphData { nodes: GraphNode[]; edges: GraphEdge[]; max_layer: number }

export interface Explanation {
  question: string; narrative: string; risk_level: RiskLevel; drivers: Driver[];
  observed_evidence: { fact: string; text: string; kind: string }[];
  derived_evidence: { fact: string; text: string; kind: string; source: string }[];
  behavioural_deviations: Deviation[]; violated_constraints: Constraint[];
  logical_inference: InferenceStep[];
  final_decision: {
    risk_level: RiskLevel; decisive_fact: string | null; decisive_rules: string[]; resolution: string;
    recommendation: string; recommendation_rationale: string;
  };
  why_chain: ProofNode | null;
  graph: TraceGraphData;
}

export interface Assessment {
  risk_level: RiskLevel; decisive_fact: string | null; decisive_rules: string[];
  candidates: { level: RiskLevel; fact: string; derived_by: string[]; mitigating: boolean }[];
  overridden_levels: string[]; rationale: string; policy: string[];
}
export interface SeverityIndex { name: string; value: number; max: number; note: string; breakdown: { fact: string; predicate: string; weight: number }[] }

export interface AnalysisResult {
  evaluation_id: string; transaction_id: string; user_id: string; risk_level: RiskLevel;
  recommendation: Recommendation; assessment: Assessment; severity_index: SeverityIndex;
  input_snapshot: Record<string, string | number | null>;
  validation: { passed: boolean; errors: unknown[]; normalisations: { field: string; from: string; to: string }[] };
  constraints: Constraint[]; behavioural_analysis: BehaviourAnalysis; features: Feature[];
  facts: Fact[]; initial_facts: Fact[]; derived_facts: Fact[]; rules_evaluated: string[];
  triggered_rules: TriggeredRule[]; reasoning_trace: RuleExecution[];
  inference: { cycles: number; firings: number; terminated_by: string; conflict_resolution_strategy: string[] };
  explanation: Explanation; pipeline: PipelineStage[];
  decision_status?: string; synthetic?: boolean;
  metadata: {
    timestamp: string; submitted_at?: string; processing_time_ms: number; engine_version: string; rulebase_version: string;
    rulebase_name: string; app_version: string; schema_version?: number; thresholds: Record<string, number>;
  };
}

export interface TransactionRow {
  pk: number; transaction_id: string; user_id: string; amount: number; currency: string; transaction_time: string;
  device_trust: string; device_id: string | null; location: string; login_behavior: string; transaction_frequency: number;
  account_activity: string; channel: string | null; status: string; is_synthetic: number; submitted_at: string;
  evaluation_id: string | null; risk_level: RiskLevel | null; severity_index: number | null; summary: string | null;
  processing_time_ms: number | null; recommendation_action: ActionCode | null; recommendation_label: string | null;
}
export interface Paged<T> { items: T[]; total: number; page: number; page_size: number; pages: number }

export interface AuditEvent {
  id: number; timestamp: string; event_type: string; actor: string; transaction_id: string | null; risk_level: RiskLevel | null;
  rule_id: string | null; description: string; metadata: Record<string, unknown> | null;
  engine_version: string; rulebase_version: string; app_version: string;
}

export interface RecentEvent {
  transaction_id: string; user_id: string; amount: number; currency: string; location: string; submitted_at: string;
  risk_level: RiskLevel; severity_index: number; summary: string | null; recommendation_action: ActionCode; recommendation_label: string;
}
export interface TrendDay { day: string; total: number; low: number; medium: number; high: number; critical: number }
export interface TopRule { rule_id: string; rule_name: string; category: string; firings: number; transactions: number }

export interface DashboardSummary {
  total_transactions: number; risk_counts: Record<RiskLevel, number>; low: number; medium: number; high: number; critical: number;
  blocked_or_flagged: number; high_risk_percentage: number; avg_processing_ms: number;
  risk_distribution: { risk_level: RiskLevel; count: number }[];
  recent_alerts: RecentEvent[]; recent_analyses: RecentEvent[];
  trend: { days: TrendDay[]; sufficient: boolean }; top_rules: TopRule[]; synthetic_transactions: number;
}

export interface AnalyticsSummary {
  total_evaluations: number; avg_processing_ms: number; avg_severity_index: number; high_risk_percentage: number; critical_count: number;
  risk_distribution: { risk_level: RiskLevel; count: number }[];
  recommendation_distribution: { action: ActionCode; count: number }[];
  trend: { days: TrendDay[]; sufficient: boolean };
  locations: { location: string; transactions: number; high_risk: number }[];
  device_anomalies: { device_trust: string; transactions: number; high_risk: number }[];
  behavioural_anomalies: { predicate: string; occurrences: number }[];
  indicator_frequency: { predicate: string; occurrences: number }[];
  top_rules: TopRule[];
}

export interface HealthStatus {
  status: 'ok' | 'degraded'; api: string; database: string; rule_engine: string; knowledge_base: string; active_rules: number;
  versions: { application: string; engine: string; rulebase: string; schema: number | null; schema_expected: number };
  uptime_seconds: number; environment: string;
}

export interface RuleDef {
  id: string; name: string; category: string; description: string; explanation: string; antecedents: string[];
  consequent: string; formula: string; priority: number; severity: RiskLevel; min_matches: number | null; tags: string[];
  source: string; version: string; status: 'ACTIVE' | 'INACTIVE';
}
export interface RulesPayload { name: string; version: string; rules: RuleDef[]; dependencies: { from: string; to: string; via: string }[]; conflict_resolution: string[] }

export interface PredicateDef {
  name: string; kind: FactKind; category: string; description: string; driver_text: string; weight: number; arity: number;
  used_in_rules: string[]; derived_by_rules: string[];
}
export interface KnowledgeBasePayload {
  rulebase: { name: string; version: string; rule_count: number; active_rule_count: number };
  predicates: PredicateDef[]; predicate_kinds: Record<string, number>; rule_dependencies: { from: string; to: string; via: string }[]; status: string;
}

export interface ReportSection {
  key: string; title: string; type: 'text' | 'kv' | 'list' | 'table';
  data: string | [string, unknown][] | string[] | { columns: string[]; rows: unknown[][] };
}
export interface ReportDoc { report_id: string; title: string; generated_at: string; transaction_id: string; risk_level: RiskLevel; sections: ReportSection[] }
export interface ReportRecord {
  report_id: string; format: string; filename: string | null; size_bytes: number | null; status: string; error: string | null;
  created_at: string; transaction_id: string;
}
export interface GeneratedReport { report_id: string; format: string; filename: string; size_bytes: number; created_at: string; download_url: string; report: ReportDoc }

export interface SystemInfo {
  name: string; full_name: string; versions: HealthStatus['versions']; config: Record<string, unknown>;
  thresholds: Record<string, number>; rulebase: { name: string; version: string }; transaction_count: number; synthetic_count: number;
}
export interface StartupCheck { name: string; status: 'PASS' | 'FAIL' | 'WARN'; detail: string }

export interface TransactionDetail { transaction: TransactionRow; result: AnalysisResult; audit: AuditEvent[] }
export interface TracePayload { transaction_id: string; executions: RuleExecution[]; graph: TraceGraphData; inference: AnalysisResult['inference']; pipeline: PipelineStage[] }
