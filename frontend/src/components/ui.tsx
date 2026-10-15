import type { ReactNode } from 'react';
import type { ApiError } from '../services/api';

export function Card({ title, actions, children, className = '', pad = true }: { title?: ReactNode; actions?: ReactNode; children: ReactNode; className?: string; pad?: boolean }) {
  return (
    <section className={`card ${className}`}>
      {(title || actions) && (
        <header className="flex items-center justify-between gap-3 px-4 pt-3.5 pb-2">
          <h2 className="card-title">{title}</h2>
          {actions}
        </header>
      )}
      <div className={pad ? 'px-4 pb-4 pt-1' : ''}>{children}</div>
    </section>
  );
}

export function StatCard({ label, value, hint, accent }: { label: string; value: ReactNode; hint?: ReactNode; accent?: string }) {
  return (
    <div className="card px-4 py-3.5 relative overflow-hidden" data-testid={`stat-${label.toLowerCase().replace(/[^a-z0-9]+/g, '-')}`}>
      <span className="absolute left-0 top-0 h-full w-1" style={{ background: accent ?? '#0E7C86' }} aria-hidden="true" />
      <div className="card-title">{label}</div>
      <div className="mt-1 text-2xl font-bold tabular-nums">{value}</div>
      {hint && <div className="mt-0.5 text-xs text-slate-500">{hint}</div>}
    </div>
  );
}

export function PageHeader({ title, subtitle, actions }: { title: string; subtitle?: ReactNode; actions?: ReactNode }) {
  return (
    <div className="mb-5 flex flex-wrap items-end justify-between gap-3">
      <div>
        <h1 className="text-xl font-bold tracking-tight">{title}</h1>
        {subtitle && <p className="mt-0.5 text-sm text-slate-500">{subtitle}</p>}
      </div>
      {actions && <div className="flex flex-wrap items-center gap-2">{actions}</div>}
    </div>
  );
}

export function Loading({ label = 'Loading' }: { label?: string }) {
  return (
    <div role="status" aria-live="polite" className="flex items-center gap-3 px-4 py-8 text-slate-500">
      <span className="h-4 w-4 animate-spin rounded-full border-2 border-slate-300 border-t-signal" aria-hidden="true" />
      {label}...
    </div>
  );
}

export function ErrorState({ error, onRetry }: { error: ApiError | Error; onRetry?: () => void }) {
  const code = (error as ApiError).code;
  return (
    <div role="alert" className="rounded-lg border border-risk-critical/30 bg-[#FBE4EA] px-4 py-3 text-sm text-[#7A0E2C]">
      <div className="font-semibold">{code ? `${code}: ` : ''}{error.message}</div>
      {onRetry && (
        <button className="btn-secondary mt-2" onClick={onRetry}>
          Retry
        </button>
      )}
    </div>
  );
}

export function EmptyState({ title, children }: { title: string; children?: ReactNode }) {
  return (
    <div className="rounded-lg border border-dashed border-slate-300 bg-slate-50 px-4 py-8 text-center">
      <div className="font-semibold text-slate-700">{title}</div>
      {children && <div className="mt-1 text-sm text-slate-500">{children}</div>}
    </div>
  );
}

export function Pagination({ page, pages, total, onPage }: { page: number; pages: number; total: number; onPage: (p: number) => void }) {
  return (
    <nav aria-label="Pagination" className="flex items-center justify-between gap-3 border-t border-line px-3 py-2 text-sm">
      <span className="text-slate-500">{total.toLocaleString()} result{total === 1 ? '' : 's'}</span>
      <div className="flex items-center gap-2">
        <button className="btn-secondary !py-1" disabled={page <= 1} onClick={() => onPage(page - 1)}>
          Previous
        </button>
        <span className="tabular-nums" aria-live="polite">Page {page} of {pages}</span>
        <button className="btn-secondary !py-1" disabled={page >= pages} onClick={() => onPage(page + 1)}>
          Next
        </button>
      </div>
    </nav>
  );
}

export function Field({ label, htmlFor, error, hint, children }: { label: string; htmlFor: string; error?: string; hint?: string; children: ReactNode }) {
  return (
    <div>
      <label htmlFor={htmlFor} className="mb-1 block text-xs font-semibold text-slate-600">{label}</label>
      {children}
      {hint && !error && <p className="mt-1 text-xs text-slate-500">{hint}</p>}
      {error && <p id={`${htmlFor}-error`} role="alert" className="mt-1 text-xs font-medium text-risk-critical">{error}</p>}
    </div>
  );
}

export function Tag({ children, tone = 'slate' }: { children: ReactNode; tone?: 'slate' | 'teal' | 'amber' | 'red' }) {
  const tones = { slate: 'bg-slate-100 text-slate-700', teal: 'bg-signal-soft text-signal-dark', amber: 'bg-[#FDF1DC] text-[#7A4A06]', red: 'bg-[#FBE4EA] text-[#7A0E2C]' };
  return <span className={`inline-block rounded px-1.5 py-0.5 text-[11px] font-semibold ${tones[tone]}`}>{children}</span>;
}

export function TableWrap({ children }: { children: ReactNode }) {
  return <div className="overflow-x-auto">{children}</div>;
}

export function Meter({ value, max = 100, label }: { value: number; max?: number; label: string }) {
  const pct = Math.max(0, Math.min(100, (value / max) * 100));
  return (
    <div>
      <div className="flex items-baseline justify-between text-xs">
        <span className="font-semibold text-slate-600">{label}</span>
        <span className="tabular-nums font-bold">{value} / {max}</span>
      </div>
      <div className="mt-1 h-2.5 w-full overflow-hidden rounded-full bg-slate-200" role="meter" aria-label={label} aria-valuenow={value} aria-valuemin={0} aria-valuemax={max}>
        <div className="h-full rounded-full bg-ink-700" style={{ width: `${pct}%` }} />
      </div>
    </div>
  );
}
