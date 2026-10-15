import { useEffect, useState, type FormEvent } from 'react';
import { useSearchParams } from 'react-router-dom';
import { ReportViewer } from '../components/ReportViewer';
import { Card, EmptyState, ErrorState, Loading, PageHeader, TableWrap, Tag } from '../components/ui';
import { useAsync } from '../hooks/useAsync';
import { api } from '../services/api';
import type { GeneratedReport, ReportDoc } from '../types/api';
import { formatDateTime } from '../utils/format';

export function ReportsPage() {
  const [params] = useSearchParams();
  const [tid, setTid] = useState(params.get('transaction') ?? '');
  const [format, setFormat] = useState<'json' | 'csv' | 'pdf'>('pdf');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<Error | null>(null);
  const [doc, setDoc] = useState<ReportDoc | null>(null);
  const [generated, setGenerated] = useState<GeneratedReport | null>(null);
  const list = useAsync(() => api.reports());

  const view = async (id: string) => {
    setError(null); setGenerated(null);
    try { setDoc(await api.transactionReport(id.trim())); } catch (e) { setError(e as Error); setDoc(null); }
  };
  useEffect(() => { const t = params.get('transaction'); if (t) void view(t); /* eslint-disable-next-line */ }, []);

  const generate = async (e: FormEvent) => {
    e.preventDefault();
    setBusy(true); setError(null);
    try {
      const g = await api.createReport(tid.trim(), format);
      setGenerated(g); setDoc(g.report); list.reload();
    } catch (x) { setError(x as Error); } finally { setBusy(false); }
  };

  const open = async (reportId: string) => {
    setError(null); setGenerated(null);
    try { setDoc(await api.reportDocument(reportId)); } catch (e) { setError(e as Error); }
  };

  return (
    <div className="space-y-5">
      <PageHeader title="Reports" subtitle="Generate, review and export transaction risk reports" />
      <Card title="Generate a report">
        <form onSubmit={generate} className="flex flex-wrap items-end gap-3" aria-label="Generate report">
          <div><label htmlFor="rep-tid" className="mb-1 block text-xs font-semibold text-slate-600">Transaction ID</label><input id="rep-tid" className="input" value={tid} onChange={(e) => setTid(e.target.value)} placeholder="TXN001" /></div>
          <div><label htmlFor="rep-format" className="mb-1 block text-xs font-semibold text-slate-600">Export format</label>
            <select id="rep-format" className="input" value={format} onChange={(e) => setFormat(e.target.value as 'json' | 'csv' | 'pdf')}><option value="pdf">PDF</option><option value="json">JSON</option><option value="csv">CSV</option></select></div>
          <button type="submit" className="btn-primary" disabled={!tid.trim() || busy} data-testid="generate-report">{busy ? 'Generating…' : 'Generate and export'}</button>
          <button type="button" className="btn-secondary" disabled={!tid.trim()} onClick={() => view(tid)}>Preview only</button>
        </form>
        {generated && (
          <p className="mt-3 rounded bg-signal-soft px-3 py-2 text-sm" role="status" data-testid="report-generated">
            Report <b>{generated.report_id}</b> saved as <b>{generated.filename}</b> ({(generated.size_bytes / 1024).toFixed(1)} KB). <a className="font-semibold text-signal-dark underline" href={api.reportDownloadUrl(generated.report_id)}>Download {generated.format.toUpperCase()}</a>
          </p>
        )}
        {error && <div className="mt-3"><ErrorState error={error} /></div>}
      </Card>

      <div className="grid gap-5 xl:grid-cols-3">
        <Card title="Generated reports" pad={false} className="h-fit xl:col-span-1">
          {list.loading && !list.data ? <Loading /> : list.error ? <div className="p-3"><ErrorState error={list.error} onRetry={list.reload} /></div> : !list.data || list.data.length === 0 ? <div className="p-4"><EmptyState title="No reports yet" /></div> : (
            <TableWrap>
              <table className="w-full text-sm" data-testid="reports-table">
                <thead><tr><th className="th">Report</th><th className="th">Format</th><th className="th">Created</th></tr></thead>
                <tbody>
                  {list.data.map((r) => (
                    <tr key={r.report_id}>
                      <td className="td"><button className="text-left font-semibold text-signal-dark hover:underline" onClick={() => open(r.report_id)}>{r.transaction_id}</button><div className="text-xs text-slate-500">{r.report_id}</div></td>
                      <td className="td">{r.status === 'FAILED' ? <Tag tone="red" >failed</Tag> : <>{r.format.toUpperCase()} {r.status === 'COMPLETED' && <a className="ml-1 text-xs text-signal-dark underline" href={api.reportDownloadUrl(r.report_id)}>download</a>}</>}</td>
                      <td className="td text-xs text-slate-500">{formatDateTime(r.created_at)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </TableWrap>
          )}
        </Card>
        <div className="xl:col-span-2">{doc ? <ReportViewer report={doc} /> : <EmptyState title="No report open">Generate a report, open one from the list, or preview a transaction.</EmptyState>}</div>
      </div>
    </div>
  );
}
