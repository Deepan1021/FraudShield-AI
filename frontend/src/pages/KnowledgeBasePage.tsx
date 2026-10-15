import { useState, type FormEvent } from 'react';
import { Card, EmptyState, ErrorState, Loading, PageHeader, StatCard, TableWrap, Tag } from '../components/ui';
import { FactsPanel } from '../components/ResultPanels';
import { useAsync } from '../hooks/useAsync';
import { api } from '../services/api';
import type { Fact } from '../types/api';
import { KIND_STYLE } from '../utils/risk';

export function KnowledgeBasePage() {
  const kb = useAsync(() => api.knowledgeBase());
  const [tid, setTid] = useState('');
  const [facts, setFacts] = useState<Fact[] | null>(null);
  const [err, setErr] = useState<Error | null>(null);
  const [kind, setKind] = useState('');

  const inspect = async (e: FormEvent) => {
    e.preventDefault();
    setErr(null);
    try { setFacts(await api.facts(tid.trim())); } catch (x) { setErr(x as Error); setFacts(null); }
  };

  if (kb.loading && !kb.data) return <Loading label="Loading knowledge base" />;
  if (kb.error && !kb.data) return <ErrorState error={kb.error} onRetry={kb.reload} />;
  const d = kb.data!;
  const preds = d.predicates.filter((p) => !kind || p.kind === kind);

  return (
    <div className="space-y-5">
      <PageHeader title="Knowledge Base" subtitle="Predicate vocabulary, rule dependencies and inspectable facts" />
      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        <StatCard label="Status" value={d.status} />
        <StatCard label="Predicates" value={d.predicates.length} />
        <StatCard label="Active rules" value={d.rulebase.active_rule_count} hint={`of ${d.rulebase.rule_count} · v${d.rulebase.version}`} />
        <StatCard label="Rule dependencies" value={d.rule_dependencies.length} />
      </div>

      <Card title="Inspect facts for a transaction">
        <form onSubmit={inspect} className="flex flex-wrap items-end gap-3">
          <div><label htmlFor="kb-tid" className="mb-1 block text-xs font-semibold text-slate-600">Transaction ID</label><input id="kb-tid" className="input" value={tid} onChange={(e) => setTid(e.target.value)} placeholder="TXN001" /></div>
          <button className="btn-primary" type="submit" disabled={!tid.trim()}>Inspect facts</button>
        </form>
        {err && <div className="mt-3"><ErrorState error={err} /></div>}
        {facts && <div className="mt-4"><FactsPanel facts={facts} /></div>}
      </Card>

      <Card title="Predicates" pad={false} actions={
        <select aria-label="Filter predicates by kind" className="input !w-auto !py-1" value={kind} onChange={(e) => setKind(e.target.value)}><option value="">All kinds</option>{Object.keys(d.predicate_kinds).map((k) => <option key={k} value={k}>{KIND_STYLE[k]?.label ?? k} ({d.predicate_kinds[k]})</option>)}</select>}>
        <TableWrap>
          <table className="w-full text-sm" data-testid="predicates-table">
            <thead><tr><th className="th">Predicate</th><th className="th">Kind</th><th className="th">Category</th><th className="th">Meaning</th><th className="th">Used in</th><th className="th">Derived by</th></tr></thead>
            <tbody>
              {preds.map((p) => (
                <tr key={p.name}>
                  <td className="td mono font-bold">{p.name}(x)</td>
                  <td className="td"><span className="rounded border px-1.5 py-0.5 text-[11px] font-semibold" style={{ background: KIND_STYLE[p.kind]?.fill, borderColor: KIND_STYLE[p.kind]?.stroke, color: KIND_STYLE[p.kind]?.text }}>{KIND_STYLE[p.kind]?.label ?? p.kind}</span></td>
                  <td className="td">{p.category}</td><td className="td text-slate-600">{p.description}</td>
                  <td className="td text-xs">{p.used_in_rules.join(', ') || '-'}</td><td className="td text-xs">{p.derived_by_rules.join(', ') || '-'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </TableWrap>
      </Card>

      <Card title="Rule dependencies (a rule feeds another when its conclusion is used as a condition)">
        {d.rule_dependencies.length === 0 ? <EmptyState title="No dependencies" /> : (
          <ul className="grid gap-1.5 text-sm sm:grid-cols-2 xl:grid-cols-3">
            {d.rule_dependencies.map((e, i) => <li key={i} className="mono"><b>{e.from}</b> <span className="text-slate-400">→ {e.via} →</span> <b>{e.to}</b></li>)}
          </ul>
        )}
        <p className="mt-3 text-xs text-slate-500"><Tag>extension point</Tag> External signals (for example an ML anomaly score or IP reputation) can be added as new facts by a FactProvider without changing the symbolic core.</p>
      </Card>
    </div>
  );
}
