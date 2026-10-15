export function formatAmount(amount: number, currency = 'INR'): string {
  try {
    return new Intl.NumberFormat('en-IN', { style: 'currency', currency, maximumFractionDigits: 2 }).format(amount);
  } catch {
    return `${currency} ${amount.toLocaleString('en-IN')}`;
  }
}

export function formatDateTime(iso?: string | null): string {
  if (!iso) return '-';
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleString('en-GB', { day: '2-digit', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit' });
}

export function formatDay(iso: string): string {
  const d = new Date(iso + 'T00:00:00');
  return Number.isNaN(d.getTime()) ? iso : d.toLocaleDateString('en-GB', { day: '2-digit', month: 'short' });
}

export function formatMs(ms?: number | null): string {
  if (ms === undefined || ms === null) return '-';
  return ms < 10 ? `${ms.toFixed(2)} ms` : `${ms.toFixed(1)} ms`;
}

export function humanize(token: string): string {
  const s = token.replace(/_/g, ' ').toLowerCase();
  return s.charAt(0).toUpperCase() + s.slice(1);
}

export function formatUptime(seconds: number): string {
  if (seconds < 60) return `${seconds}s`;
  if (seconds < 3600) return `${Math.floor(seconds / 60)}m ${seconds % 60}s`;
  return `${Math.floor(seconds / 3600)}h ${Math.floor((seconds % 3600) / 60)}m`;
}

export function newTransactionId(): string {
  return 'TXN' + Date.now().toString(36).toUpperCase().slice(-7);
}

export function cellText(v: unknown): string {
  if (v === null || v === undefined) return '-';
  if (typeof v === 'boolean') return v ? 'Yes' : 'No';
  if (Array.isArray(v)) return v.map(cellText).join(', ') || '-';
  if (typeof v === 'object') return JSON.stringify(v);
  return String(v);
}
