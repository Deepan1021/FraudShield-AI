import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { RiskDistributionChart, TrendChart } from '../components/Charts';
import { RiskBadge } from '../components/RiskBadge';
import { Card, EmptyState, ErrorState, Loading, PageHeader, StatCard, Tag, TableWrap } from '../components/ui';
import { useAsync } from '../hooks/useAsync';
import { api } from '../services/api';
import type { RecentEvent } from '../types/api';
import { formatAmount, formatDateTime, formatMs } from '../utils/format';
import { RISK_STYLE } from '../utils/risk';

function EventsTable({ events, empty }: { events: RecentEvent[]; empty: string }) {
  const nav = useNavigate();
  if (!events.length) return <EmptyState title={empty} />;
  return (
    <TableWrap>
      <table className="w-full text-sm">
        <thead><tr><th className="th">Transaction</th><th className="th">Risk</th><th className="th">Amount</th><th className="th">Primary indicators</th><th className="th">Time</th></tr></thead>
        <tbody>
          {events.map((e) => (
            <tr key={e.transaction_id} className="cursor-pointer hover:bg-slate-50" onClick={() => nav(`/transactions/${e.transaction_id}`)}>
              <td className="td"><Link className="font-bold text-signal-dark hover:underline" to={`/transactions/${e.transaction_id}`} onClick={(ev) => ev.stopPropagation()}>{e.transaction_id}</Link><div className="text-xs text-slate-500">{e.user_id} · {e.location}</div></td>
              <td className="td"><RiskBadge level={e.risk_level} size="sm" /></td>
              <td className="td tabular-nums">{formatAmount(e.amount, e.currency)}</td>
              <td className="td text-slate-600">{e.summary ?? '-'}</td>
              <td className="td whitespace-nowrap text-xs text-slate-500">{formatDateTime(e.submitted_at)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </TableWrap>
  );
}

export function DashboardPage() {
  const dash = useAsync(() => api.dashboard());
  const health = useAsync(() => api.health());
  const [seeding, setSeeding] = useState(false);
  const [seedError, setSeedError] = useState<Error | null>(null);

  const seed = async () => {
    setSeeding(true);
    setSeedError(null);
    try {
      await api.seedDemo();
      dash.reload();
    } catch (e) {
      setSeedError(e as Error);
    } finally {
      setSeeding(false);
    }
  };

  if (dash.loading && !dash.data) return <Loading label="Loading dashboard" />;
  if (dash.error && !dash.data) return <ErrorState error={dash.error} onRetry={dash.reload} />;
  const d = dash.data!;

  return (
    <div>
      <PageHeader
        title="Risk Intelligence Dashboard"
        subtitle={d.synthetic_transactions > 0 ? <span><Tag tone="amber">Synthetic Demonstration Data</Tag> {d.synthetic_transactions} of {d.total_transactions} evaluations are synthetic.</span> : 'Live view of evaluated transactions'}
        actions={<><button className="btn-secondary" onClick={dash.reload}>Refresh</button><Link className="btn-primary" to="/analyze">Analyze transaction</Link></>}
      />
      {seedError && <div className="mb-4"><ErrorState error={seedError} /></div>}
      {d.total_transactions === 0 && (
        <div className="card mb-5 flex flex-wrap items-center justify-between gap-3 p-5">
          <div>
            <div className="font-semibold">No transactions have been evaluated yet</div>
            <p className="text-sm text-slate-500">Analyze a transaction, or load the optional synthetic demonstration data set (classified by the rule engine at load time).</p>
          </div>
          <button className="btn-secondary" onClick={seed} disabled={seeding}>{seeding ? 'Loading…' : 'Seed demo data'}</button>
        </div>
      )}

      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4 xl:grid-cols-7">
        <StatCard label="Transactions evaluated" value={d.total_transactions.toLocaleString()} />
        <StatCard label="Critical alerts" value={d.critical} accent={RISK_STYLE.CRITICAL.color} />
        <StatCard label="High-risk alerts" value={d.high} accent={RISK_STYLE.HIGH.color} />
        <StatCard label="Medium-risk alerts" value={d.medium} accent={RISK_STYLE.MEDIUM.color} />
        <StatCard label="Low-risk transactions" value={d.low} accent={RISK_STYLE.LOW.color} />
        <StatCard label="Blocked / flagged" value={d.blocked_or_flagged} hint={`${d.high_risk_percentage}% high or critical`} accent="#1B3150" />
        <StatCard label="Avg evaluation time" value={formatMs(d.avg_processing_ms)} accent="#1B3150" />
      </div>

      <div className="mt-5 grid gap-5 xl:grid-cols-3">
        <Card title="Risk distribution" className="xl:col-span-1"><RiskDistributionChart data={d.risk_distribution} /></Card>
        <Card title="Evaluations per day (last 14 days)" className="xl:col-span-2"><TrendChart days={d.trend.days} sufficient={d.trend.sufficient} /></Card>
      </div>

      <div className="mt-5 grid gap-5 xl:grid-cols-3">
        <Card title="Recent critical and high-risk alerts" className="xl:col-span-2" pad={false}><EventsTable events={d.recent_alerts} empty="No high-risk alerts" /></Card>
        <div className="space-y-5">
          <Card title="System status">
            {health.data ? (
              <dl className="space-y-1.5 text-sm" data-testid="system-status">
                {([['API', health.data.api], ['Database', health.data.database], ['Rule engine', health.data.rule_engine], ['Knowledge base', health.data.knowledge_base]] as const).map(([k, v]) => (
                  <div key={k} className="flex justify-between"><dt className="text-slate-500">{k}</dt><dd className="font-bold">{v}</dd></div>
                ))}
                <div className="flex justify-between"><dt className="text-slate-500">Active rules</dt><dd className="font-bold">{health.data.active_rules}</dd></div>
                <div className="flex justify-between"><dt className="text-slate-500">Rule base</dt><dd className="font-bold">v{health.data.versions.rulebase}</dd></div>
              </dl>
            ) : health.error ? <ErrorState error={health.error} /> : <Loading />}
          </Card>
          <Card title="Top triggered rules">
            {d.top_rules.length === 0 ? <EmptyState title="No rule activity yet" /> : (
              <ol className="space-y-1.5 text-sm">
                {d.top_rules.map((r) => (
                  <li key={r.rule_id} className="flex justify-between gap-3"><span><b>{r.rule_id}</b> <span className="text-slate-600">{r.rule_name}</span></span><span className="tabular-nums font-semibold">{r.firings}</span></li>
                ))}
              </ol>
            )}
          </Card>
        </div>
      </div>

      <Card title="Recent analyses" className="mt-5" pad={false}><EventsTable events={d.recent_analyses} empty="No analyses yet" /></Card>
    </div>
  );
}
