import type { ReactNode } from 'react';
import { Link } from 'react-router-dom';
import type {
  AnalysisResult, AuditEvent, BehaviourAnalysis, Constraint, Explanation, Fact, Feature, PipelineStage, ProofNode,
  Recommendation, RuleExecution, SeverityIndex, TriggeredRule,
} from '../types/api';
import { cellText, formatDateTime, formatMs, humanize } from '../utils/format';
import { KIND_STYLE, RISK_STYLE, STATUS_LABEL } from '../utils/risk';
import { RiskBadge } from './RiskBadge';
import { Card, EmptyState, Meter, Tag, TableWrap } from './ui';

export function RecommendationCard({ rec, status }: { rec: Recommendation; status?: string }) {
  return (
    <div data-testid="recommendation" className="rounded-lg border border-line bg-white p-4">
      <div className="card-title">Recommendation</div>
      <div className="mt-1 text-lg font-bold" data-testid="recommendation-label">{rec.label}</div>
      <div className="mt-0.5 text-xs font-semibold uppercase tracking-wider text-slate-500">{rec.action.replace(/_/g, ' ')} · {rec.urgency.replace(/_/g, ' ')}</div>
      <p className="mt-2 text-sm text-slate-600">{rec.rationale}</p>
      {status && <div className="mt-2 text-xs text-slate-500">Decision status: <b>{STATUS_LABEL[status] ?? humanize(status)}</b></div>}
    </div>
  );
}

export function SeverityMeter({ index }: { index: SeverityIndex }) {
  return (
    <div className="rounded-lg border border-line bg-white p-4">
      <Meter value={index.value} max={index.max} label={index.name} />
      <p className="mt-2 text-xs text-slate-500">{index.note}</p>
    </div>
  );
}

export function DriversPanel({ explanation }: { explanation: Explanation }) {
  const drivers = explanation.drivers;
  const mitigating = drivers.length > 0 && drivers[0].role === 'mitigating';
  return (
    <Card title={mitigating ? 'Mitigating evidence' : 'Primary risk drivers'}>
      {drivers.length === 0 ? (
        <EmptyState title="No risk drivers">No rule produced a risk conclusion for this transaction.</EmptyState>
      ) : (
        <ul className="space-y-1.5" data-testid="drivers">
          {drivers.map((d) => (
            <li key={d.fact} className="flex items-start gap-2.5">
              <span aria-hidden="true" className="mt-1.5 inline-block h-2 w-2 shrink-0 rounded-sm bg-ink-700" />
              <span>
                <span className="font-medium">{d.text}</span> <span className="mono text-slate-500">{d.fact}</span>
              </span>
            </li>
          ))}
        </ul>
      )}
    </Card>
  );
}

export function NarrativePanel({ explanation }: { explanation: Explanation }) {
  const fd = explanation.final_decision;
  return (
    <Card title={explanation.question}>
      <p className="leading-relaxed" data-testid="narrative">{explanation.narrative}</p>
      <dl className="mt-3 grid gap-x-6 gap-y-1 text-sm sm:grid-cols-[160px_1fr]">
        <dt className="text-slate-500">Decisive conclusion</dt>
        <dd className="mono">{fd.decisive_fact ?? 'none (default LOW)'}</dd>
        <dt className="text-slate-500">Decisive rules</dt>
        <dd>{fd.decisive_rules.length ? fd.decisive_rules.join(', ') : '-'}</dd>
        <dt className="text-slate-500">Resolution</dt>
        <dd>{fd.resolution}</dd>
      </dl>
    </Card>
  );
}

export function EvidenceSeparation({ explanation }: { explanation: Explanation }) {
  const col = (title: string, hint: string, items: { fact: string; text: string }[]) => (
    <div>
      <div className="card-title">{title}</div>
      <p className="mb-1.5 text-xs text-slate-500">{hint}</p>
      {items.length === 0 ? <p className="text-sm text-slate-400">None</p> : (
        <ul className="space-y-1 text-sm">
          {items.map((i) => <li key={i.fact}>{i.text} <span className="mono text-slate-500">{i.fact}</span></li>)}
        </ul>
      )}
    </div>
  );
  return (
    <Card title="Evidence layers">
      <div className="grid gap-5 md:grid-cols-3">
        {col('Observed evidence', 'Taken directly from the transaction input.', explanation.observed_evidence)}
        {col('Derived evidence', 'Derived from baseline and constraint analysis.', explanation.derived_evidence)}
        {col('Logical inference', 'Concluded by production rules (see trace).',
          explanation.logical_inference.filter((s) => s.new_fact).map((s) => ({ fact: s.statement.split(' → ').pop() ?? '', text: `${s.rule_id}` })))}
      </div>
    </Card>
  );
}

