import { useMemo, useState } from 'react';
import type { TraceGraphData } from '../types/api';
import { KIND_STYLE } from '../utils/risk';

const COL_W = 210;
const ROW_H = 44;
const NODE_W = 168;
const NODE_H = 30;
const PAD = 14;

interface Props {
  graph: TraceGraphData;
  /** Start with only the decisive reasoning chain visible. */
  decisiveOnly?: boolean;
}

/** Layered SVG rendering of the inference: facts -> rules -> derived facts. Layout comes from backend layers. */
export function TraceGraph({ graph, decisiveOnly = true }: Props) {
  const [only, setOnly] = useState(decisiveOnly);
  const [selected, setSelected] = useState<string | null>(null);

  const layout = useMemo(() => {
    const nodes = graph.nodes.filter((n) => !only || n.decisive);
    const ids = new Set(nodes.map((n) => n.id));
    const edges = graph.edges.filter((e) => ids.has(e.from) && ids.has(e.to) && (!only || e.decisive));
    const layers = Array.from(new Set(nodes.map((n) => n.layer))).sort((a, b) => a - b);
    const rows: Record<number, number> = {};
    const pos = new Map<string, { x: number; y: number }>();
    nodes.forEach((n) => {
      const col = layers.indexOf(n.layer);
      const row = (rows[n.layer] = (rows[n.layer] ?? -1) + 1);
      pos.set(n.id, { x: PAD + col * COL_W, y: PAD + row * ROW_H });
    });
    const maxRows = Math.max(1, ...Object.values(rows).map((r) => r + 1));
    return { nodes, edges, pos, width: PAD * 2 + Math.max(1, layers.length) * COL_W - (COL_W - NODE_W), height: PAD * 2 + maxRows * ROW_H - (ROW_H - NODE_H) };
  }, [graph, only]);

  const connected = useMemo(() => {
    if (!selected) return null;
    const set = new Set<string>([selected]);
    layout.edges.forEach((e) => {
      if (e.from === selected) set.add(e.to);
      if (e.to === selected) set.add(e.from);
    });
    return set;
  }, [selected, layout.edges]);

  const total = graph.nodes.length;
  return (
    <div>
      <div className="mb-2 flex flex-wrap items-center justify-between gap-3">
        <div className="flex flex-wrap items-center gap-3 text-xs text-slate-600">
          {['observed', 'behavioural', 'constraint', 'indicator', 'risk'].map((k) => (
            <span key={k} className="inline-flex items-center gap-1.5">
              <span className="inline-block h-3 w-4 rounded-sm border" style={{ background: KIND_STYLE[k].fill, borderColor: KIND_STYLE[k].stroke }} />
              {KIND_STYLE[k].label}
            </span>
          ))}
          <span className="inline-flex items-center gap-1.5">
            <span className="inline-block h-3 w-4 rounded-full bg-ink" /> Rule
          </span>
        </div>
        <label className="inline-flex items-center gap-2 text-xs font-semibold">
          <input type="checkbox" checked={only} onChange={(e) => setOnly(e.target.checked)} />
          Decisive chain only ({layout.nodes.length} of {total} nodes)
        </label>
      </div>
      <div className="overflow-auto rounded-md border border-line bg-slate-50" style={{ maxHeight: 520 }}>
        <svg
          role="img"
          aria-label="Inference trace graph: observed facts feed rules, which derive indicators and risk conclusions"
          width={layout.width}
          height={layout.height}
          data-testid="trace-graph"
        >
          {layout.edges.map((e, i) => {
            const a = layout.pos.get(e.from)!;
            const b = layout.pos.get(e.to)!;
            const x1 = a.x + NODE_W, y1 = a.y + NODE_H / 2, x2 = b.x, y2 = b.y + NODE_H / 2;
            const active = !connected || (connected.has(e.from) && connected.has(e.to));
            return (
              <path
                key={i}
                d={`M${x1} ${y1} C${x1 + 50} ${y1}, ${x2 - 50} ${y2}, ${x2} ${y2}`}
                fill="none"
                stroke={e.decisive ? '#0E7C86' : '#9AA7B8'}
                strokeWidth={e.decisive ? 1.8 : 1}
                opacity={active ? 0.9 : 0.12}
              />
            );
          })}
          {layout.nodes.map((n) => {
            const p = layout.pos.get(n.id)!;
            const isRule = n.type === 'rule';
            const k = KIND_STYLE[n.kind] ?? KIND_STYLE.external;
            const dim = connected && !connected.has(n.id);
            const label = isRule ? `${n.label} ${n.name ?? ''}` : n.label;
            return (
              <g
                key={n.id}
                transform={`translate(${p.x},${p.y})`}
                role="button"
                tabIndex={0}
                aria-pressed={selected === n.id}
                aria-label={isRule ? `Rule ${n.label}: ${n.name}` : `Fact ${n.id}`}
                data-testid={`graph-node-${n.id}`}
                onClick={() => setSelected(selected === n.id ? null : n.id)}
                onKeyDown={(e) => (e.key === 'Enter' || e.key === ' ') && setSelected(selected === n.id ? null : n.id)}
                style={{ cursor: 'pointer', opacity: dim ? 0.25 : 1 }}
              >
                <title>{isRule ? `${n.label}: ${n.name}` : n.id}</title>
                <rect
                  width={NODE_W}
                  height={NODE_H}
                  rx={isRule ? 15 : 5}
                  fill={isRule ? '#0B1626' : k.fill}
                  stroke={n.decisive ? '#0E7C86' : isRule ? '#0B1626' : k.stroke}
                  strokeWidth={n.decisive ? 2.4 : 1}
                />
                <text x={NODE_W / 2} y={NODE_H / 2 + 4} textAnchor="middle" fontSize="11.5" fontWeight={isRule ? 700 : 600} fill={isRule ? '#fff' : k.text}>
                  {label.length > 24 ? label.slice(0, 23) + '…' : label}
                </text>
              </g>
            );
          })}
        </svg>
      </div>
      <p className="mt-1 text-xs text-slate-500">Click a node to highlight its connections. Teal outlines mark the decisive reasoning chain.</p>
    </div>
  );
}
