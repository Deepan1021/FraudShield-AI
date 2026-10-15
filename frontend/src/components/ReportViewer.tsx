import type { ReportDoc, ReportSection } from '../types/api';
import { cellText } from '../utils/format';
import { RiskBadge } from './RiskBadge';
import { TableWrap } from './ui';

function Section({ s }: { s: ReportSection }) {
  return (
    <section className="mb-5 break-inside-avoid">
      <h3 className="mb-1.5 border-b border-line pb-1 text-sm font-bold text-ink-700">{s.title}</h3>
      {s.type === 'text' && <p className="leading-relaxed">{s.data as string}</p>}
      {s.type === 'list' && <ul className="list-disc space-y-0.5 pl-5">{(s.data as string[]).map((i, n) => <li key={n}>{i}</li>)}</ul>}
      {s.type === 'kv' && (
        <dl className="grid gap-x-6 sm:grid-cols-[220px_1fr]">
          {(s.data as [string, unknown][]).map(([k, v]) => (
            <div key={k} className="contents"><dt className="border-b border-slate-100 py-1 text-slate-500">{k}</dt><dd className="border-b border-slate-100 py-1 font-medium break-words">{cellText(v)}</dd></div>
          ))}
        </dl>
      )}
      {s.type === 'table' && (() => {
        const t = s.data as { columns: string[]; rows: unknown[][] };
        return (
          <TableWrap>
            <table className="w-full text-[13px]">
              <thead><tr>{t.columns.map((c) => <th key={c} className="th">{c}</th>)}</tr></thead>
              <tbody>{t.rows.map((r, i) => <tr key={i}>{r.map((c, j) => <td key={j} className="td">{cellText(c)}</td>)}</tr>)}</tbody>
            </table>
          </TableWrap>
        );
      })()}
    </section>
  );
}

/** In-app report viewer: renders the same document that is exported to JSON, CSV and PDF. */
export function ReportViewer({ report }: { report: ReportDoc }) {
  return (
    <article className="card p-6" data-testid="report-viewer" aria-label="Report">
      <header className="mb-5 flex flex-wrap items-start justify-between gap-3 border-b-2 border-ink pb-3">
        <div>
          <h2 className="text-lg font-extrabold">{report.title}</h2>
          <p className="text-xs text-slate-500">Report {report.report_id} · generated {report.generated_at}</p>
        </div>
        <RiskBadge level={report.risk_level} size="lg" />
      </header>
      {report.sections.map((s) => <Section key={s.key} s={s} />)}
    </article>
  );
}
