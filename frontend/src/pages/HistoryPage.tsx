import { useEffect, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { RiskBadge } from '../components/RiskBadge';
import { Card, EmptyState, ErrorState, Loading, PageHeader, Pagination, TableWrap, Tag } from '../components/ui';
import { useAsync, useDebounced } from '../hooks/useAsync';
import { api } from '../services/api';
import type { RiskLevel } from '../types/api';
import { formatAmount, formatDateTime } from '../utils/format';
import { ACTION_LABEL, RISK_LEVELS, STATUS_LABEL } from '../utils/risk';

export const PAGE_SIZE_KEY = 'fs.pageSize';
const SORTS = [['submitted_at', 'Date'], ['amount', 'Amount'], ['risk_rank', 'Risk level'], ['severity_index', 'Severity index'], ['transaction_id', 'Transaction ID'], ['user_id', 'User ID']];

export function HistoryPage() {
  const nav = useNavigate();
  const [q, setQ] = useState('');
  const [risk, setRisk] = useState<RiskLevel[]>([]);
  const [recommendation, setRecommendation] = useState('');
  const [deviceTrust, setDeviceTrust] = useState('');
  const [location, setLocation] = useState('');
  const [rule, setRule] = useState('');
  const [status, setStatus] = useState('');
  const [dateFrom, setDateFrom] = useState('');
  const [dateTo, setDateTo] = useState('');
  const [sort, setSort] = useState('submitted_at');
  const [order, setOrder] = useState<'asc' | 'desc'>('desc');
  const [page, setPage] = useState(1);
  const pageSize = Number(localStorage.getItem(PAGE_SIZE_KEY)) || 20;

  const dq = useDebounced(q);
  const dl = useDebounced(location);
  const dr = useDebounced(rule);
  const params = { q: dq, risk, recommendation, device_trust: deviceTrust, location: dl, rule: /^R\d{2,3}$/i.test(dr) ? dr.toUpperCase() : '', status, date_from: dateFrom, date_to: dateTo, sort, order, page, page_size: pageSize };
  const key = JSON.stringify(params);
  useEffect(() => setPage(1), [dq, risk.join(), recommendation, deviceTrust, dl, dr, status, dateFrom, dateTo, sort, order]);
  const res = useAsync(() => api.transactions(params), [key]);

  const toggleRisk = (r: RiskLevel) => setRisk((s) => (s.includes(r) ? s.filter((x) => x !== r) : [...s, r]));
  const clear = () => { setQ(''); setRisk([]); setRecommendation(''); setDeviceTrust(''); setLocation(''); setRule(''); setStatus(''); setDateFrom(''); setDateTo(''); };

  return (
    <div>
      <PageHeader title="Transaction History" subtitle="Search, filter and open any analysed transaction" />
      <Card className="mb-4">
        <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
          <div><label htmlFor="f-q" className="mb-1 block text-xs font-semibold text-slate-600">Transaction or user ID</label>
            <input id="f-q" className="input" value={q} onChange={(e) => setQ(e.target.value)} placeholder="TXN001 or USER001" /></div>
          <div><label htmlFor="f-loc" className="mb-1 block text-xs font-semibold text-slate-600">Location</label>
            <input id="f-loc" className="input" value={location} onChange={(e) => setLocation(e.target.value)} placeholder="Delhi" /></div>
          <div><label htmlFor="f-rec" className="mb-1 block text-xs font-semibold text-slate-600">Recommendation</label>
            <select id="f-rec" className="input" value={recommendation} onChange={(e) => setRecommendation(e.target.value)}><option value="">All</option>{Object.entries(ACTION_LABEL).map(([k, v]) => <option key={k} value={k}>{v}</option>)}</select></div>
          <div><label htmlFor="f-dev" className="mb-1 block text-xs font-semibold text-slate-600">Device trust</label>
            <select id="f-dev" className="input" value={deviceTrust} onChange={(e) => setDeviceTrust(e.target.value)}><option value="">All</option>{['TRUSTED', 'KNOWN', 'UNTRUSTED', 'UNKNOWN'].map((o) => <option key={o} value={o}>{o.charAt(0) + o.slice(1).toLowerCase()}</option>)}</select></div>
          <div><label htmlFor="f-rule" className="mb-1 block text-xs font-semibold text-slate-600">Rule fired</label>
            <input id="f-rule" className="input" value={rule} onChange={(e) => setRule(e.target.value)} placeholder="R30" /></div>
          <div><label htmlFor="f-status" className="mb-1 block text-xs font-semibold text-slate-600">Decision status</label>
            <select id="f-status" className="input" value={status} onChange={(e) => setStatus(e.target.value)}><option value="">All</option>{Object.entries(STATUS_LABEL).map(([k, v]) => <option key={k} value={k}>{v}</option>)}</select></div>
          <div><label htmlFor="f-from" className="mb-1 block text-xs font-semibold text-slate-600">From date</label>
            <input id="f-from" type="date" className="input" value={dateFrom} onChange={(e) => setDateFrom(e.target.value)} /></div>
          <div><label htmlFor="f-to" className="mb-1 block text-xs font-semibold text-slate-600">To date</label>
            <input id="f-to" type="date" className="input" value={dateTo} onChange={(e) => setDateTo(e.target.value)} /></div>
        </div>
        <div className="mt-3 flex flex-wrap items-center gap-3">
          <fieldset className="flex items-center gap-2"><legend className="sr-only">Risk level</legend>
            {RISK_LEVELS.map((r) => (
              <button key={r} type="button" aria-pressed={risk.includes(r)} onClick={() => toggleRisk(r)} data-testid={`filter-${r}`}
                className={`rounded-full ${risk.includes(r) ? 'ring-2 ring-signal ring-offset-1' : 'opacity-70 hover:opacity-100'}`}><RiskBadge level={r} size="sm" /></button>
            ))}
          </fieldset>
          <div className="ml-auto flex items-center gap-2">
            <label htmlFor="f-sort" className="text-xs font-semibold text-slate-600">Sort by</label>
            <select id="f-sort" className="input !w-auto" value={sort} onChange={(e) => setSort(e.target.value)}>{SORTS.map(([k, v]) => <option key={k} value={k}>{v}</option>)}</select>
            <button className="btn-secondary" onClick={() => setOrder(order === 'asc' ? 'desc' : 'asc')} aria-label={`Sort order: ${order === 'asc' ? 'ascending' : 'descending'}`}>{order === 'asc' ? '↑ Ascending' : '↓ Descending'}</button>
            <button className="btn-secondary" onClick={clear}>Clear filters</button>
          </div>
        </div>
      </Card>

      <Card pad={false}>
        {res.loading && !res.data ? <Loading label="Searching" /> : res.error && !res.data ? <ErrorState error={res.error} onRetry={res.reload} /> : res.data && res.data.items.length === 0 ? (
          <div className="p-4"><EmptyState title="No transactions match these filters">Adjust or clear the filters.</EmptyState></div>
        ) : res.data ? (
          <>
            <TableWrap>
              <table className="w-full text-sm" data-testid="history-table">
                <thead><tr><th className="th">Transaction</th><th className="th">User</th><th className="th">Amount</th><th className="th">Location</th><th className="th">Device</th><th className="th">Risk</th><th className="th">Recommendation</th><th className="th">Index</th><th className="th">Date</th></tr></thead>
                <tbody>
                  {res.data.items.map((t) => (
                    <tr key={t.transaction_id} className="cursor-pointer hover:bg-slate-50" onClick={() => nav(`/transactions/${t.transaction_id}`)}>
                      <td className="td"><Link className="font-bold text-signal-dark hover:underline" to={`/transactions/${t.transaction_id}`} onClick={(e) => e.stopPropagation()}>{t.transaction_id}</Link>{t.is_synthetic ? <> <Tag tone="amber">synthetic</Tag></> : null}</td>
                      <td className="td">{t.user_id}</td>
                      <td className="td tabular-nums">{formatAmount(t.amount, t.currency)}</td>
                      <td className="td">{t.location}</td>
                      <td className="td">{t.device_trust.charAt(0) + t.device_trust.slice(1).toLowerCase()}</td>
                      <td className="td"><RiskBadge level={t.risk_level} size="sm" /></td>
                      <td className="td">{t.recommendation_action ? ACTION_LABEL[t.recommendation_action] : '-'}</td>
                      <td className="td tabular-nums">{t.severity_index ?? '-'}</td>
                      <td className="td whitespace-nowrap text-xs text-slate-500">{formatDateTime(t.submitted_at)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </TableWrap>
            <Pagination page={res.data.page} pages={res.data.pages} total={res.data.total} onPage={setPage} />
          </>
        ) : null}
      </Card>
    </div>
  );
}
