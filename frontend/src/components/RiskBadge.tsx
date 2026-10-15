import type { RiskLevel } from '../types/api';
import { RISK_STYLE } from '../utils/risk';

// Each level has a distinct shape AND a text label, so risk is never conveyed by colour alone.
function Shape({ level, color }: { level: RiskLevel; color: string }) {
  switch (level) {
    case 'LOW':
      return <circle cx="6" cy="6" r="4.500" fill={color} />;
    case 'MEDIUM':
      return <path d="M6 1 11 6 6 11 1 6z" fill={color} />;
    case 'HIGH':
      return <path d="M6 1 11.500 11H.5z" fill={color} />;
    default:
      return <path d="M4 1h4l3 3v4l-3 3H4L1 8V4z" fill={color} />;
  }
}

export function RiskBadge({ level, size = 'md' }: { level: RiskLevel | null | undefined; size?: 'sm' | 'md' | 'lg' }) {
  if (!level) return <span className="text-slate-400">-</span>;
  const s = RISK_STYLE[level];
  const cls = size === 'lg' ? 'text-base px-4 py-1.5 gap-2.5' : size === 'sm' ? 'text-[11px] px-2 py-0.5 gap-1.5' : 'text-xs px-2.5 py-1 gap-2';
  return (
    <span
      data-testid={`risk-badge-${level}`}
      className={`inline-flex items-center rounded-full border font-bold uppercase tracking-wide ${cls}`}
      style={{ color: s.color, background: s.bg, borderColor: s.border }}
    >
      <svg width={size === 'lg' ? 16 : 12} height={size === 'lg' ? 16 : 12} viewBox="0 0 12 12" aria-hidden="true">
        <Shape level={level} color={s.color} />
      </svg>
      {level}
    </span>
  );
}
