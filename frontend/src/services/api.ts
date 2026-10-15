import type {
  AnalysisResult, AnalyticsSummary, AuditEvent, DashboardSummary, GeneratedReport, HealthStatus, KnowledgeBasePayload,
  Paged, ReportDoc, ReportRecord, RulesPayload, StartupCheck, SystemInfo, TracePayload, TransactionDetail,
  TransactionInput, TransactionRow, Fact,
} from '../types/api';

const BASE = '/api';

export class ApiError extends Error {
  code: string;
  field?: string;
  details?: { field: string; message: string }[];
  status: number;
  constructor(status: number, code: string, message: string, field?: string, details?: { field: string; message: string }[]) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.code = code;
    this.field = field;
    this.details = details;
  }
}

type Params = Record<string, string | number | boolean | string[] | undefined | null>;

function qs(params?: Params): string {
  if (!params) return '';
  const sp = new URLSearchParams();
  Object.entries(params).forEach(([k, v]) => {
    if (v === undefined || v === null || v === '' || (Array.isArray(v) && v.length === 0)) return;
    sp.set(k, Array.isArray(v) ? v.join(',') : String(v));
  });
  const s = sp.toString();
  return s ? `?${s}` : '';
}

async function request<T>(method: 'GET' | 'POST', path: string, body?: unknown, params?: Params): Promise<T> {
  let res: Response;
  try {
    res = await fetch(`${BASE}${path}${qs(params)}`, {
      method,
      headers: body !== undefined ? { 'Content-Type': 'application/json', Accept: 'application/json' } : { Accept: 'application/json' },
      body: body !== undefined ? JSON.stringify(body) : undefined,
    });
  } catch {
    throw new ApiError(0, 'NETWORK_ERROR', 'Cannot reach the FraudShield API. Check that the backend is running.');
  }
  let payload: any = null;
  try {
    payload = await res.json();
  } catch {
    /* non-JSON response */
  }
  if (!res.ok || !payload || payload.success === false) {
    const err = payload?.error;
    throw new ApiError(res.status, err?.code ?? 'HTTP_ERROR', err?.message ?? `Request failed (${res.status})`, err?.field, err?.details);
  }
  return payload.data as T;
}

export const api = {
  health: () => request<HealthStatus>('GET', '/health'),
  systemInfo: () => request<SystemInfo>('GET', '/system/info'),
  startupReport: () => request<StartupCheck[]>('GET', '/system/startup-report'),
  backup: () => request<{ filename: string; size_bytes: number; created_at: string }>('POST', '/system/backup'),
  seedDemo: () => request<{ created: number; skipped: number; failed: number; label: string }>('POST', '/system/seed-demo'),
  dashboard: () => request<DashboardSummary>('GET', '/dashboard/summary'),
  analytics: () => request<AnalyticsSummary>('GET', '/analytics'),
  analyze: (tx: TransactionInput) => request<AnalysisResult>('POST', '/transactions/analyze', tx),
  transactions: (params: Params) => request<Paged<TransactionRow>>('GET', '/transactions', undefined, params),
  transaction: (id: string) => request<TransactionDetail>('GET', `/transactions/${encodeURIComponent(id)}`),
  facts: (id: string) => request<Fact[]>('GET', `/transactions/${encodeURIComponent(id)}/facts`),
  trace: (id: string) => request<TracePayload>('GET', `/transactions/${encodeURIComponent(id)}/trace`),
  rules: () => request<RulesPayload>('GET', '/rules'),
  knowledgeBase: () => request<KnowledgeBasePayload>('GET', '/knowledge-base'),
  auditLogs: (params: Params) => request<Paged<AuditEvent> & { event_types: string[] }>('GET', '/audit-logs', undefined, params),
  reports: () => request<ReportRecord[]>('GET', '/reports'),
  createReport: (transaction_id: string, format: 'json' | 'csv' | 'pdf') =>
    request<GeneratedReport>('POST', '/reports', { transaction_id, format }),
  reportDocument: (reportId: string) => request<ReportDoc>('GET', `/reports/${encodeURIComponent(reportId)}`),
  transactionReport: (id: string) => request<ReportDoc>('GET', `/transactions/${encodeURIComponent(id)}/report`),
  reportDownloadUrl: (reportId: string) => `${BASE}/reports/${encodeURIComponent(reportId)}/download`,
};
