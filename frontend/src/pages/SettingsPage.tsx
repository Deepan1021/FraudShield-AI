import { useState } from 'react';
import { Card, ErrorState, Loading, PageHeader, TableWrap, Tag } from '../components/ui';
import { useAsync } from '../hooks/useAsync';
import { api } from '../services/api';
import { cellText, formatUptime } from '../utils/format';
import { PAGE_SIZE_KEY } from './HistoryPage';

export function SettingsPage() {
  const info = useAsync(() => api.systemInfo());
  const startup = useAsync(() => api.startupReport());
  const health = useAsync(() => api.health());
  const [msg, setMsg] = useState<{ ok: boolean; text: string } | null>(null);
  const [busy, setBusy] = useState('');
  const [pageSize, setPageSize] = useState(Number(localStorage.getItem(PAGE_SIZE_KEY)) || 20);
  const [confirmSeed, setConfirmSeed] = useState(false);

  const run = async (name: string, fn: () => Promise<string>) => {
    setBusy(name); setMsg(null);
    try { setMsg({ ok: true, text: await fn() }); info.reload(); health.reload(); } catch (e) { setMsg({ ok: false, text: (e as Error).message }); } finally { setBusy(''); }
  };

  if (info.loading && !info.data) return <Loading />;
  if (info.error && !info.data) return <ErrorState error={info.error} onRetry={info.reload} />;
  const i = info.data!;

  return (
    <div className="space-y-5">
      <PageHeader title="System Settings" subtitle="Status, safe configuration and maintenance (configuration is read-only; change it through environment variables)" />
      {msg && <div role={msg.ok ? 'status' : 'alert'} className={`rounded-lg border px-4 py-3 text-sm ${msg.ok ? 'border-signal/30 bg-signal-soft' : 'border-risk-critical/30 bg-[#FBE4EA] text-[#7A0E2C]'}`} data-testid="settings-message">{msg.text}</div>}
      <div className="grid gap-5 xl:grid-cols-2">
        <Card title="Versions and status">
          <dl className="space-y-1.5 text-sm">
            {[['Application', i.versions.application], ['Inference engine', i.versions.engine], ['Rule base', `${i.rulebase.name} v${i.versions.rulebase}`], ['Database schema', `v${i.versions.schema} (expected v${i.versions.schema_expected})`],
              ['Environment', health.data?.environment ?? '-'], ['Uptime', health.data ? formatUptime(health.data.uptime_seconds) : '-'], ['Stored transactions', `${i.transaction_count} (${i.synthetic_count} synthetic)`]].map(([k, v]) => (
              <div key={k} className="flex justify-between border-b border-slate-100 pb-1"><dt className="text-slate-500">{k}</dt><dd className="font-semibold">{v}</dd></div>
            ))}
          </dl>
        </Card>
        <Card title="Startup validation">
          {startup.data ? <ul className="space-y-1.5 text-sm" data-testid="startup-checks">{startup.data.map((c) => <li key={c.name} className="flex items-start gap-2"><Tag tone={c.status === 'PASS' ? 'teal' : c.status === 'WARN' ? 'amber' : 'red'}>{c.status === 'PASS' ? '● PASS' : c.status === 'WARN' ? '▲ WARN' : '✘ FAIL'}</Tag><span><b>{c.name}</b> <span className="text-slate-500">{c.detail}</span></span></li>)}</ul> : startup.error ? <ErrorState error={startup.error} /> : <Loading />}
        </Card>
      </div>

      <div className="grid gap-5 xl:grid-cols-2">
        <Card title="Maintenance">
          <div className="space-y-4 text-sm">
            <div><button className="btn-secondary" disabled={!!busy} onClick={() => run('backup', async () => { const b = await api.backup(); return `Snapshot saved as ${b.filename} (${(b.size_bytes / 1024).toFixed(0)} KB) in the backups folder. Existing backups are never overwritten.`; })}>{busy === 'backup' ? 'Writing snapshot…' : 'Export database snapshot'}</button></div>
            <div>
              {!confirmSeed ? <button className="btn-secondary" disabled={!!busy} onClick={() => setConfirmSeed(true)}>Seed demo data…</button> : (
                <div className="rounded border border-line bg-slate-50 p-3">
                  <p>This adds a labelled <b>synthetic demonstration data set</b> (about 74 transactions) classified by the rule engine. Existing transactions are kept; duplicates are skipped.</p>
                  <div className="mt-2 flex gap-2"><button className="btn-primary" disabled={!!busy} onClick={() => { setConfirmSeed(false); void run('seed', async () => { const r = await api.seedDemo(); return `Synthetic demonstration data: ${r.created} created, ${r.skipped} already present, ${r.failed} failed.`; }); }}>Confirm</button><button className="btn-secondary" onClick={() => setConfirmSeed(false)}>Cancel</button></div>
                </div>
              )}
            </div>
          </div>
        </Card>
        <Card title="Display preferences (stored in this browser)">
          <label htmlFor="pageSize" className="mb-1 block text-xs font-semibold text-slate-600">Rows per page in Transaction History</label>
          <select id="pageSize" className="input !w-auto" value={pageSize} onChange={(e) => { const n = Number(e.target.value); setPageSize(n); localStorage.setItem(PAGE_SIZE_KEY, String(n)); }}>{[10, 20, 50, 100].map((n) => <option key={n}>{n}</option>)}</select>
        </Card>
      </div>

      <div className="grid gap-5 xl:grid-cols-2">
        <Card title="Runtime configuration (read-only)" pad={false}>
          <TableWrap><table className="w-full text-sm"><tbody>{Object.entries(i.config).map(([k, v]) => <tr key={k}><td className="td mono font-semibold">{k}</td><td className="td">{cellText(v)}</td></tr>)}</tbody></table></TableWrap>
        </Card>
        <Card title="Inference thresholds (read-only)" pad={false}>
          <TableWrap><table className="w-full text-sm"><tbody>{Object.entries(i.thresholds).map(([k, v]) => <tr key={k}><td className="td mono font-semibold">{k}</td><td className="td tabular-nums">{v}</td></tr>)}</tbody></table></TableWrap>
        </Card>
      </div>
    </div>
  );
}
