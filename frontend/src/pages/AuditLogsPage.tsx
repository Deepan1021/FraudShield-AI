import { useEffect, useState } from 'react';
import { AuditTable } from '../components/ResultPanels';
import { RiskBadge } from '../components/RiskBadge';
import { Card, ErrorState, Loading, PageHeader, Pagination } from '../components/ui';
import { useAsync, useDebounced } from '../hooks/useAsync';
import { api } from '../services/api';
import { RISK_LEVELS } from '../utils/risk';

export function AuditLogsPage() {
  const [q, setQ] = useState('');
  const [eventType, setEventType] = useState('');
  const [risk, setRisk] = useState('');
  const [from, setFrom] = useState('');
  const [to, setTo] = useState('');
  const [page, setPage] = useState(1);
  const dq = useDebounced(q);
  useEffect(() => setPage(1), [dq, eventType, risk, from, to]);
  const params = { q: dq, event_type: eventType, risk, date_from: from, date_to: to, page, page_size: 25 };
  const res = useAsync(() => api.auditLogs(params), [JSON.stringify(params)]);

  return (
    <div>
      <PageHeader title="Audit Logs" subtitle="Immutable record of analyses, decisions, reports and system events" actions={<button className="btn-secondary" onClick={res.reload}>Refresh</button>} />
      <Card className="mb-4">
        <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-5">
          <div><label htmlFor="a-q" className="mb-1 block text-xs font-semibold text-slate-600">Search</label><input id="a-q" className="input" value={q} onChange={(e) => setQ(e.target.value)} placeholder="Transaction, actor, text" /></div>
          <div><label htmlFor="a-ev" className="mb-1 block text-xs font-semibold text-slate-600">Event</label><select id="a-ev" className="input" value={eventType} onChange={(e) => setEventType(e.target.value)}><option value="">All events</option>{(res.data?.event_types ?? []).map((t) => <option key={t}>{t}</option>)}</select></div>
          <div><label htmlFor="a-risk" className="mb-1 block text-xs font-semibold text-slate-600">Risk</label><select id="a-risk" className="input" value={risk} onChange={(e) => setRisk(e.target.value)}><option value="">All</option>{RISK_LEVELS.map((r) => <option key={r}>{r}</option>)}</select></div>
          <div><label htmlFor="a-from" className="mb-1 block text-xs font-semibold text-slate-600">From</label><input id="a-from" type="date" className="input" value={from} onChange={(e) => setFrom(e.target.value)} /></div>
          <div><label htmlFor="a-to" className="mb-1 block text-xs font-semibold text-slate-600">To</label><input id="a-to" type="date" className="input" value={to} onChange={(e) => setTo(e.target.value)} /></div>
        </div>
        <div className="mt-2 flex items-center gap-2 text-xs text-slate-500">Risk legend: {RISK_LEVELS.map((r) => <RiskBadge key={r} level={r} size="sm" />)}</div>
      </Card>
      <Card pad={false}>
        {res.loading && !res.data ? <Loading /> : res.error && !res.data ? <ErrorState error={res.error} onRetry={res.reload} /> : res.data ? (
          <><AuditTable events={res.data.items} showTransaction /><Pagination page={res.data.page} pages={res.data.pages} total={res.data.total} onPage={setPage} /></>
        ) : null}
      </Card>
    </div>
  );
}
