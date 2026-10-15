import { useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { TraceGraph } from '../components/TraceGraph';
import {
  AuditTable, BehaviourTable, ConstraintsTable, DriversPanel, ExecutiveBanner, ExecutionTable, FactsPanel, FeaturesTable,
  InputSnapshot, LogicalInference, MetadataPanel, NarrativePanel, PipelinePanel, ProofTree, RecommendationCard, SeverityMeter,
  TriggeredRulesTable, EvidenceSeparation,
} from '../components/ResultPanels';
import { Card, ErrorState, Loading, PageHeader } from '../components/ui';
import { useAsync } from '../hooks/useAsync';
import { api } from '../services/api';

const TABS = ['Overview', 'Evidence', 'Reasoning', 'Behaviour & constraints', 'Audit trail', 'Raw record'] as const;

export function TransactionDetailsPage() {
  const { id = '' } = useParams();
  const [tab, setTab] = useState<(typeof TABS)[number]>('Overview');
  const q = useAsync(() => api.transaction(id), [id]);
  if (q.loading && !q.data) return <Loading label="Loading transaction" />;
  if (q.error && !q.data) return <ErrorState error={q.error} onRetry={q.reload} />;
  const { result, audit, transaction } = q.data!;

  return (
    <div className="space-y-5">
      <PageHeader
        title={`Transaction ${result.transaction_id}`}
        subtitle="Forensic view: evidence, reasoning and audit trail"
        actions={<>
          <Link className="btn-secondary" to="/history">Back to history</Link>
          <Link className="btn-primary" to={`/reports?transaction=${result.transaction_id}`}>Generate report</Link>
        </>}
      />
      <ExecutiveBanner result={result} />
      <div role="tablist" aria-label="Transaction sections" className="flex flex-wrap gap-1 border-b border-line">
        {TABS.map((t) => (
          <button key={t} role="tab" aria-selected={tab === t} id={`tab-${t}`} onClick={() => setTab(t)}
            className={`-mb-px border-b-2 px-4 py-2 text-sm font-semibold ${tab === t ? 'border-signal text-signal-dark' : 'border-transparent text-slate-500 hover:text-ink'}`}>
            {t}
          </button>
        ))}
      </div>
      <div role="tabpanel" aria-labelledby={`tab-${tab}`} className="space-y-5">
        {tab === 'Overview' && (
          <>
            <div className="grid gap-5 lg:grid-cols-2"><RecommendationCard rec={result.recommendation} status={transaction.status} /><SeverityMeter index={result.severity_index} /></div>
            <div className="grid gap-5 lg:grid-cols-2"><DriversPanel explanation={result.explanation} /><NarrativePanel explanation={result.explanation} /></div>
            <div className="grid gap-5 lg:grid-cols-2"><Card title="Input snapshot"><InputSnapshot snapshot={result.input_snapshot} /></Card><Card title="Audit metadata"><MetadataPanel result={result} /></Card></div>
            <Card title="Pipeline execution"><PipelinePanel stages={result.pipeline} /></Card>
          </>
        )}
        {tab === 'Evidence' && (
          <>
            <EvidenceSeparation explanation={result.explanation} />
            <Card title="Generated facts"><FactsPanel facts={result.facts} /></Card>
            <Card title="Extracted features" pad={false}><FeaturesTable features={result.features} /></Card>
          </>
        )}
        {tab === 'Reasoning' && (
          <>
            <Card title="Inference trace graph"><TraceGraph graph={result.explanation.graph} /></Card>
            {result.explanation.why_chain && <Card title={result.explanation.question}><ProofTree node={result.explanation.why_chain} /></Card>}
            <Card title="Rules triggered" pad={false}><TriggeredRulesTable rules={result.triggered_rules} /></Card>
            <Card title="Logical inference chain"><LogicalInference steps={result.explanation.logical_inference} /></Card>
            <Card title="Forward-chaining execution trace" pad={false}><ExecutionTable executions={result.reasoning_trace} /></Card>
            <Card title="Conflict-resolution strategy"><ol className="list-decimal pl-5 text-sm">{result.inference.conflict_resolution_strategy.map((s) => <li key={s}>{s.replace(/^\d+\.\s*/, '')}</li>)}</ol>
              <p className="mt-2 text-sm text-slate-600">Final risk resolution: {result.assessment.rationale}</p></Card>
          </>
        )}
        {tab === 'Behaviour & constraints' && (
          <>
            <Card title="Behavioural analysis" pad={false}><BehaviourTable behaviour={result.behavioural_analysis} /></Card>
            <Card title="Constraint evaluation" pad={false}><ConstraintsTable constraints={result.constraints} /></Card>
            <Card title="Validation"><p className="text-sm">Input accepted: <b>{result.validation.passed ? 'yes' : 'no'}</b>. {result.validation.normalisations.length ? 'Normalised: ' + result.validation.normalisations.map((n) => `${n.field} "${n.from}" → "${n.to}"`).join('; ') : 'No normalisation was necessary.'}</p></Card>
          </>
        )}
        {tab === 'Audit trail' && <Card title="Audit events" pad={false}><AuditTable events={audit} /></Card>}
        {tab === 'Raw record' && <Card title="Stored analysis result (JSON)"><pre className="mono max-h-[600px] overflow-auto rounded bg-slate-50 p-3" data-testid="raw-json">{JSON.stringify(result, null, 2)}</pre></Card>}
      </div>
    </div>
  );
}
