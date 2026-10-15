import { Bar, BarChart, CartesianGrid, Cell, Legend, Pie, PieChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import type { RiskLevel, TrendDay } from '../types/api';
import { formatDay } from '../utils/format';
import { RISK_LEVELS, RISK_STYLE } from '../utils/risk';
import { EmptyState } from './ui';
import { RiskBadge } from './RiskBadge';

export function RiskDistributionChart({ data }: { data: { risk_level: RiskLevel; count: number }[] }) {
  const total = data.reduce((a, d) => a + d.count, 0);
  if (total === 0) return <EmptyState title="No evaluations yet">Analyse a transaction to populate the distribution.</EmptyState>;
  return (
    <div className="flex flex-wrap items-center gap-6" data-testid="risk-distribution">
      <div style={{ width: 190, height: 190 }}>
        <ResponsiveContainer width="100%" height="100%">
          <PieChart>
            <Pie data={data} dataKey="count" nameKey="risk_level" innerRadius={52} outerRadius={84} paddingAngle={2} stroke="#fff" isAnimationActive={false}>
              {data.map((d) => <Cell key={d.risk_level} fill={RISK_STYLE[d.risk_level].color} />)}
            </Pie>
            <Tooltip />
          </PieChart>
        </ResponsiveContainer>
      </div>
      {/* The legend always shows labels and counts: colour is never the only channel. */}
      <ul className="min-w-[170px] space-y-2">
        {data.map((d) => (
          <li key={d.risk_level} className="flex items-center justify-between gap-4">
            <RiskBadge level={d.risk_level} size="sm" />
            <span className="tabular-nums font-semibold">{d.count} <span className="font-normal text-slate-500">({total ? Math.round((d.count / total) * 100) : 0}%)</span></span>
          </li>
        ))}
      </ul>
    </div>
  );
}

export function TrendChart({ days, sufficient }: { days: TrendDay[]; sufficient: boolean }) {
  if (!sufficient) return <EmptyState title="Not enough history for a trend">A trend needs evaluations on at least two different days.</EmptyState>;
  const data = days.map((d) => ({ ...d, label: formatDay(d.day) }));
  return (
    <div style={{ height: 240 }} data-testid="trend-chart">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={data} margin={{ top: 4, right: 8, left: -18, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#E2E8F0" vertical={false} />
          <XAxis dataKey="label" tick={{ fontSize: 11 }} interval="preserveStartEnd" />
          <YAxis allowDecimals={false} tick={{ fontSize: 11 }} />
          <Tooltip />
          <Legend wrapperStyle={{ fontSize: 12 }} />
          {RISK_LEVELS.map((lv) => (
            <Bar key={lv} dataKey={lv.toLowerCase()} name={RISK_STYLE[lv].label} stackId="a" fill={RISK_STYLE[lv].color} isAnimationActive={false} />
          ))}
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

export function HBar({ data, nameKey, valueKey, color = '#1B3150', height }: { data: Record<string, any>[]; nameKey: string; valueKey: string; color?: string; height?: number }) {
  if (!data.length) return <EmptyState title="No data" />;
  return (
    <div style={{ height: height ?? Math.max(120, data.length * 30 + 30) }}>
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={data} layout="vertical" margin={{ top: 0, right: 24, left: 8, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#E2E8F0" horizontal={false} />
          <XAxis type="number" allowDecimals={false} tick={{ fontSize: 11 }} />
          <YAxis type="category" dataKey={nameKey} width={130} tick={{ fontSize: 11 }} />
          <Tooltip />
          <Bar dataKey={valueKey} fill={color} radius={[0, 3, 3, 0]} isAnimationActive={false} label={{ position: 'right', fontSize: 11 }} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
