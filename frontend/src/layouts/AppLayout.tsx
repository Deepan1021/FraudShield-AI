import { useEffect, useState } from 'react';
import { NavLink, Outlet, useLocation } from 'react-router-dom';
import { Icon } from '../components/Icon';
import { api } from '../services/api';
import type { HealthStatus } from '../types/api';

const NAV = [
  { to: '/', label: 'Dashboard', icon: 'dashboard', end: true },
  { to: '/analyze', label: 'Transaction Analysis', icon: 'analyze' },
  { to: '/history', label: 'Transaction History', icon: 'history' },
  { to: '/analytics', label: 'Analytics', icon: 'analytics' },
  { to: '/rules', label: 'Rule Explorer', icon: 'rules' },
  { to: '/knowledge-base', label: 'Knowledge Base', icon: 'kb' },
  { to: '/reports', label: 'Reports', icon: 'reports' },
  { to: '/audit', label: 'Audit Logs', icon: 'audit' },
  { to: '/settings', label: 'System Settings', icon: 'settings' },
  { to: '/about', label: 'About', icon: 'about' },
];

function StatusChip({ label, value, ok }: { label: string; value: string; ok: boolean }) {
  return (
    <span className="inline-flex items-center gap-1.5 rounded-full border border-white/10 bg-white/5 px-2.5 py-1 text-[11px] font-semibold text-slate-200" title={`${label}: ${value}`}>
      <span className={`inline-block h-2 w-2 ${ok ? 'rounded-full bg-emerald-400' : 'rotate-45 bg-red-400'}`} aria-hidden="true" />
      {label} <span className="font-bold text-white">{value}</span>
    </span>
  );
}

export function AppLayout() {
  const [health, setHealth] = useState<HealthStatus | null>(null);
  const [offline, setOffline] = useState(false);
  const [open, setOpen] = useState(false);
  const location = useLocation();

  useEffect(() => {
    let alive = true;
    const poll = () =>
      api.health().then((h) => alive && (setHealth(h), setOffline(false))).catch(() => alive && setOffline(true));
    poll();
    const t = setInterval(poll, 30000);
    return () => { alive = false; clearInterval(t); };
  }, []);
  useEffect(() => setOpen(false), [location.pathname]);

  const nav = (
    <nav aria-label="Main navigation" className="flex-1 overflow-y-auto px-2 py-3">
      {NAV.map((n) => (
        <NavLink
          key={n.to}
          to={n.to}
          end={n.end}
          className={({ isActive }) =>
            `mb-0.5 flex items-center gap-3 rounded-md px-3 py-2 text-[13px] font-medium transition-colors ${isActive ? 'bg-signal text-white' : 'text-slate-300 hover:bg-white/10 hover:text-white'}`
          }
        >
          <Icon name={n.icon} />
          {n.label}
        </NavLink>
      ))}
    </nav>
  );

  return (
    <div className="flex h-full">
      <aside className="hidden w-60 shrink-0 flex-col bg-ink lg:flex">
        <Brand />
        {nav}
        <div className="border-t border-white/10 px-4 py-3 text-[11px] text-slate-400">
          v{health?.versions.application ?? '-'} · rule base v{health?.versions.rulebase ?? '-'}
        </div>
      </aside>
      {open && (
        <div className="fixed inset-0 z-40 lg:hidden" role="dialog" aria-modal="true" aria-label="Navigation">
          <div className="absolute inset-0 bg-black/50" onClick={() => setOpen(false)} />
          <aside className="absolute left-0 top-0 flex h-full w-64 flex-col bg-ink"><Brand />{nav}</aside>
        </div>
      )}
      <div className="flex min-w-0 flex-1 flex-col">
        <header className="flex items-center justify-between gap-3 bg-ink-800 px-4 py-2.5 text-white">
          <div className="flex items-center gap-3">
            <button className="rounded p-1.5 hover:bg-white/10 lg:hidden" aria-label="Open navigation" onClick={() => setOpen(true)}>
              <Icon name="menu" />
            </button>
            <span className="text-sm font-bold tracking-wide lg:hidden">FRAUDSHIELD AI</span>
            <span className="hidden text-xs font-semibold uppercase tracking-widest text-slate-400 lg:inline">Risk Intelligence Console</span>
          </div>
          <div className="flex flex-wrap items-center justify-end gap-2" data-testid="status-bar">
            {offline || !health ? (
              <StatusChip label="API" value={offline ? 'OFFLINE' : 'CHECKING'} ok={false} />
            ) : (
              <>
                <StatusChip label="API" value={health.api} ok={health.api === 'ONLINE'} />
                <StatusChip label="Database" value={health.database} ok={health.database === 'CONNECTED'} />
                <StatusChip label="Rule engine" value={health.rule_engine} ok={health.rule_engine === 'READY'} />
                <span className="hidden md:inline-flex"><StatusChip label="Knowledge base" value={health.knowledge_base} ok={health.knowledge_base === 'LOADED'} /></span>
              </>
            )}
          </div>
        </header>
        <main className="min-h-0 flex-1 overflow-y-auto px-5 py-5 lg:px-7" id="main">
          <Outlet />
        </main>
      </div>
    </div>
  );
}

function Brand() {
  return (
    <div className="flex items-center gap-3 px-4 py-4">
      <svg width="30" height="30" viewBox="0 0 32 32" aria-hidden="true">
        <path d="M16 2 4 7v8c0 7.500 5 12.900 12 15 7-2.100 12-7.500 12-15V7z" fill="#12233A" stroke="#0E7C86" strokeWidth="1.500" />
        <path d="m12 15.500 3 3 6-6" fill="none" stroke="#fff" strokeWidth="2.400" strokeLinecap="round" strokeLinejoin="round" />
      </svg>
      <div>
        <div className="text-[15px] font-extrabold leading-none tracking-wide text-white">FRAUDSHIELD <span className="text-[#46C3CC]">AI</span></div>
        <div className="mt-1 text-[10px] uppercase tracking-widest text-slate-400">Payment risk intelligence</div>
      </div>
    </div>
  );
}
