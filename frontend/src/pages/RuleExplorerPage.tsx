import { useMemo, useState } from 'react';
import { Card, ErrorState, Loading, PageHeader, TableWrap, Tag } from '../components/ui';
import { RiskBadge } from '../components/RiskBadge';
import { useAsync } from '../hooks/useAsync';
import { api } from '../services/api';
import type { RuleDef } from '../types/api';

export function RuleExplorerPage() {
  const q = useAsync(() => api.rules());
  const [search, setSearch] = useState('');
  const [category, setCategory] = useState('');
  const [severity, setSeverity] = useState('');
  const [selected, setSelected] = useState<string | null>(null);

  const rules = q.data?.rules ?? [];
  const categories = useMemo(() => Array.from(new Set(rules.map((r) => r.category))).sort(), [rules]);
  const shown = rules.filter((r) =>
    (!category || r.category === category) && (!severity || r.severity === severity) &&
    (!search || `${r.id} ${r.name} ${r.description} ${r.formula}`.toLowerCase().includes(search.toLowerCase())));
  const sel: RuleDef | undefined = rules.find((r) => r.id === selected);
  const deps = q.data?.dependencies ?? [];

  if (q.loading && !q.data) return <Loading label="Loading rule base" />;
  if (q.error && !q.data) return <ErrorState error={q.error} onRetry={q.reload} />;

  return (
    <div>
      <PageHeader title="Rule Explorer" subtitle={q.data ? `${q.data.name} · version ${q.data.version} · ${rules.filter((r) => r.status === 'ACTIVE').length} active rules (read-only)` : ''} />
      <Card className="mb-4">
        <div className="grid gap-3 md:grid-cols-3">
          <div><label htmlFor="r-search" className="mb-1 block text-xs font-semibold text-slate-600">Search rules</label><input id="r-search" className="input" value={search} onChange={(e) => setSearch(e.target.value)} placeholder="R30, device, HighRisk…" /></div>
          <div><label htmlFor="r-cat" className="mb-1 block text-xs font-semibold text-slate-600">Category</label><select id="r-cat" className="input" value={category} onChange={(e) => setCategory(e.target.value)}><option value="">All categories</option>{categories.map((c) => <option key={c}>{c}</option>)}</select></div>
          <div><label htmlFor="r-sev" className="mb-1 block text-xs font-semibold text-slate-600">Severity</label><select id="r-sev" className="input" value={severity} onChange={(e) => setSeverity(e.target.value)}><option value="">All</option>{['LOW', 'MEDIUM', 'HIGH', 'CRITICAL'].map((s) => <option key={s}>{s}</option>)}</select></div>
        </div>
      </Card>
      <div className="grid gap-5 xl:grid-cols-3">
        <Card pad={false} className="xl:col-span-2">
          <TableWrap>
            <table className="w-full text-sm" data-testid="rules-table">
              <thead><tr><th className="th">ID</th><th className="th">Name</th><th className="th">Category</th><th className="th">Prio</th><th className="th">Severity</th><th className="th">Status</th></tr></thead>
              <tbody>
                {shown.map((r) => (
                  <tr key={r.id} className={`cursor-pointer hover:bg-slate-50 ${selected === r.id ? 'bg-signal-soft' : ''}`} onClick={() => setSelected(r.id)} tabIndex={0}
                    onKeyDown={(e) => e.key === 'Enter' && setSelected(r.id)} aria-selected={selected === r.id}>
                    <td className="td font-bold">{r.id}</td><td className="td">{r.name}</td><td className="td">{r.category}</td>
                    <td className="td tabular-nums">{r.priority}</td><td className="td"><RiskBadge level={r.severity} size="sm" /></td>
                    <td className="td"><Tag tone={r.status === 'ACTIVE' ? 'teal' : 'slate'}>{r.status}</Tag></td>
                  </tr>
                ))}
                {shown.length === 0 && <tr><td className="td text-slate-500" colSpan={6}>No rules match the filters.</td></tr>}
              </tbody>
            </table>
          </TableWrap>
        </Card>
        <div className="space-y-5">
          <Card title={sel ? `Rule ${sel.id}` : 'Rule detail'}>
            {!sel ? <p className="text-sm text-slate-500">Select a rule to see its logic, rationale and dependencies.</p> : (
              <div className="space-y-3 text-sm" data-testid="rule-detail">
                <div className="text-base font-bold">{sel.name}</div>
                <div>
                  <div className="card-title">IF</div>
                  <ul className="mono mt-1 space-y-0.5">{sel.antecedents.map((a, i) => <li key={a}>{i > 0 && sel.min_matches === null ? 'AND ' : ''}{a}</li>)}</ul>
                  {sel.min_matches !== null && <p className="mt-1 text-xs text-slate-500">At least {sel.min_matches} of the {sel.antecedents.length} conditions must hold.</p>}
                  <div className="card-title mt-2">THEN</div>
                  <div className="mono mt-1 font-bold">{sel.consequent}</div>
                </div>
                <p>{sel.description}</p>
                <p className="text-slate-600"><b>Explanation shown to analysts:</b> {sel.explanation}</p>
                <div className="flex flex-wrap gap-1.5">{sel.tags.map((t) => <Tag key={t}>{t}</Tag>)}</div>
                <dl className="grid grid-cols-2 gap-1 text-xs text-slate-600"><dt>Version</dt><dd className="font-semibold">{sel.version}</dd><dt>Source</dt><dd className="font-semibold">{sel.source}</dd><dt>Priority</dt><dd className="font-semibold">{sel.priority}</dd></dl>
                <div><div className="card-title">Dependencies</div>
                  <p className="text-xs">Feeds: {deps.filter((d) => d.from === sel.id).map((d) => d.to).join(', ') || '-'}</p>
                  <p className="text-xs">Fed by: {deps.filter((d) => d.to === sel.id).map((d) => d.from).join(', ') || '-'}</p></div>
              </div>
            )}
          </Card>
          <Card title="Conflict-resolution strategy"><ol className="list-decimal pl-5 text-sm">{(q.data?.conflict_resolution ?? []).map((s) => <li key={s}>{s.replace(/^\d+\.\s*/, '')}</li>)}</ol></Card>
        </div>
      </div>
    </div>
  );
}