export function LogicalInference({ steps }: { steps: Explanation['logical_inference'] }) {
  return (
    <ol className="space-y-2" data-testid="logical-inference">
      {steps.map((s) => (
        <li key={s.step} className="rounded-md border border-line bg-white p-3">
          <div className="flex flex-wrap items-center gap-2">
            <span className="rounded bg-ink px-1.5 py-0.5 text-[11px] font-bold text-white">{s.rule_id}</span>
            <span className="font-semibold">{s.rule_name}</span>
            <span className="text-xs text-slate-500">step {s.step} · cycle {s.cycle}</span>
            <Tag tone={s.new_fact ? 'teal' : 'slate'}>{s.new_fact ? 'new fact' : 'additional support'}</Tag>
          </div>
          <div className="mono mt-1.5 break-words">{s.statement}</div>
          <p className="mt-1 text-xs text-slate-500">{s.explanation} Selected because: {s.selected_because}.</p>
        </li>
      ))}
    </ol>
  );
}

export function TriggeredRulesTable({ rules }: { rules: TriggeredRule[] }) {
  if (!rules.length) return <EmptyState title="No rules fired" />;
  return (
    <TableWrap>
      <table className="w-full text-sm" data-testid="triggered-rules">
        <thead><tr><th className="th">Rule</th><th className="th">Name</th><th className="th">Category</th><th className="th">Prio</th><th className="th">Logic</th><th className="th">Fired</th></tr></thead>
        <tbody>
          {rules.map((r) => (
            <tr key={r.rule_id}>
              <td className="td font-bold">{r.rule_id}</td>
              <td className="td">{r.rule_name}</td>
              <td className="td">{r.category}</td>
              <td className="td tabular-nums">{r.priority}</td>
              <td className="td mono">{r.formula}</td>
              <td className="td tabular-nums">{r.times_fired}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </TableWrap>
  );
}

export function ExecutionTable({ executions }: { executions: RuleExecution[] }) {
  return (
    <TableWrap>
      <table className="w-full text-sm" data-testid="execution-trace">
        <thead><tr><th className="th">#</th><th className="th">Cycle</th><th className="th">Rule</th><th className="th">Matched facts</th><th className="th">Derived</th><th className="th">Conflict set</th><th className="th">Selected because</th></tr></thead>
        <tbody>
          {executions.map((e) => (
            <tr key={e.seq}>
              <td className="td tabular-nums">{e.seq}</td>
              <td className="td tabular-nums">{e.cycle}</td>
              <td className="td"><b>{e.rule_id}</b></td>
              <td className="td mono">{e.matched_facts.join(' ∧ ')}</td>
              <td className="td mono">{e.derived_fact} {!e.new_fact && <Tag>support</Tag>}</td>
              <td className="td tabular-nums">{e.conflict_set_size}</td>
              <td className="td text-xs text-slate-600">{e.selected_because}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </TableWrap>
  );
}

export function ProofTree({ node, depth = 0 }: { node: ProofNode; depth?: number }) {
  const k = KIND_STYLE[node.kind] ?? KIND_STYLE.external;
  return (
    <div style={{ marginLeft: depth ? 18 : 0 }} className={depth ? 'border-l-2 border-line pl-3' : ''}>
      <div className="py-0.5">
        <span className="mono rounded px-1.5 py-0.5" style={{ background: k.fill, color: k.text, border: `1px solid ${k.stroke}` }}>{node.fact}</span>
        {node.rule && <span className="ml-2 text-xs text-slate-500">derived by <b>{node.rule}</b></span>}
        {!node.rule && <span className="ml-2 text-xs text-slate-400">{k.label.toLowerCase()} fact</span>}
      </div>
      {node.children.map((c) => <ProofTree key={c.fact} node={c} depth={depth + 1} />)}
    </div>
  );
}

export function FactsPanel({ facts }: { facts: Fact[] }) {
  const kinds = ['observed', 'behavioural', 'constraint', 'indicator', 'risk', 'external'];
  return (
    <div className="space-y-4" data-testid="facts-panel">
      {kinds.map((k) => {
        const list = facts.filter((f) => f.kind === k);
        if (!list.length) return null;
        return (
          <div key={k}>
            <div className="card-title mb-1.5">{KIND_STYLE[k].label} facts ({list.length})</div>
            <TableWrap>
              <table className="w-full text-sm">
                <thead><tr><th className="th">Fact</th><th className="th">Source</th><th className="th">Derived by</th><th className="th">Parents</th></tr></thead>
                <tbody>
                  {list.map((f) => (
                    <tr key={f.text}>
                      <td className="td mono font-semibold">{f.text}</td>
                      <td className="td">{f.source}</td>
                      <td className="td">{f.derivation_rule ? [f.derivation_rule, ...f.supported_by].join(', ') : '-'}</td>
                      <td className="td mono text-slate-500">{f.parents.join(', ') || '-'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </TableWrap>
          </div>
        );
      })}
    </div>
  );
}

export function FeaturesTable({ features }: { features: Feature[] }) {
  return (
    <TableWrap>
      <table className="w-full text-sm">
        <thead><tr><th className="th">Feature</th><th className="th">Category</th><th className="th">Value</th><th className="th">Definition</th></tr></thead>
        <tbody>
          {features.map((f) => (
            <tr key={f.name}>
              <td className="td mono font-semibold">{f.name}</td>
              <td className="td">{f.category}</td>
              <td className="td font-semibold">{typeof f.value === 'boolean' ? (f.value ? '✔ true' : '✘ false') : cellText(f.value)}</td>
              <td className="td text-slate-600">{f.description}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </TableWrap>
  );
}

export function BehaviourTable({ behaviour }: { behaviour: BehaviourAnalysis }) {
  return (
    <div>
      {!behaviour.baseline_available && <p className="mb-2 rounded bg-[#FDF1DC] px-3 py-2 text-sm text-[#7A4A06]">No behavioural baseline exists for this user, so baseline comparisons were skipped.</p>}
      <TableWrap>
        <table className="w-full text-sm" data-testid="behaviour-table">
          <thead><tr><th className="th">Dimension</th><th className="th">Observed</th><th className="th">Baseline</th><th className="th">Ratio</th><th className="th">Result</th></tr></thead>
          <tbody>
            {behaviour.deviations.map((d) => (
              <tr key={d.dimension}>
                <td className="td font-medium">{d.label}</td>
                <td className="td">{cellText(d.observed)}</td>
                <td className="td">{cellText(d.baseline)}</td>
                <td className="td tabular-nums">{d.ratio ?? '-'}</td>
                <td className="td">{!d.evaluated ? <Tag>not evaluated</Tag> : d.anomalous ? <Tag tone="red">▲ deviation</Tag> : <Tag tone="teal">● normal</Tag>} <span className="text-xs text-slate-500">{d.message}</span></td>
              </tr>
            ))}
          </tbody>
        </table>
      </TableWrap>
    </div>
  );
}

export function ConstraintsTable({ constraints }: { constraints: Constraint[] }) {
  return (
    <TableWrap>
      <table className="w-full text-sm">
        <thead><tr><th className="th">ID</th><th className="th">Constraint</th><th className="th">Result</th><th className="th">Detail</th></tr></thead>
        <tbody>
          {constraints.map((c) => (
            <tr key={c.id}>
              <td className="td font-bold">{c.id}</td><td className="td">{c.name}</td>
              <td className="td">{c.passed ? <Tag tone="teal">● pass</Tag> : <Tag tone="amber">▲ violated</Tag>}</td>
              <td className="td text-slate-600">{c.message}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </TableWrap>
  );
}

export function InputSnapshot({ snapshot }: { snapshot: AnalysisResult['input_snapshot'] }) {
  return (
    <dl className="grid gap-x-6 gap-y-1.5 text-sm sm:grid-cols-2" data-testid="input-snapshot">
      {Object.entries(snapshot).map(([k, v]) => (
        <div key={k} className="flex justify-between gap-3 border-b border-slate-100 py-1">
          <dt className="text-slate-500">{humanize(k)}</dt>
          <dd className="font-medium text-right">{cellText(v)}</dd>
        </div>
      ))}
    </dl>
  );
}

export function PipelinePanel({ stages }: { stages: PipelineStage[] }) {
  return (
    <ol className="grid gap-1.5 sm:grid-cols-2" data-testid="pipeline-panel">
      {stages.map((s, i) => (
        <li key={s.key} className="flex items-start gap-3 rounded-md border border-line bg-white px-3 py-2">
          <span className="mt-0.5 inline-flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-ink text-[11px] font-bold text-white">{i + 1}</span>
          <div className="min-w-0 flex-1">
            <div className="flex justify-between gap-2"><span className="font-medium">{s.label}</span><span className="tabular-nums text-xs text-slate-500">{formatMs(s.duration_ms)}</span></div>
            <div className="truncate text-xs text-slate-500">{s.status === 'COMPLETED' ? '✔ ' : '✘ '}{s.detail}</div>
          </div>
        </li>
      ))}
    </ol>
  );
}

export function MetadataPanel({ result }: { result: AnalysisResult }) {
  const m = result.metadata;
  const rows: [string, ReactNode][] = [
    ['Evaluation ID', <span className="mono">{result.evaluation_id}</span>],
    ['Timestamp', formatDateTime(m.submitted_at ?? m.timestamp)],
    ['Engine version', m.engine_version],
    ['Rule base version', `${m.rulebase_name} v${m.rulebase_version}`],
    ['Application version', m.app_version],
    ['Schema version', m.schema_version ?? '-'],
    ['Processing time', formatMs(m.processing_time_ms)],
    ['Inference', `${result.inference.firings} firings in ${result.inference.cycles} cycles (${result.inference.terminated_by})`],
    ['Rules evaluated', `${result.rules_evaluated.length} (${result.triggered_rules.length} triggered)`],
  ];
  return (
    <dl className="grid gap-x-6 gap-y-1.5 text-sm sm:grid-cols-2" data-testid="audit-metadata">
      {rows.map(([k, v]) => (
        <div key={k} className="flex justify-between gap-3 border-b border-slate-100 py-1"><dt className="text-slate-500">{k}</dt><dd className="font-medium text-right">{v}</dd></div>
      ))}
    </dl>
  );
}

export function AuditTable({ events, showTransaction = false }: { events: AuditEvent[]; showTransaction?: boolean }) {
  if (!events.length) return <EmptyState title="No audit events" />;
  return (
    <TableWrap>
      <table className="w-full text-sm" data-testid="audit-table">
        <thead><tr><th className="th">Timestamp</th><th className="th">Event</th>{showTransaction && <th className="th">Transaction</th>}<th className="th">Risk</th><th className="th">Actor</th><th className="th">Rule</th><th className="th">Description</th></tr></thead>
        <tbody>
          {events.map((e) => (
            <tr key={e.id}>
              <td className="td whitespace-nowrap">{formatDateTime(e.timestamp)}</td>
              <td className="td mono font-semibold">{e.event_type}</td>
              {showTransaction && <td className="td">{e.transaction_id ? <Link className="font-semibold text-signal-dark hover:underline" to={`/transactions/${e.transaction_id}`}>{e.transaction_id}</Link> : '-'}</td>}
              <td className="td"><RiskBadge level={e.risk_level} size="sm" /></td>
              <td className="td">{e.actor}</td>
              <td className="td">{e.rule_id ?? '-'}</td>
              <td className="td">{e.description}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </TableWrap>
  );
}

export function ExecutiveBanner({ result }: { result: AnalysisResult }) {
  const s = RISK_STYLE[result.risk_level];
  return (
    <div className="card overflow-hidden" data-testid="executive-decision">
      <div className="h-1.5" style={{ background: s.color }} aria-hidden="true" />
      <div className="flex flex-wrap items-center justify-between gap-4 p-5">
        <div>
          <div className="card-title">Executive decision</div>
          <div className="mt-2 flex items-center gap-3">
            <RiskBadge level={result.risk_level} size="lg" />
            <span className="text-sm text-slate-500">Transaction <b className="mono text-ink">{result.transaction_id}</b> · User <b className="mono text-ink">{result.user_id}</b></span>
          </div>
        </div>
        <div className="text-right text-xs text-slate-500">
          <div>Evaluation <span className="mono text-ink">{result.evaluation_id}</span></div>
          <div>{formatDateTime(result.metadata.submitted_at ?? result.metadata.timestamp)} · {formatMs(result.metadata.processing_time_ms)}</div>
          {result.synthetic && <div className="mt-1"><Tag tone="amber">Synthetic demonstration data</Tag></div>}
        </div>
      </div>
    </div>
  );
}
