import { HBar, RiskDistributionChart, TrendChart } from '../components/Charts';
import { Card, ErrorState, Loading, PageHeader, StatCard, TableWrap, EmptyState } from '../components/ui';
import { useAsync } from '../hooks/useAsync';
import { api } from '../services/api';
import { formatMs, humanize } from '../utils/format';
import { ACTION_LABEL, RISK_STYLE } from '../utils/risk';

export function AnalyticsPage() {
  const q = useAsync(() => api.analytics());
  if (q.loading && !q.data) return <Loading label="Loading analytics" />;
  if (q.error && !q.data) return <ErrorState error={q.error} onRetry={q.reload} />;
  const a = q.data!;
  if (a.total_evaluations === 0) return (<div><PageHeader title="Analytics" /><EmptyState title="No data to analyse yet">Analyse transactions or seed the demonstration data from the dashboard.</EmptyState></div>);
  return (
    <div className="space-y-5">
      <PageHeader title="Analytics" subtitle="All figures are computed from stored evaluations" actions={<button className="btn-secondary" onClick={q.reload}>Refresh</button>} />
      <div className="grid grid-cols-2 gap-3 lg:grid-cols-5">
        <StatCard label="Total evaluations" value={a.total_evaluations.toLocaleString()} />
        <StatCard label="High-risk share" value={`${a.high_risk_percentage}%`} hint="HIGH + CRITICAL" accent={RISK_STYLE.HIGH.color} />
        <StatCard label="Critical transactions" value={a.critical_count} accent={RISK_STYLE.CRITICAL.color} />
        <StatCard label="Avg severity index" value={a.avg_severity_index} hint="rule-based, not a probability" />
        <StatCard label="Avg evaluation time" value={formatMs(a.avg_processing_ms)} />
      </div>
      <div className="grid gap-5 xl:grid-cols-2">
        <Card title="Risk distribution"><RiskDistributionChart data={a.risk_distribution} /></Card>
        <Card title="Recommendation distribution"><HBar data={a.recommendation_distribution.map((r) => ({ name: ACTION_LABEL[r.action], count: r.count }))} nameKey="name" valueKey="count" /></Card>
      </div>
      <Card title="Daily evaluations and risk trend (last 30 days)"><TrendChart days={a.trend.days} sufficient={a.trend.sufficient} /></Card>
      <div className="grid gap-5 xl:grid-cols-2">
        <Card title="Most frequently triggered rules"><HBar data={a.top_rules.map((r) => ({ name: `${r.rule_id} ${r.rule_name}`.slice(0, 26), firings: r.firings }))} nameKey="name" valueKey="firings" color="#0E7C86" /></Card>
        <Card title="Observed security indicators"><HBar data={a.indicator_frequency.map((r) => ({ name: humanize(r.predicate.replace(/([A-Z])/g, ' $1').trim()), count: r.occurrences }))} nameKey="name" valueKey="count" color="#9F1239" /></Card>
      </div>
      <div className="grid gap-5 xl:grid-cols-3">
        <Card title="Location patterns" pad={false}>
          <TableWrap><table className="w-full text-sm"><thead><tr><th className="th">Location</th><th className="th">Transactions</th><th className="th">High / critical</th></tr></thead>
            <tbody>{a.locations.map((l) => <tr key={l.location}><td className="td">{l.location}</td><td className="td tabular-nums">{l.transactions}</td><td className="td tabular-nums">{l.high_risk}</td></tr>)}</tbody></table></TableWrap>
        </Card>
        <Card title="Device trust vs. risk" pad={false}>
          <TableWrap><table className="w-full text-sm"><thead><tr><th className="th">Device trust</th><th className="th">Transactions</th><th className="th">High / critical</th></tr></thead>
            <tbody>{a.device_anomalies.map((l) => <tr key={l.device_trust}><td className="td">{humanize(l.device_trust)}</td><td className="td tabular-nums">{l.transactions}</td><td className="td tabular-nums">{l.high_risk}</td></tr>)}</tbody></table></TableWrap>
        </Card>
        <Card title="Behavioural anomalies (vs. baseline)" pad={false}>
          <TableWrap><table className="w-full text-sm"><thead><tr><th className="th">Anomaly</th><th className="th">Occurrences</th></tr></thead>
            <tbody>{a.behavioural_anomalies.map((l) => <tr key={l.predicate}><td className="td mono">{l.predicate}</td><td className="td tabular-nums">{l.occurrences}</td></tr>)}</tbody></table></TableWrap>
        </Card>
      </div>
    </div>
  );
}
